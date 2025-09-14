"""
Social Media Publishing Services
Core business logic for publishing content to social platforms
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import requests
import logging
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
import json
import uuid

from .models import (
    SocialAccount, ScheduledPost, PostAnalytics,
    SocialPlatform, WebhookEvent
)

logger = logging.getLogger(__name__)


class SocialMediaError(Exception):
    """Base exception for social media operations"""
    pass


class AuthenticationError(SocialMediaError):
    """OAuth/Authentication related errors"""
    pass


class PublishingError(SocialMediaError):
    """Content publishing errors"""
    pass


class RateLimitError(SocialMediaError):
    """Rate limiting errors"""
    pass


class BaseSocialPublisher(ABC):
    """Abstract base class for social media publishers"""

    def __init__(self, social_account: SocialAccount):
        self.social_account = social_account
        self.platform = social_account.platform.name
        self.access_token = social_account.access_token

    @abstractmethod
    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """Handle OAuth authentication flow"""
        pass

    @abstractmethod
    def refresh_token(self) -> Dict[str, Any]:
        """Refresh access token"""
        pass

    @abstractmethod
    def publish_video(self, video_path: str, caption: str, **kwargs) -> Dict[str, Any]:
        """Publish video to platform"""
        pass

    @abstractmethod
    def get_user_info(self) -> Dict[str, Any]:
        """Get user profile information"""
        pass

    @abstractmethod
    def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get post analytics"""
        pass

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling"""
        try:
            response = requests.request(method, url, timeout=30, **kwargs)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', 60)
                raise RateLimitError(f"Rate limited. Retry after {retry_after} seconds")

            # Handle authentication errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid or expired access token")

            # Handle other errors
            if not response.ok:
                error_data = response.json() if response.content else {}
                raise SocialMediaError(f"API Error: {response.status_code} - {error_data}")

            return response

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise SocialMediaError(f"Network error: {e}")


class TikTokPublisher(BaseSocialPublisher):
    """TikTok Content Posting API integration"""

    BASE_URL = "https://open.tiktokapis.com/v2"

    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        url = f"{self.BASE_URL}/oauth/token/"

        data = {
            'client_id': settings.TIKTOK_CLIENT_ID,
            'client_secret': settings.TIKTOK_CLIENT_SECRET,
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.TIKTOK_REDIRECT_URI
        }

        response = self._make_request('POST', url, data=data)
        return response.json()

    def refresh_token(self) -> Dict[str, Any]:
        """Refresh TikTok access token"""
        url = f"{self.BASE_URL}/oauth/token/"

        data = {
            'client_id': settings.TIKTOK_CLIENT_ID,
            'client_secret': settings.TIKTOK_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': self.social_account.refresh_token
        }

        response = self._make_request('POST', url, data=data)
        return response.json()

    def publish_video(self, video_path: str, caption: str, **kwargs) -> Dict[str, Any]:
        """Publish video to TikTok using Content Posting API"""

        # Step 1: Initialize post
        post_info = self._initialize_post(caption, **kwargs)

        # Step 2: Upload video
        upload_url = post_info['data']['upload_url']
        self._upload_video_file(upload_url, video_path)

        # Step 3: Publish post
        result = self._publish_post(post_info['data']['publish_id'])

        return result

    def _initialize_post(self, caption: str, **kwargs) -> Dict[str, Any]:
        """Initialize TikTok post"""
        url = f"{self.BASE_URL}/post/publish/inbox/video/init/"

        # Extract hashtags from caption or kwargs
        hashtags = kwargs.get('hashtags', [])
        if hashtags and not any(tag in caption for tag in hashtags):
            caption = f"{caption} " + " ".join(f"#{tag}" for tag in hashtags)

        # Add #Shorts for short videos
        if kwargs.get('is_short', True) and '#Shorts' not in caption:
            caption = f"{caption} #Shorts"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        data = {
            'post_info': {
                'title': caption,
                'privacy_level': kwargs.get('privacy_level', 'MUTUAL_FOLLOW_FRIEND'),
                'disable_duet': kwargs.get('disable_duet', False),
                'disable_comment': kwargs.get('disable_comment', False),
                'disable_stitch': kwargs.get('disable_stitch', False),
                'video_cover_timestamp_ms': kwargs.get('cover_timestamp', 1000),
            },
            'source_info': {
                'source': 'PULL_FROM_URL',
                'video_url': kwargs.get('video_url', ''),
            }
        }

        response = self._make_request('POST', url, headers=headers, json=data)
        return response.json()

    def _upload_video_file(self, upload_url: str, video_path: str):
        """Upload video file to TikTok"""
        with open(video_path, 'rb') as video_file:
            headers = {
                'Content-Type': 'video/mp4',
                'Content-Range': f'bytes 0-{len(video_file.read())-1}/{len(video_file.read())}',
                'Content-Length': str(len(video_file.read()))
            }
            video_file.seek(0)  # Reset file pointer

            response = requests.put(upload_url, data=video_file, headers=headers, timeout=300)
            if not response.ok:
                raise PublishingError(f"Video upload failed: {response.status_code}")

    def _publish_post(self, publish_id: str) -> Dict[str, Any]:
        """Finalize TikTok post publication"""
        url = f"{self.BASE_URL}/post/publish/submit/{publish_id}/"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
        }

        response = self._make_request('POST', url, headers=headers)
        return response.json()

    def get_user_info(self) -> Dict[str, Any]:
        """Get TikTok user information"""
        url = f"{self.BASE_URL}/user/info/"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
        }

        response = self._make_request('GET', url, headers=headers)
        return response.json()

    def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get TikTok post analytics (requires approval)"""
        # Note: This requires additional approval from TikTok
        url = f"{self.BASE_URL}/video/query/"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
        }

        params = {
            'fields': 'id,title,video_description,duration,cover_image_url,create_time,view_count,like_count,comment_count,share_count'
        }

        response = self._make_request('POST', url, headers=headers, json={'filters': {'video_ids': [post_id]}})
        return response.json()


