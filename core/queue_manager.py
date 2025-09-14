"""
Queue management system for video processing tasks
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from core.models import ProcessingQueue, QueueStats, NotificationEvent, UserCredits
from clipper.tasks.tasks import process_video_with_custom_settings

logger = logging.getLogger(__name__)


class QueueManager:
    """Manages video processing queue with priority-based scheduling"""

    @classmethod
    def add_to_queue(cls, video_request, processing_settings=None):
        """Add a video request to the processing queue"""

        # Determine user priority based on plan
        user_priority = cls.get_user_priority(video_request.user)

        # Create queue entry
        with transaction.atomic():
            queue_entry = ProcessingQueue.objects.create(
                video_request=video_request,
                user=video_request.user,
                priority=user_priority,
                processing_settings=processing_settings or {},
                estimated_duration=cls.estimate_processing_time(video_request, processing_settings)
            )

            # Update video request status
            video_request.status = 'pending'
            video_request.save()

            logger.info(f"Added video request {video_request.id} to queue with priority {user_priority}")

            # Schedule notification for queue position
            cls.schedule_notification(
                queue_entry,
                'queue_added',
                f"Your video has been added to the processing queue. Position: #{queue_entry.queue_position}"
            )

            return queue_entry

    @classmethod
    def get_user_priority(cls, user):
        """Determine user's processing priority based on their plan"""
        try:
            user_credits = UserCredits.objects.get(user=user)
            plan_name = user_credits.plan.name if user_credits.plan else 'free'

            priority_map = {
                'free': 1,      # Low priority
                'pro': 2,       # Normal priority
                'premium': 3,   # High priority
            }

            return priority_map.get(plan_name, 1)

        except UserCredits.DoesNotExist:
            return 1  # Default to free tier priority

    @classmethod
    def estimate_processing_time(cls, video_request, processing_settings=None):
        """Estimate processing time based on settings"""
        base_time = 3.0  # 3 minutes base time

        if processing_settings:
            # Add time for AI processing
            if processing_settings.get('moment_detection_type') == 'ai_powered':
                base_time += 2.0

            # Add time for higher quality
            quality = processing_settings.get('video_quality', '720p')
            quality_multiplier = {
                '480p': 0.7,
                '720p': 1.0,
                '1080p': 1.5,
                '1440p': 2.2,
                '2160p': 3.5
            }.get(quality, 1.0)

            base_time *= quality_multiplier

            # Add time for more clips
            max_clips = processing_settings.get('max_clips', 10)
            base_time += max_clips * 0.2  # 0.2 minutes per clip

        return base_time

    @classmethod
    def get_next_task(cls):
        """Get the next task to process based on priority"""
        return ProcessingQueue.objects.filter(
            status='queued'
        ).first()  # Already ordered by priority, then queued_at

    @classmethod
    def start_processing(cls, queue_entry, worker_id='default'):
        """Mark a task as started"""
        with transaction.atomic():
            queue_entry.status = 'processing'
            queue_entry.started_at = timezone.now()
            queue_entry.worker_id = worker_id
            queue_entry.save()

            # Update video request status
            queue_entry.video_request.status = 'processing'
            queue_entry.video_request.save()

            logger.info(f"Started processing queue entry {queue_entry.id} with worker {worker_id}")

            # Send notification
            cls.schedule_notification(
                queue_entry,
                'processing_started',
                f"Your video is now being processed. Estimated completion time: {queue_entry.estimated_duration:.1f} minutes"
            )

    @classmethod
    def complete_processing(cls, queue_entry, success=True, error_message=None):
        """Mark a task as completed"""
        with transaction.atomic():
            queue_entry.status = 'completed' if success else 'failed'
            queue_entry.completed_at = timezone.now()
            queue_entry.error_message = error_message or ''

            # Calculate actual duration
            if queue_entry.started_at:
                duration = (queue_entry.completed_at - queue_entry.started_at).total_seconds() / 60
                queue_entry.actual_duration = duration

            queue_entry.save()

            # Update video request status
            queue_entry.video_request.status = 'done' if success else 'failed'
            queue_entry.video_request.save()

            logger.info(f"Completed processing queue entry {queue_entry.id} - Success: {success}")

            # Send completion notification
            if success:
                message = f"Your video has been processed successfully! {queue_entry.video_request.clips.count()} clips are ready for download."
                cls.schedule_notification(queue_entry, 'processing_completed', message)
            else:
                message = f"Video processing failed: {error_message}"
                cls.schedule_notification(queue_entry, 'processing_failed', message)

            # Update daily stats
            cls.update_daily_stats(queue_entry)

    @classmethod
    def schedule_notification(cls, queue_entry, event_type, message):
        """Schedule a notification for a queue event"""
        try:
            NotificationEvent.objects.create(
                user=queue_entry.user,
                queue_entry=queue_entry,
                event_type=event_type,
                notification_type='email',
                subject=f"Video Processing Update - {event_type.replace('_', ' ').title()}",
                message=message,
                recipient=queue_entry.user.email
            )
            logger.info(f"Scheduled {event_type} notification for user {queue_entry.user.email}")
        except Exception as e:
            logger.error(f"Failed to schedule notification: {e}")

    @classmethod
    def process_notifications(cls):
        """Process pending notifications (call this periodically)"""
        pending_notifications = NotificationEvent.objects.filter(
            status='pending',
            notification_type='email'
        )[:10]  # Process 10 at a time

        for notification in pending_notifications:
            try:
                send_mail(
                    subject=notification.subject,
                    message=notification.message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[notification.recipient],
                    fail_silently=False
                )

                notification.status = 'sent'
                notification.sent_at = timezone.now()
                notification.save()

                logger.info(f"Sent email notification to {notification.recipient}")

            except Exception as e:
                notification.status = 'failed'
                notification.error_message = str(e)
                notification.save()
                logger.error(f"Failed to send email to {notification.recipient}: {e}")

    @classmethod
    def update_daily_stats(cls, queue_entry):
        """Update daily queue statistics"""
        today = timezone.now().date()

        stats, created = QueueStats.objects.get_or_create(
            date=today,
            defaults={
                'total_queued': 0,
                'total_processed': 0,
                'total_failed': 0,
                'avg_wait_time': 0.0,
                'avg_processing_time': 0.0,
                'max_queue_length': 0
            }
        )

        # Update counts
        if queue_entry.status == 'completed':
            stats.total_processed += 1

            # Update user tier stats
            user_priority = cls.get_user_priority(queue_entry.user)
            if user_priority == 1:
                stats.free_users_processed += 1
            elif user_priority == 2:
                stats.pro_users_processed += 1
            elif user_priority == 3:
                stats.premium_users_processed += 1

        elif queue_entry.status == 'failed':
            stats.total_failed += 1

        # Update timing averages (simplified - could be more sophisticated)
        if queue_entry.actual_duration:
            current_avg = stats.avg_processing_time
            total_processed = stats.total_processed
            stats.avg_processing_time = ((current_avg * (total_processed - 1)) + queue_entry.actual_duration) / total_processed

        stats.save()

    @classmethod
    def get_queue_status(cls, user=None):
        """Get current queue status"""
        if user:
            # Get user's queue entries
            user_entries = ProcessingQueue.objects.filter(user=user).order_by('-queued_at')[:5]

            return {
                'user_queue': [{
                    'id': entry.id,
                    'status': entry.status,
                    'position': entry.queue_position,
                    'estimated_wait': entry.estimated_wait_time,
                    'queued_at': entry.queued_at,
                    'video_url': entry.video_request.url
                } for entry in user_entries],
                'queue_length': ProcessingQueue.objects.filter(status='queued').count(),
                'processing_count': ProcessingQueue.objects.filter(status='processing').count()
            }
        else:
            # Global queue status
            return {
                'total_queued': ProcessingQueue.objects.filter(status='queued').count(),
                'total_processing': ProcessingQueue.objects.filter(status='processing').count(),
                'queue_by_priority': {
                    'free': ProcessingQueue.objects.filter(status='queued', priority=1).count(),
                    'pro': ProcessingQueue.objects.filter(status='queued', priority=2).count(),
                    'premium': ProcessingQueue.objects.filter(status='queued', priority=3).count(),
                },
                'average_wait_time': cls.get_average_wait_time()
            }

    @classmethod
    def get_average_wait_time(cls):
        """Calculate current average wait time"""
        recent_completed = ProcessingQueue.objects.filter(
            status='completed',
            completed_at__gte=timezone.now() - timedelta(hours=24)
        )

        if not recent_completed:
            return 5.0  # Default 5 minutes

        total_time = sum([
            (entry.completed_at - entry.queued_at).total_seconds() / 60
            for entry in recent_completed
            if entry.completed_at and entry.queued_at
        ])

        return total_time / len(recent_completed) if recent_completed else 5.0

    @classmethod
    def cancel_task(cls, queue_entry):
        """Cancel a queued task"""
        if queue_entry.status in ['queued', 'processing']:
            queue_entry.status = 'cancelled'
            queue_entry.completed_at = timezone.now()
            queue_entry.save()

            # Update video request
            queue_entry.video_request.status = 'failed'  # or 'cancelled' if you add this status
            queue_entry.video_request.save()

            logger.info(f"Cancelled queue entry {queue_entry.id}")
            return True
        return False

    @classmethod
    def retry_failed_task(cls, queue_entry):
        """Retry a failed task"""
        if queue_entry.status == 'failed' and queue_entry.retry_count < queue_entry.max_retries:
            queue_entry.status = 'queued'
            queue_entry.retry_count += 1
            queue_entry.error_message = ''
            queue_entry.started_at = None
            queue_entry.completed_at = None
            queue_entry.save()

            logger.info(f"Retrying queue entry {queue_entry.id} (attempt {queue_entry.retry_count})")
            return True
        return False


# Celery task integration
def process_queue_entry(queue_entry_id):
    """Process a queue entry (called by Celery worker)"""
    try:
        queue_entry = ProcessingQueue.objects.get(id=queue_entry_id)

        # Start processing
        QueueManager.start_processing(queue_entry)

        # Process the video
        result = process_video_with_custom_settings.delay(
            queue_entry.video_request.id,
            **queue_entry.processing_settings
        )

        # Wait for result (or handle async)
        # This is simplified - in production you'd handle this differently

        QueueManager.complete_processing(queue_entry, success=True)

    except Exception as e:
        logger.error(f"Failed to process queue entry {queue_entry_id}: {e}")
        QueueManager.complete_processing(queue_entry, success=False, error_message=str(e))