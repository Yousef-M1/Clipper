from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import VideoRequest, ProcessingQueue
from core.queue_manager import QueueManager
import time

User = get_user_model()


class Command(BaseCommand):
    help = 'Test the queue management system'

    def add_arguments(self, parser):
        parser.add_argument('--email', help='User email to create test videos for')
        parser.add_argument('--count', type=int, default=3, help='Number of test videos to queue')

    def handle(self, *args, **options):
        email = options.get('email')
        count = options['count']

        if not email:
            self.stdout.write(self.style.ERROR('Please provide --email argument'))
            return

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {email} not found'))
            return

        self.stdout.write(f'Testing queue system with {count} videos for user {email}')

        # Create test video requests and add to queue
        for i in range(count):
            video_request = VideoRequest.objects.create(
                user=user,
                url=f"https://youtube.com/watch?v=test{i+1}",
                status='pending'
            )

            # Add to queue with different settings
            processing_settings = {
                'moment_detection_type': 'ai_powered',
                'clip_duration': 30.0,
                'max_clips': 5,
                'video_quality': '720p',
                'output_format': 'vertical' if i % 2 == 0 else 'horizontal',
                'social_platform': 'tiktok' if i % 2 == 0 else 'youtube'
            }

            queue_entry = QueueManager.add_to_queue(video_request, processing_settings)

            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Created video {i+1}: Queue position #{queue_entry.queue_position}, '
                    f'Priority {queue_entry.priority}, Est. wait: {queue_entry.estimated_wait_time:.1f}min'
                )
            )

        # Show queue status
        self.stdout.write('\n' + '='*50)
        self.stdout.write('QUEUE STATUS:')

        queue_status = QueueManager.get_queue_status()
        self.stdout.write(f'Total queued: {queue_status["total_queued"]}')
        self.stdout.write(f'Currently processing: {queue_status["total_processing"]}')

        # Show queue by priority
        self.stdout.write('\nQueue by priority:')
        for tier, count in queue_status['queue_by_priority'].items():
            self.stdout.write(f'  {tier.title()}: {count}')

        # Show user's queue
        user_queue = QueueManager.get_queue_status(user)
        self.stdout.write(f'\n{email}\'s queue:')
        for entry in user_queue['user_queue']:
            status_color = {
                'queued': self.style.WARNING,
                'processing': self.style.NOTICE,
                'completed': self.style.SUCCESS,
                'failed': self.style.ERROR
            }.get(entry['status'], self.style.NOTICE)

            self.stdout.write(
                f'  Video: {entry["video_url"]} - '
                + status_color(f'Status: {entry["status"]}') +
                (f' - Position: #{entry["position"]}' if entry["position"] else '') +
                (f' - Wait: {entry["estimated_wait"]:.1f}min' if entry["estimated_wait"] else '')
            )

        self.stdout.write(self.style.SUCCESS(f'\n✅ Queue test completed successfully!'))