class InstagramPublisher(BaseSocialPublisher):
    """Instagram Graph API integration for business accounts"""

    BASE_URL = "https://graph.facebook.com/v18.0"

    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        url = f"https://api.instagram.com/oauth/access_token"

        data = {
            'client_id': settings.INSTAGRAM_CLIENT_ID,
            'client_secret': settings.INSTAGRAM_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.INSTAGRAM_REDIRECT_URI,
            'code': auth_code
        }

        response = self._make_request('POST', url, data=data)
        return response.json()

    def refresh_token(self) -> Dict[str, Any]:
        """Refresh Instagram long-lived access token"""
        url = f"{self.BASE_URL}/refresh_access_token"

        params = {
            'grant_type': 'ig_refresh_token',
            'access_token': self.access_token
        }

        response = self._make_request('GET', url, params=params)
        return response.json()

    def publish_video(self, video_path: str, caption: str, **kwargs) -> Dict[str, Any]:
        """Publish video to Instagram (Reels)"""

        # Step 1: Create media container
        container_id = self._create_media_container(video_path, caption, **kwargs)

        # Step 2: Publish container
        result = self._publish_media_container(container_id)

        return result

    def _create_media_container(self, video_path: str, caption: str, **kwargs) -> str:
        """Create Instagram media container"""
        user_id = self.social_account.account_id
        url = f"{self.BASE_URL}/{user_id}/media"

        # Upload video to a public URL first (you'll need your own CDN/storage)
        video_url = kwargs.get('video_url') or self._upload_to_cdn(video_path)

        params = {
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'access_token': self.access_token
        }

        # Add cover image if provided
        if kwargs.get('cover_url'):
            params['thumb_offset'] = kwargs.get('thumb_offset', '0')

        response = self._make_request('POST', url, params=params)
        data = response.json()
        return data['id']

    def _publish_media_container(self, container_id: str) -> Dict[str, Any]:
        """Publish Instagram media container"""
        user_id = self.social_account.account_id
        url = f"{self.BASE_URL}/{user_id}/media_publish"

        params = {
            'creation_id': container_id,
            'access_token': self.access_token
        }

        response = self._make_request('POST', url, params=params)
        return response.json()

    def _upload_to_cdn(self, video_path: str) -> str:
        """Upload video to CDN (implement based on your storage solution)"""
        # This is a placeholder - implement based on your CDN (AWS S3, Cloudinary, etc.)
        # For now, return a placeholder URL
        raise NotImplementedError("CDN upload not implemented. Provide video_url in kwargs.")

    def get_user_info(self) -> Dict[str, Any]:
        """Get Instagram user information"""
        user_id = self.social_account.account_id
        url = f"{self.BASE_URL}/{user_id}"

        params = {
            'fields': 'id,username,account_type,media_count,followers_count',
            'access_token': self.access_token
        }

        response = self._make_request('GET', url, params=params)
        return response.json()

    def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get Instagram post analytics"""
        url = f"{self.BASE_URL}/{post_id}/insights"

        params = {
            'metric': 'impressions,reach,saved,video_views,likes,comments,shares',
            'access_token': self.access_token
        }

        response = self._make_request('GET', url, params=params)
        return response.json()


class YouTubePublisher(BaseSocialPublisher):
    """YouTube Data API v3 integration for Shorts"""

    BASE_URL = "https://www.googleapis.com/youtube/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"

    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        url = "https://oauth2.googleapis.com/token"

        data = {
            'client_id': settings.YOUTUBE_CLIENT_ID,
            'client_secret': settings.YOUTUBE_CLIENT_SECRET,
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.YOUTUBE_REDIRECT_URI
        }

        response = self._make_request('POST', url, data=data)
        return response.json()

    def refresh_token(self) -> Dict[str, Any]:
        """Refresh YouTube access token"""
        url = "https://oauth2.googleapis.com/token"

        data = {
            'client_id': settings.YOUTUBE_CLIENT_ID,
            'client_secret': settings.YOUTUBE_CLIENT_SECRET,
            'refresh_token': self.social_account.refresh_token,
            'grant_type': 'refresh_token'
        }

        response = self._make_request('POST', url, data=data)
        return response.json()

    def publish_video(self, video_path: str, caption: str, **kwargs) -> Dict[str, Any]:
        """Upload video to YouTube as Short"""

        # Prepare video metadata
        snippet = {
            'title': kwargs.get('title', caption[:100]),  # Max 100 chars for title
            'description': f"{caption}\n\n#Shorts",  # Add #Shorts hashtag
            'tags': kwargs.get('hashtags', []),
            'categoryId': kwargs.get('category_id', '22'),  # 22 = People & Blogs
        }

        status = {
            'privacyStatus': kwargs.get('privacy_status', 'public'),
            'selfDeclaredMadeForKids': False
        }

        metadata = {
            'snippet': snippet,
            'status': status
        }

        # Upload video
        return self._upload_video(video_path, metadata)

    def _upload_video(self, video_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Upload video file to YouTube"""

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'X-Upload-Content-Type': 'video/*',
            'X-Upload-Content-Length': str(self._get_file_size(video_path)),
            'Content-Type': 'application/json'
        }

        # Step 1: Initiate resumable upload
        params = {'part': 'snippet,status', 'uploadType': 'resumable'}

        init_response = self._make_request(
            'POST',
            self.UPLOAD_URL,
            headers=headers,
            params=params,
            json=metadata
        )

        upload_url = init_response.headers['Location']

        # Step 2: Upload video file
        return self._upload_video_data(upload_url, video_path)

    def _upload_video_data(self, upload_url: str, video_path: str) -> Dict[str, Any]:
        """Upload video data to YouTube"""

        with open(video_path, 'rb') as video_file:
            file_size = self._get_file_size(video_path)

            headers = {
                'Content-Length': str(file_size),
                'Content-Type': 'video/*'
            }

            response = requests.put(
                upload_url,
                data=video_file,
                headers=headers,
                timeout=600  # 10 minutes timeout for large videos
            )

            if not response.ok:
                raise PublishingError(f"YouTube upload failed: {response.status_code}")

            return response.json()

    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        import os
        return os.path.getsize(file_path)

    def get_user_info(self) -> Dict[str, Any]:
        """Get YouTube channel information"""
        url = f"{self.BASE_URL}/channels"

        params = {
            'part': 'snippet,statistics,contentDetails',
            'mine': 'true',
            'access_token': self.access_token
        }

        response = self._make_request('GET', url, params=params)
        return response.json()

    def get_analytics(self, video_id: str) -> Dict[str, Any]:
        """Get YouTube video statistics"""
        url = f"{self.BASE_URL}/videos"

        params = {
            'part': 'statistics,snippet',
            'id': video_id,
            'access_token': self.access_token
        }

        response = self._make_request('GET', url, params=params)
        return response.json()


