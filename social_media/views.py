"""
Social Media Publishing API Views
REST API endpoints for managing social media connections and publishing
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta
import uuid

from core.throttling import PlanBasedThrottle
from .models import (
    SocialPlatform, SocialAccount, ScheduledPost,
    PostTemplate, PostAnalytics, ContentCalendar
)
from .services import SocialMediaPublishingService
from .tasks import publish_single_post, generate_content_suggestions
from .serializers import (
    SocialAccountSerializer, ScheduledPostSerializer,
    PostTemplateSerializer, PostAnalyticsSerializer,
    ContentCalendarSerializer
)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_supported_platforms(request):
    """Get list of supported social media platforms"""
    platforms = SocialPlatform.objects.filter(is_active=True)

    platform_data = []
    for platform in platforms:
        platform_data.append({
            'id': platform.id,
            'name': platform.name,
            'display_name': platform.display_name,
            'capabilities': {
                'max_video_duration': platform.max_video_duration,
                'max_file_size_mb': platform.max_file_size_mb,
                'supported_formats': platform.supported_formats,
                'aspect_ratios': platform.aspect_ratios,
                'supports_scheduling': platform.supports_scheduling,
                'supports_analytics': platform.supports_analytics,
                'supports_captions': platform.supports_captions,
                'supports_hashtags': platform.supports_hashtags,
            }
        })

    return Response({
        'platforms': platform_data,
        'total': len(platform_data)
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_connected_accounts(request):
    """Get user's connected social media accounts"""
    accounts = SocialAccount.objects.filter(user=request.user).select_related('platform')
    serializer = SocialAccountSerializer(accounts, many=True)

    return Response({
        'accounts': serializer.data,
        'total': len(serializer.data)
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([PlanBasedThrottle])
def connect_social_account(request):
    """Connect a social media account via OAuth"""
    try:
        platform_name = request.data.get('platform')
        auth_code = request.data.get('auth_code')
        redirect_uri = request.data.get('redirect_uri')

        if not all([platform_name, auth_code]):
            return Response({
                'error': 'platform and auth_code are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get platform
        try:
            platform = SocialPlatform.objects.get(name=platform_name, is_active=True)
        except SocialPlatform.DoesNotExist:
            return Response({
                'error': f'Platform {platform_name} not supported'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create temporary social account for authentication
        temp_account = SocialAccount(platform=platform, user=request.user, access_token='temp')
        publisher = SocialMediaPublishingService.get_publisher(temp_account)

        # Exchange auth code for tokens
        token_data = publisher.authenticate(auth_code)

        # Get user info from platform
        temp_account.access_token = token_data['access_token']
        user_info = publisher.get_user_info()

        # Create or update social account
        account_data = {
            'user': request.user,
            'platform': platform,
            'account_id': user_info.get('id', ''),
            'username': user_info.get('username', ''),
            'display_name': user_info.get('display_name', ''),
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token', ''),
            'scope': token_data.get('scope', ''),
            'status': 'connected'
        }

        # Set token expiration
        if 'expires_in' in token_data:
            account_data['token_expires_at'] = timezone.now() + timedelta(
                seconds=token_data['expires_in']
            )

        # Update user info if available
        if 'followers_count' in user_info:
            account_data['follower_count'] = user_info['followers_count']
        if 'is_verified' in user_info:
            account_data['is_verified'] = user_info['is_verified']
        if 'account_type' in user_info:
            account_data['is_business_account'] = user_info['account_type'] in ['BUSINESS', 'CREATOR']

        # Create or update account
        social_account, created = SocialAccount.objects.update_or_create(
            user=request.user,
            platform=platform,
            account_id=account_data['account_id'],
            defaults=account_data
        )

        serializer = SocialAccountSerializer(social_account)

        return Response({
            'account': serializer.data,
            'message': f'Successfully connected {platform.display_name} account',
            'created': created
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'Failed to connect account: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def disconnect_social_account(request, account_id):
    """Disconnect a social media account"""
    try:
        account = get_object_or_404(
            SocialAccount,
            id=account_id,
            user=request.user
        )

        platform_name = account.platform.display_name

        # Cancel any scheduled posts for this account
        ScheduledPost.objects.filter(
            social_account=account,
            status__in=['draft', 'scheduled']
        ).update(status='cancelled')

        # Delete the account
        account.delete()

        return Response({
            'message': f'Successfully disconnected {platform_name} account'
        })

    except Exception as e:
        return Response({
            'error': f'Failed to disconnect account: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([PlanBasedThrottle])
def schedule_post(request):
    """Schedule a post to social media"""
    try:
        # Required fields
        social_account_id = request.data.get('social_account_id')
        scheduled_time = request.data.get('scheduled_time')

        # Content fields
        video_url = request.data.get('video_url')
        caption = request.data.get('caption', '')
        hashtags = request.data.get('hashtags', [])

        if not all([social_account_id, scheduled_time]):
            return Response({
                'error': 'social_account_id and scheduled_time are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get social account
        try:
            social_account = SocialAccount.objects.get(
                id=social_account_id,
                user=request.user,
                status='connected'
            )
        except SocialAccount.DoesNotExist:
            return Response({
                'error': 'Social account not found or not connected'
            }, status=status.HTTP_404_NOT_FOUND)

        # Parse scheduled time
        try:
            scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
        except ValueError:
            return Response({
                'error': 'Invalid scheduled_time format. Use ISO format.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate scheduled time is in future
        if scheduled_dt <= timezone.now():
            return Response({
                'error': 'Scheduled time must be in the future'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create scheduled post
        scheduled_post = ScheduledPost.objects.create(
            user=request.user,
            social_account=social_account,
            video_url=video_url,
            caption=caption,
            hashtags=hashtags if isinstance(hashtags, list) else [],
            scheduled_time=scheduled_dt,
            status='scheduled',
            priority=request.data.get('priority', 2)
        )

        serializer = ScheduledPostSerializer(scheduled_post)

        return Response({
            'post': serializer.data,
            'message': f'Post scheduled for {scheduled_dt}'
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            'error': f'Failed to schedule post: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([PlanBasedThrottle])
def publish_now(request):
    """Publish content immediately"""
    try:
        # This creates a scheduled post with immediate time and triggers publishing
        request.data['scheduled_time'] = timezone.now().isoformat()

        # Create the scheduled post
        response_data = schedule_post(request)

        if response_data.status_code != 201:
            return response_data

        # Get the created post ID and trigger immediate publishing
        post_id = response_data.data['post']['id']

        # Trigger async publishing task
        publish_single_post.apply_async(args=[post_id], countdown=5)  # 5 seconds delay

        return Response({
            'post': response_data.data['post'],
            'message': 'Publishing started - check status in a few moments'
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        return Response({
            'error': f'Failed to publish immediately: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_scheduled_posts(request):
    """Get user's scheduled posts"""
    # Filter parameters
    platform = request.GET.get('platform')
    status_filter = request.GET.get('status')
    limit = int(request.GET.get('limit', 20))

    posts = ScheduledPost.objects.filter(user=request.user).select_related(
        'social_account', 'social_account__platform'
    ).prefetch_related('analytics')

    # Apply filters
    if platform:
        posts = posts.filter(social_account__platform__name=platform)

    if status_filter:
        posts = posts.filter(status=status_filter)

    # Order by scheduled time
    posts = posts.order_by('-scheduled_time')[:limit]

    serializer = ScheduledPostSerializer(posts, many=True)

    return Response({
        'posts': serializer.data,
        'total': len(serializer.data)
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def cancel_scheduled_post(request, post_id):
    """Cancel a scheduled post"""
    try:
        post = get_object_or_404(
            ScheduledPost,
            id=post_id,
            user=request.user,
            status__in=['draft', 'scheduled']
        )

        post.status = 'cancelled'
        post.save()

        return Response({
            'message': 'Post cancelled successfully'
        })

    except Exception as e:
        return Response({
            'error': f'Failed to cancel post: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def retry_failed_post(request, post_id):
    """Retry a failed post"""
    try:
        post = get_object_or_404(
            ScheduledPost,
            id=post_id,
            user=request.user,
            status='failed'
        )

        if not post.can_retry():
            return Response({
                'error': 'Post cannot be retried (max retries exceeded)'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Reset status and schedule for immediate retry
        post.status = 'scheduled'
        post.scheduled_time = timezone.now() + timedelta(minutes=1)
        post.error_message = ''
        post.save()

        # Trigger retry task
        publish_single_post.apply_async(args=[post_id], countdown=60)

        return Response({
            'message': 'Post scheduled for retry'
        })

    except Exception as e:
        return Response({
            'error': f'Failed to retry post: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_post_analytics(request, post_id):
    """Get analytics for a specific post"""
    try:
        post = get_object_or_404(
            ScheduledPost,
            id=post_id,
            user=request.user,
            status='posted'
        )

        if not hasattr(post, 'analytics'):
            return Response({
                'error': 'Analytics not available for this post'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = PostAnalyticsSerializer(post.analytics)

        return Response({
            'analytics': serializer.data,
            'post_info': {
                'id': post.id,
                'platform': post.social_account.platform.display_name,
                'posted_at': post.posted_at,
                'caption': post.caption
            }
        })

    except Exception as e:
        return Response({
            'error': f'Failed to get analytics: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_dashboard_summary(request):
    """Get social media dashboard summary"""
    try:
        # Get user's accounts and posts
        accounts = SocialAccount.objects.filter(user=request.user).select_related('platform')

        # Posts in last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_posts = ScheduledPost.objects.filter(
            user=request.user,
            created_at__gte=thirty_days_ago
        )

        # Summary stats
        summary = {
            'connected_accounts': accounts.count(),
            'accounts_by_platform': {},
            'total_posts': recent_posts.count(),
            'posts_by_status': {},
            'top_performing_posts': [],
            'upcoming_posts': [],
        }

        # Account breakdown by platform
        for account in accounts:
            platform = account.platform.display_name
            if platform not in summary['accounts_by_platform']:
                summary['accounts_by_platform'][platform] = []

            summary['accounts_by_platform'][platform].append({
                'id': account.id,
                'username': account.username,
                'status': account.status,
                'follower_count': account.follower_count
            })

        # Posts by status
        status_counts = recent_posts.values('status').annotate(count=Count('status'))
        for item in status_counts:
            summary['posts_by_status'][item['status']] = item['count']

        # Upcoming posts (next 7 days)
        next_week = timezone.now() + timedelta(days=7)
        upcoming = ScheduledPost.objects.filter(
            user=request.user,
            status='scheduled',
            scheduled_time__lte=next_week
        ).order_by('scheduled_time')[:5]

        summary['upcoming_posts'] = ScheduledPostSerializer(upcoming, many=True).data

        # Top performing posts (with analytics)
        top_posts = ScheduledPost.objects.filter(
            user=request.user,
            status='posted',
            posted_at__gte=thirty_days_ago
        ).prefetch_related('analytics').order_by('-analytics__engagement_rate')[:5]

        if top_posts:
            summary['top_performing_posts'] = ScheduledPostSerializer(top_posts, many=True).data

        return Response(summary)

    except Exception as e:
        return Response({
            'error': f'Failed to get dashboard summary: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([PlanBasedThrottle])
def get_content_suggestions(request):
    """Get AI-powered content suggestions for user"""
    try:
        # Trigger async task to generate suggestions
        task = generate_content_suggestions.apply_async(args=[request.user.id])

        return Response({
            'message': 'Generating content suggestions...',
            'task_id': task.id,
            'check_status_url': f'/api/social/suggestions/status/{task.id}/'
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        return Response({
            'error': f'Failed to generate suggestions: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_suggestion_status(request, task_id):
    """Check status of content suggestion generation"""
    try:
        from celery.result import AsyncResult

        task_result = AsyncResult(task_id)

        if task_result.ready():
            if task_result.successful():
                return Response({
                    'status': 'completed',
                    'result': task_result.result
                })
            else:
                return Response({
                    'status': 'failed',
                    'error': str(task_result.result)
                })
        else:
            return Response({
                'status': 'pending',
                'message': 'Still generating suggestions...'
            })

    except Exception as e:
        return Response({
            'error': f'Failed to check status: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Template management views
class PostTemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = PostTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.post_templates.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PostTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PostTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.post_templates.all()


# Content calendar views
class ContentCalendarListCreateView(generics.ListCreateAPIView):
    serializer_class = ContentCalendarSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.content_calendars.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ContentCalendarDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContentCalendarSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.content_calendars.all()