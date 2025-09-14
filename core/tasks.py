"""
Celery tasks for queue management and notifications
"""

from celery import shared_task
from django.utils import timezone
from core.models import ProcessingQueue, NotificationEvent
from core.queue_manager import QueueManager
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_next_in_queue(self):
    """Process the next video in the queue"""
    try:
        # Get the next task to process
        queue_entry = QueueManager.get_next_task()

        if not queue_entry:
            logger.info("No tasks in queue")
            return "No tasks in queue"

        logger.info(f"Processing queue entry {queue_entry.id}")

        # Start processing
        QueueManager.start_processing(queue_entry, worker_id=self.request.id)

        try:
            # Import here to avoid circular imports
            from clipper.tasks.tasks import process_video_with_custom_settings

            # Process the video
            result = process_video_with_custom_settings(
                queue_entry.video_request.id,
                **queue_entry.processing_settings
            )

            # Mark as completed
            QueueManager.complete_processing(queue_entry, success=True)
            logger.info(f"Successfully processed queue entry {queue_entry.id}")

            return f"Successfully processed queue entry {queue_entry.id}"

        except Exception as e:
            # Mark as failed
            QueueManager.complete_processing(queue_entry, success=False, error_message=str(e))
            logger.error(f"Failed to process queue entry {queue_entry.id}: {e}")

            # Retry if possible
            if queue_entry.retry_count < queue_entry.max_retries:
                QueueManager.retry_failed_task(queue_entry)
                raise self.retry(exc=e, countdown=60)  # Retry after 1 minute

            return f"Failed to process queue entry {queue_entry.id}: {e}"

    except Exception as e:
        logger.error(f"Error in queue processing: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task
def process_notification_queue():
    """Process pending notifications"""
    try:
        QueueManager.process_notifications()
        return "Notification queue processed"
    except Exception as e:
        logger.error(f"Error processing notifications: {e}")
        return f"Error: {e}"


@shared_task
def update_queue_stats():
    """Update daily queue statistics"""
    try:
        from datetime import date
        from core.models import QueueStats

        today = date.today()
        current_queue_length = ProcessingQueue.objects.filter(status='queued').count()

        # Update or create today's stats
        stats, created = QueueStats.objects.get_or_create(
            date=today,
            defaults={
                'max_queue_length': current_queue_length
            }
        )

        # Update max queue length if current is higher
        if current_queue_length > stats.max_queue_length:
            stats.max_queue_length = current_queue_length
            stats.save()

        return f"Updated stats for {today}"

    except Exception as e:
        logger.error(f"Error updating queue stats: {e}")
        return f"Error: {e}"


@shared_task
def cleanup_old_queue_entries():
    """Clean up old completed queue entries (run daily)"""
    try:
        from datetime import timedelta

        # Keep completed entries for 30 days, failed entries for 7 days
        cutoff_completed = timezone.now() - timedelta(days=30)
        cutoff_failed = timezone.now() - timedelta(days=7)

        # Delete old completed entries
        deleted_completed = ProcessingQueue.objects.filter(
            status='completed',
            completed_at__lt=cutoff_completed
        ).delete()

        # Delete old failed entries
        deleted_failed = ProcessingQueue.objects.filter(
            status='failed',
            completed_at__lt=cutoff_failed
        ).delete()

        # Delete old notifications
        cutoff_notifications = timezone.now() - timedelta(days=14)
        deleted_notifications = NotificationEvent.objects.filter(
            created_at__lt=cutoff_notifications
        ).delete()

        return f"Cleaned up {deleted_completed[0]} completed, {deleted_failed[0]} failed entries, {deleted_notifications[0]} notifications"

    except Exception as e:
        logger.error(f"Error cleaning up queue entries: {e}")
        return f"Error: {e}"


@shared_task
def send_queue_status_report():
    """Send daily queue status report to admins"""
    try:
        from django.core.mail import mail_admins
        from core.models import QueueStats
        from datetime import date, timedelta

        today = date.today()
        yesterday = today - timedelta(days=1)

        # Get yesterday's stats
        try:
            stats = QueueStats.objects.get(date=yesterday)
        except QueueStats.DoesNotExist:
            return "No stats available for yesterday"

        # Current queue status
        current_status = QueueManager.get_queue_status()

        report = f"""
Queue Status Report for {yesterday}

YESTERDAY'S STATS:
- Total Processed: {stats.total_processed}
- Total Failed: {stats.total_failed}
- Average Processing Time: {stats.avg_processing_time:.1f} minutes
- Max Queue Length: {stats.max_queue_length}

USER TIER BREAKDOWN:
- Free Users: {stats.free_users_processed}
- Pro Users: {stats.pro_users_processed}
- Premium Users: {stats.premium_users_processed}

CURRENT STATUS:
- Queued: {current_status['total_queued']}
- Processing: {current_status['total_processing']}
- Average Wait Time: {current_status.get('average_wait_time', 'N/A'):.1f} minutes

QUEUE BY PRIORITY:
- Free Users: {current_status['queue_by_priority']['free']}
- Pro Users: {current_status['queue_by_priority']['pro']}
- Premium Users: {current_status['queue_by_priority']['premium']}
        """

        mail_admins(
            subject=f'Queue Status Report - {yesterday}',
            message=report,
            fail_silently=False
        )

        return f"Sent queue status report for {yesterday}"

    except Exception as e:
        logger.error(f"Error sending queue status report: {e}")
        return f"Error: {e}"


# Periodic task setup (add this to your celery beat schedule)
"""
CELERY_BEAT_SCHEDULE = {
    'process-queue': {
        'task': 'core.tasks.process_next_in_queue',
        'schedule': 30.0,  # Run every 30 seconds
    },
    'process-notifications': {
        'task': 'core.tasks.process_notification_queue',
        'schedule': 60.0,  # Run every minute
    },
    'update-queue-stats': {
        'task': 'core.tasks.update_queue_stats',
        'schedule': 300.0,  # Run every 5 minutes
    },
    'cleanup-old-entries': {
        'task': 'core.tasks.cleanup_old_queue_entries',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    'daily-queue-report': {
        'task': 'core.tasks.send_queue_status_report',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9 AM
    },
}
"""