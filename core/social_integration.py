"""
Social Media Integration for Video Processing
Connects video clipping system to social media posting
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from typing import List, Dict, Any, Optional

from .models import VideoRequest, Clip
from social_media.models import ScheduledPost, SocialAccount
from social_media.tasks import publish_single_post

logger = logging.getLogger(__name__)


class SocialMediaIntegrationService:
    """Service to handle automatic social media posting for video clips"""

    def __init__(self, video_request: VideoRequest):
        self.video_request = video_request
        self.user = video_request.user

    def should_auto_post(self) -> bool:
        """Check if this video request should auto-post to social media"""
        return (
            self.video_request.auto_post_to_social and
            self.video_request.social_accounts.exists()
        )

    def get_social_accounts(self) -> List[SocialAccount]:
        """Get connected social accounts for this video request"""
        return list(self.video_request.social_accounts.filter(
            status='connected'
        ))

    def generate_clip_caption(self, clip: Clip, platform: str = "") -> str:
        """Generate social media caption for a clip"""
        template = self.video_request.post_caption_template

        if not template:
            # Default template
            template = "🎬 New clip from my latest video! Duration: {duration}s #AI #VideoClip #Content"

        # Replace template variables
        caption = template.format(
            title=f"Video Clip {clip.id}",
            duration=int(clip.duration),
            start_time=int(clip.start_time),
            end_time=int(clip.end_time),
            engagement_score=clip.engagement_score,
            platform=platform,
            quality=clip.video_quality
        )

        return caption

    def generate_hashtags(self, clip: Clip, platform: str = "") -> List[str]:
        """Generate hashtags for the clip"""
        hashtags = list(self.video_request.post_hashtags) if self.video_request.post_hashtags else []

        # Add default hashtags based on platform
        platform_hashtags = {
            'youtube': ['YouTube', 'Shorts', 'AI', 'VideoClip'],
            'tiktok': ['TikTok', 'AI', 'ContentCreator', 'VideoEditing'],
            'instagram': ['Instagram', 'Reel', 'AI', 'ContentCreation']
        }

        if platform.lower() in platform_hashtags:
            hashtags.extend(platform_hashtags[platform.lower()])

        # Add engagement-based hashtags
        if clip.engagement_score >= 8.0:
            hashtags.append('HighEngagement')
        if clip.engagement_score >= 9.0:
            hashtags.append('Viral')

        # Add moment tags if available
        if clip.moment_tags:
            hashtags.extend(clip.moment_tags)

        # Remove duplicates and limit to reasonable number
        hashtags = list(dict.fromkeys(hashtags))[:15]  # Keep unique, max 15

        return hashtags

    def calculate_schedule_time(self, clip_index: int, base_time: Optional[datetime] = None) -> datetime:
        """Calculate when to schedule this clip's post"""
        if not base_time:
            base_time = timezone.now()

        if self.video_request.schedule_posts:
            # Schedule posts with intervals
            interval_minutes = self.video_request.post_schedule_interval
            schedule_time = base_time + timedelta(minutes=interval_minutes * clip_index)
        else:
            # Post immediately
            schedule_time = base_time + timedelta(minutes=5)  # Small delay for processing

        return schedule_time

    def create_social_posts_for_clip(self, clip: Clip, clip_index: int = 0) -> List[str]:
        """Create scheduled social media posts for a single clip"""
        if not clip.file_path:
            logger.warning(f"Clip {clip.id} has no file path, skipping social posts")
            return []

        social_accounts = self.get_social_accounts()
        if not social_accounts:
            logger.warning(f"No social accounts found for video request {self.video_request.id}")
            return []

        created_post_ids = []
        base_schedule_time = timezone.now()

        for account_index, social_account in enumerate(social_accounts):
            try:
                platform_name = social_account.platform.display_name
                caption = self.generate_clip_caption(clip, platform_name)
                hashtags = self.generate_hashtags(clip, social_account.platform.name)

                # Calculate schedule time (stagger posts across platforms)
                schedule_time = self.calculate_schedule_time(
                    clip_index * len(social_accounts) + account_index,
                    base_schedule_time
                )

                # Create scheduled post
                scheduled_post = ScheduledPost.objects.create(
                    user=self.user,
                    social_account=social_account,
                    video_url=clip.file_path.url if clip.file_path else "",
                    caption=caption,
                    hashtags=hashtags,
                    scheduled_time=schedule_time,
                    status='scheduled' if self.video_request.schedule_posts else 'pending',
                    priority=2,
                    platform_response={
                        'source': 'video_processing',
                        'video_request_id': self.video_request.id,
                        'clip_id': clip.id,
                        'engagement_score': clip.engagement_score,
                        'clip_duration': clip.duration,
                        'auto_generated': True
                    }
                )

                created_post_ids.append(str(scheduled_post.id))

                logger.info(
                    f"Created social post {scheduled_post.id} for clip {clip.id} "
                    f"on {platform_name} scheduled for {schedule_time}"
                )

                # If not scheduling, trigger immediate publish
                if not self.video_request.schedule_posts:
                    publish_single_post.delay(str(scheduled_post.id))

            except Exception as e:
                logger.error(f"Error creating social post for clip {clip.id} on {social_account.platform.name}: {e}")
                continue

        return created_post_ids

    def create_social_posts_for_all_clips(self) -> Dict[str, Any]:
        """Create social media posts for all completed clips"""
        if not self.should_auto_post():
            return {'success': False, 'reason': 'Auto-posting not enabled or no social accounts'}

        # Get completed clips that haven't been posted yet
        clips = self.video_request.clips.filter(
            status='done',
            social_posts_created=False
        ).order_by('-engagement_score', 'start_time')  # Best clips first

        if not clips:
            return {'success': False, 'reason': 'No completed clips available for posting'}

        total_posts_created = 0
        clips_processed = 0

        for clip_index, clip in enumerate(clips):
            try:
                post_ids = self.create_social_posts_for_clip(clip, clip_index)

                if post_ids:
                    # Update clip with social posting info
                    clip.social_posts_created = True
                    clip.social_post_ids = post_ids
                    clip.auto_post_status = 'scheduled' if self.video_request.schedule_posts else 'posted'
                    clip.save()

                    total_posts_created += len(post_ids)
                    clips_processed += 1

                    logger.info(f"Created {len(post_ids)} social posts for clip {clip.id}")

            except Exception as e:
                logger.error(f"Error processing clip {clip.id} for social posting: {e}")
                clip.auto_post_status = 'failed'
                clip.save()

        return {
            'success': True,
            'clips_processed': clips_processed,
            'total_posts_created': total_posts_created,
            'schedule_type': 'scheduled' if self.video_request.schedule_posts else 'immediate'
        }

    def get_posting_status(self) -> Dict[str, Any]:
        """Get status of social media posting for this video request"""
        clips = self.video_request.clips.all()
        total_clips = clips.count()
        clips_with_posts = clips.filter(social_posts_created=True).count()
        clips_posted = clips.filter(auto_post_status='posted').count()
        clips_scheduled = clips.filter(auto_post_status='scheduled').count()
        clips_failed = clips.filter(auto_post_status='failed').count()

        return {
            'auto_posting_enabled': self.video_request.auto_post_to_social,
            'connected_accounts': self.video_request.social_accounts.count(),
            'total_clips': total_clips,
            'clips_with_posts': clips_with_posts,
            'clips_posted': clips_posted,
            'clips_scheduled': clips_scheduled,
            'clips_failed': clips_failed,
            'posting_complete': clips_with_posts == total_clips if total_clips > 0 else False
        }


def trigger_social_posting_for_video_request(video_request_id: int) -> Dict[str, Any]:
    """
    Trigger social media posting for a completed video request
    This function should be called when video processing is complete
    """
    try:
        video_request = VideoRequest.objects.get(id=video_request_id)
        integration_service = SocialMediaIntegrationService(video_request)

        if not integration_service.should_auto_post():
            return {'success': False, 'reason': 'Auto-posting not configured'}

        result = integration_service.create_social_posts_for_all_clips()

        logger.info(
            f"Social media integration completed for video request {video_request_id}: {result}"
        )

        return result

    except VideoRequest.DoesNotExist:
        logger.error(f"Video request {video_request_id} not found")
        return {'success': False, 'reason': 'Video request not found'}

    except Exception as e:
        logger.error(f"Error in social media integration for video request {video_request_id}: {e}")
        return {'success': False, 'reason': str(e)}