class SocialMediaPublishingService:
    """Main service for social media publishing operations"""

    PUBLISHERS = {
        'tiktok': TikTokPublisher,
        'instagram': InstagramPublisher,
        'youtube': YouTubePublisher,
    }

    @classmethod
    def get_publisher(cls, social_account: SocialAccount) -> BaseSocialPublisher:
        """Get appropriate publisher for social account"""
        publisher_class = cls.PUBLISHERS.get(social_account.platform.name)
        if not publisher_class:
            raise SocialMediaError(f"Publisher not available for {social_account.platform.name}")

        return publisher_class(social_account)

    @classmethod
    def publish_scheduled_post(cls, scheduled_post: ScheduledPost) -> bool:
        """Publish a scheduled post"""
        try:
            # Update status
            scheduled_post.status = 'posting'
            scheduled_post.save()

            # Get publisher
            publisher = cls.get_publisher(scheduled_post.social_account)

            # Check token validity
            if scheduled_post.social_account.needs_refresh():
                cls.refresh_account_token(scheduled_post.social_account)

            # Prepare publishing parameters
            kwargs = {
                'hashtags': scheduled_post.hashtags,
                'privacy_level': 'MUTUAL_FOLLOW_FRIEND',  # TikTok
                'privacy_status': 'public',  # YouTube
                'video_url': scheduled_post.video_url,  # If video is already uploaded
            }

            # Publish content
            if scheduled_post.video_file:
                result = publisher.publish_video(
                    scheduled_post.video_file.path,
                    scheduled_post.caption,
                    **kwargs
                )
            else:
                raise PublishingError("No video file or URL provided")

            # Update post with results
            scheduled_post.status = 'posted'
            scheduled_post.posted_at = timezone.now()
            scheduled_post.platform_response = result

            # Extract platform-specific data
            if 'id' in result:
                scheduled_post.platform_post_id = result['id']
            elif 'data' in result and 'publish_id' in result['data']:
                scheduled_post.platform_post_id = result['data']['publish_id']

            scheduled_post.save()

            # Create analytics entry
            PostAnalytics.objects.create(scheduled_post=scheduled_post)

            logger.info(f"Successfully published post {scheduled_post.id}")
            return True

        except Exception as e:
            # Handle failure
            scheduled_post.status = 'failed'
            scheduled_post.error_message = str(e)
            scheduled_post.retry_count += 1
            scheduled_post.save()

            logger.error(f"Failed to publish post {scheduled_post.id}: {e}")
            return False

    @classmethod
    def refresh_account_token(cls, social_account: SocialAccount):
        """Refresh social account access token"""
        try:
            publisher = cls.get_publisher(social_account)
            token_data = publisher.refresh_token()

            # Update account with new token
            social_account.access_token = token_data['access_token']
            if 'refresh_token' in token_data:
                social_account.refresh_token = token_data['refresh_token']

            if 'expires_in' in token_data:
                social_account.token_expires_at = timezone.now() + timedelta(
                    seconds=token_data['expires_in']
                )

            social_account.status = 'connected'
            social_account.error_message = ''
            social_account.save()

            logger.info(f"Refreshed token for {social_account}")

        except Exception as e:
            social_account.status = 'error'
            social_account.error_message = str(e)
            social_account.save()

            logger.error(f"Failed to refresh token for {social_account}: {e}")
            raise

    @classmethod
    def update_post_analytics(cls, scheduled_post: ScheduledPost):
        """Update analytics for a published post"""
        if not scheduled_post.platform_post_id:
            return

        try:
            publisher = cls.get_publisher(scheduled_post.social_account)
            analytics_data = publisher.get_analytics(scheduled_post.platform_post_id)

            # Update or create analytics
            analytics, created = PostAnalytics.objects.get_or_create(
                scheduled_post=scheduled_post,
                defaults={'platform_metrics': analytics_data}
            )

            if not created:
                analytics.platform_metrics = analytics_data
                analytics.save()

            # Extract common metrics (platform-specific logic needed)
            cls._extract_common_metrics(analytics, analytics_data)

            logger.info(f"Updated analytics for post {scheduled_post.id}")

        except Exception as e:
            logger.error(f"Failed to update analytics for post {scheduled_post.id}: {e}")

    @classmethod
    def _extract_common_metrics(cls, analytics: PostAnalytics, platform_data: Dict[str, Any]):
        """Extract common metrics from platform-specific data"""
        # This would need platform-specific logic to normalize metrics
        # Placeholder implementation
        if 'views' in platform_data:
            analytics.views = platform_data['views']
        if 'likes' in platform_data:
            analytics.likes = platform_data['likes']
        if 'comments' in platform_data:
            analytics.comments = platform_data['comments']
        if 'shares' in platform_data:
            analytics.shares = platform_data['shares']

        analytics.calculate_engagement_rate()
        analytics.save()

    @classmethod
    def get_account_info(cls, social_account: SocialAccount) -> Dict[str, Any]:
        """Get updated account information"""
        publisher = cls.get_publisher(social_account)
        return publisher.get_user_info()