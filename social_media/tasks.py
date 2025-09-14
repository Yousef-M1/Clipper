"""
Celery tasks for social media publishing
Handles scheduled posting, analytics updates, and maintenance tasks
"""

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

from .models import ScheduledPost, SocialAccount, PostAnalytics, WebhookEvent
from .services import SocialMediaPublishingService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_scheduled_posts(self):
    """Process all due scheduled posts"""
    try:
        # Get all posts that are due for posting
        due_posts = ScheduledPost.objects.filter(
            status='scheduled',
            scheduled_time__lte=timezone.now()
        ).select_related('social_account', 'user')

        processed_count = 0
        failed_count = 0

        for post in due_posts:
            try:
                with transaction.atomic():
                    success = SocialMediaPublishingService.publish_scheduled_post(post)
                    if success:
                        processed_count += 1
                    else:
                        failed_count += 1

            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing scheduled post {post.id}: {e}")

        logger.info(f"Processed {processed_count} posts, {failed_count} failed")
        return {
            'processed': processed_count,
            'failed': failed_count,
            'total': len(due_posts)
        }

    except Exception as e:
        logger.error(f"Error in process_scheduled_posts: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def publish_single_post(self, scheduled_post_id):
    """Publish a single scheduled post"""
    try:
        post = ScheduledPost.objects.select_related('social_account').get(
            id=scheduled_post_id
        )

        success = SocialMediaPublishingService.publish_scheduled_post(post)

        if success:
            logger.info(f"Successfully published post {scheduled_post_id}")
            return {'status': 'success', 'post_id': scheduled_post_id}
        else:
            logger.warning(f"Failed to publish post {scheduled_post_id}")
            return {'status': 'failed', 'post_id': scheduled_post_id}

    except ScheduledPost.DoesNotExist:
        logger.error(f"Scheduled post {scheduled_post_id} not found")
        return {'status': 'not_found', 'post_id': scheduled_post_id}

    except Exception as e:
        logger.error(f"Error publishing post {scheduled_post_id}: {e}")

        # Retry with exponential backoff
        countdown = (2 ** self.request.retries) * 60  # 1min, 2min, 4min
        raise self.retry(exc=e, countdown=countdown)


@shared_task(bind=True)
def retry_failed_posts(self):
    """Retry failed posts that can be retried"""
    try:
        # Get failed posts that can be retried
        failed_posts = ScheduledPost.objects.filter(
            status='failed',
            retry_count__lt=models.F('max_retries'),
            scheduled_time__gte=timezone.now() - timedelta(hours=24)  # Only retry recent fails
        ).select_related('social_account')

        retry_count = 0

        for post in failed_posts:
            if post.can_retry():
                # Reset status and schedule for retry
                post.status = 'scheduled'
                post.scheduled_time = timezone.now() + timedelta(minutes=5)  # Retry in 5 minutes
                post.save()

                # Schedule the retry task
                publish_single_post.apply_async(
                    args=[post.id],
                    countdown=300  # 5 minutes
                )

                retry_count += 1
                logger.info(f"Scheduled retry for post {post.id}")

        return {'retried': retry_count}

    except Exception as e:
        logger.error(f"Error in retry_failed_posts: {e}")
        raise


@shared_task(bind=True)
def update_analytics_batch(self):
    """Update analytics for recently posted content"""
    try:
        # Get posts from last 7 days that need analytics updates
        cutoff_date = timezone.now() - timedelta(days=7)

        posts_to_update = ScheduledPost.objects.filter(
            status='posted',
            posted_at__gte=cutoff_date,
            platform_post_id__isnull=False
        ).select_related('social_account').prefetch_related('analytics')

        updated_count = 0

        for post in posts_to_update:
            try:
                SocialMediaPublishingService.update_post_analytics(post)
                updated_count += 1

                # Rate limiting - small delay between updates
                import time
                time.sleep(1)

            except Exception as e:
                logger.error(f"Failed to update analytics for post {post.id}: {e}")
                continue

        logger.info(f"Updated analytics for {updated_count} posts")
        return {'updated': updated_count}

    except Exception as e:
        logger.error(f"Error in update_analytics_batch: {e}")
        raise


@shared_task(bind=True)
def refresh_expiring_tokens(self):
    """Refresh access tokens that are about to expire"""
    try:
        # Get accounts with tokens expiring in next 6 hours
        expiring_soon = timezone.now() + timedelta(hours=6)

        accounts_to_refresh = SocialAccount.objects.filter(
            status='connected',
            token_expires_at__lte=expiring_soon,
            token_expires_at__isnull=False
        )

        refreshed_count = 0
        failed_count = 0

        for account in accounts_to_refresh:
            try:
                SocialMediaPublishingService.refresh_account_token(account)
                refreshed_count += 1
                logger.info(f"Refreshed token for {account}")

            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to refresh token for {account}: {e}")

        return {
            'refreshed': refreshed_count,
            'failed': failed_count,
            'total': len(accounts_to_refresh)
        }

    except Exception as e:
        logger.error(f"Error in refresh_expiring_tokens: {e}")
        raise


@shared_task(bind=True)
def cleanup_old_posts(self):
    """Clean up old completed and failed posts"""
    try:
        # Clean up completed posts older than 90 days
        completed_cutoff = timezone.now() - timedelta(days=90)
        deleted_completed = ScheduledPost.objects.filter(
            status='posted',
            posted_at__lt=completed_cutoff
        ).delete()

        # Clean up failed posts older than 30 days
        failed_cutoff = timezone.now() - timedelta(days=30)
        deleted_failed = ScheduledPost.objects.filter(
            status='failed',
            updated_at__lt=failed_cutoff
        ).delete()

        # Clean up old webhook events (keep 14 days)
        webhook_cutoff = timezone.now() - timedelta(days=14)
        deleted_webhooks = WebhookEvent.objects.filter(
            created_at__lt=webhook_cutoff
        ).delete()

        logger.info(f"Cleanup: {deleted_completed[0]} completed, {deleted_failed[0]} failed posts, {deleted_webhooks[0]} webhooks")

        return {
            'deleted_completed': deleted_completed[0],
            'deleted_failed': deleted_failed[0],
            'deleted_webhooks': deleted_webhooks[0]
        }

    except Exception as e:
        logger.error(f"Error in cleanup_old_posts: {e}")
        raise


@shared_task(bind=True)
def generate_content_suggestions(self, user_id):
    """Generate content suggestions for a user based on their posting history"""
    try:
        from django.contrib.auth import get_user_model
        from collections import Counter

        User = get_user_model()
        user = User.objects.get(id=user_id)

        # Analyze user's posting patterns
        recent_posts = ScheduledPost.objects.filter(
            user=user,
            posted_at__gte=timezone.now() - timedelta(days=30)
        ).prefetch_related('analytics')

        if not recent_posts.exists():
            return {'suggestions': []}

        # Analyze hashtags
        all_hashtags = []
        for post in recent_posts:
            all_hashtags.extend(post.hashtags)

        top_hashtags = [tag for tag, count in Counter(all_hashtags).most_common(10)]

        # Analyze performance
        high_performing_posts = [
            post for post in recent_posts
            if hasattr(post, 'analytics') and post.analytics.engagement_rate > 5.0
        ]

        suggestions = []

        if top_hashtags:
            suggestions.append({
                'type': 'hashtags',
                'title': 'Your top performing hashtags',
                'data': top_hashtags
            })

        if high_performing_posts:
            best_times = [post.posted_at.hour for post in high_performing_posts]
            optimal_hour = Counter(best_times).most_common(1)[0][0]

            suggestions.append({
                'type': 'timing',
                'title': f'Post around {optimal_hour:02d}:00 for better engagement',
                'data': {'optimal_hour': optimal_hour}
            })

        return {'suggestions': suggestions, 'user_id': user_id}

    except Exception as e:
        logger.error(f"Error generating content suggestions for user {user_id}: {e}")
        raise


@shared_task(bind=True)
def process_webhook_events(self):
    """Process pending webhook events from social platforms"""
    try:
        pending_events = WebhookEvent.objects.filter(
            processed=False,
            created_at__gte=timezone.now() - timedelta(hours=24)  # Only process recent events
        ).select_related('social_account')

        processed_count = 0

        for event in pending_events:
            try:
                success = process_single_webhook_event(event)
                if success:
                    processed_count += 1

            except Exception as e:
                logger.error(f"Error processing webhook event {event.id}: {e}")

        return {'processed': processed_count}

    except Exception as e:
        logger.error(f"Error in process_webhook_events: {e}")
        raise


def process_single_webhook_event(webhook_event: WebhookEvent) -> bool:
    """Process a single webhook event"""
    try:
        event_type = webhook_event.event_type
        event_data = webhook_event.event_data

        if event_type == 'post_published':
            # Handle successful post publication
            post_id = event_data.get('post_id')
            if post_id:
                try:
                    scheduled_post = ScheduledPost.objects.get(
                        platform_post_id=post_id,
                        social_account=webhook_event.social_account
                    )
                    scheduled_post.status = 'posted'
                    scheduled_post.posted_at = timezone.now()
                    scheduled_post.save()
                except ScheduledPost.DoesNotExist:
                    pass

        elif event_type == 'post_failed':
            # Handle post failure
            post_id = event_data.get('post_id')
            error_message = event_data.get('error', 'Unknown error')

            if post_id:
                try:
                    scheduled_post = ScheduledPost.objects.get(
                        platform_post_id=post_id,
                        social_account=webhook_event.social_account
                    )
                    scheduled_post.status = 'failed'
                    scheduled_post.error_message = error_message
                    scheduled_post.save()
                except ScheduledPost.DoesNotExist:
                    pass

        elif event_type == 'analytics_update':
            # Handle analytics update
            post_id = event_data.get('post_id')
            metrics = event_data.get('metrics', {})

            if post_id:
                try:
                    scheduled_post = ScheduledPost.objects.get(
                        platform_post_id=post_id,
                        social_account=webhook_event.social_account
                    )

                    analytics, created = PostAnalytics.objects.get_or_create(
                        scheduled_post=scheduled_post,
                        defaults={'platform_metrics': metrics}
                    )

                    if not created:
                        analytics.platform_metrics.update(metrics)
                        analytics.save()

                except ScheduledPost.DoesNotExist:
                    pass

        elif event_type == 'account_deauthorized':
            # Handle account deauthorization
            webhook_event.social_account.status = 'disconnected'
            webhook_event.social_account.error_message = 'Account deauthorized by user'
            webhook_event.social_account.save()

        elif event_type == 'rate_limit_exceeded':
            # Handle rate limiting
            webhook_event.social_account.status = 'error'
            webhook_event.social_account.error_message = 'Rate limit exceeded'
            webhook_event.social_account.save()

        # Mark event as processed
        webhook_event.processed = True
        webhook_event.processed_at = timezone.now()
        webhook_event.save()

        return True

    except Exception as e:
        webhook_event.error_message = str(e)
        webhook_event.save()
        logger.error(f"Error processing webhook event {webhook_event.id}: {e}")
        return False


# Periodic task configuration (add to your CELERY_BEAT_SCHEDULE)
"""
CELERY_BEAT_SCHEDULE.update({
    'process-scheduled-posts': {
        'task': 'social_media.tasks.process_scheduled_posts',
        'schedule': 60.0,  # Every minute
    },
    'retry-failed-posts': {
        'task': 'social_media.tasks.retry_failed_posts',
        'schedule': 300.0,  # Every 5 minutes
    },
    'update-analytics': {
        'task': 'social_media.tasks.update_analytics_batch',
        'schedule': 3600.0,  # Every hour
    },
    'refresh-tokens': {
        'task': 'social_media.tasks.refresh_expiring_tokens',
        'schedule': 1800.0,  # Every 30 minutes
    },
    'cleanup-old-posts': {
        'task': 'social_media.tasks.cleanup_old_posts',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'process-webhooks': {
        'task': 'social_media.tasks.process_webhook_events',
        'schedule': 120.0,  # Every 2 minutes
    },
})
"""