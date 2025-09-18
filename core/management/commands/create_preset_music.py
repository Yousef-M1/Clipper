"""
Django management command to create preset background music tracks
"""
from django.core.management.base import BaseCommand
from core.models import BackgroundMusic
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create preset background music tracks'

    def handle(self, *args, **options):
        """Create preset background music tracks"""

        preset_tracks = [
            {
                'name': 'Corporate Success',
                'category': 'corporate',
                'duration_seconds': 120.0,
                'bpm': 120,
                'artist': 'Free Music Archive',
                'license_info': 'Creative Commons - Corporate background music perfect for business videos'
            },
            {
                'name': 'Chill Lo-Fi Beats',
                'category': 'chill',
                'duration_seconds': 180.0,
                'bpm': 85,
                'artist': 'Pixabay Audio',
                'license_info': 'Royalty-free relaxing background music for vlogs and tutorials'
            },
            {
                'name': 'Electronic Gaming',
                'category': 'gaming',
                'duration_seconds': 150.0,
                'bpm': 140,
                'artist': 'YouTube Audio Library',
                'license_info': 'No attribution required - High energy electronic music for gaming content'
            },
            {
                'name': 'Upbeat Pop',
                'category': 'upbeat',
                'duration_seconds': 200.0,
                'bpm': 128,
                'artist': 'Freesound.org',
                'license_info': 'Creative Commons - Energetic pop music for social media content'
            },
            {
                'name': 'Cinematic Epic',
                'category': 'cinematic',
                'duration_seconds': 240.0,
                'bpm': 100,
                'artist': 'Epidemic Sound',
                'license_info': 'Licensed - Epic orchestral music for dramatic content'
            },
            {
                'name': 'Acoustic Guitar',
                'category': 'acoustic',
                'duration_seconds': 160.0,
                'bpm': 90,
                'artist': 'Free Music Archive',
                'license_info': 'Creative Commons - Warm acoustic guitar for personal stories'
            },
            {
                'name': 'Hip Hop Beat',
                'category': 'hip_hop',
                'duration_seconds': 180.0,
                'bpm': 95,
                'artist': 'YouTube Audio Library',
                'license_info': 'No attribution required - Modern hip hop instrumental'
            }
        ]

        created_count = 0
        updated_count = 0

        for track_data in preset_tracks:
            track, created = BackgroundMusic.objects.get_or_create(
                name=track_data['name'],
                is_preset=True,
                defaults={
                    'category': track_data['category'],
                    'duration_seconds': track_data['duration_seconds'],
                    'bpm': track_data['bpm'],
                    'artist': track_data['artist'],
                    'license_info': track_data['license_info'],
                    'volume_level': 0.3,  # Default volume
                    'uploaded_by': None  # Preset tracks have no uploader
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created preset track: {track.name}')
                )
            else:
                # Update existing track with latest info
                track.category = track_data['category']
                track.duration_seconds = track_data['duration_seconds']
                track.bpm = track_data['bpm']
                track.artist = track_data['artist']
                track.license_info = track_data['license_info']
                track.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Updated preset track: {track.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\\nCompleted! Created {created_count} new tracks, updated {updated_count} existing tracks.'
            )
        )

        # Show available categories
        categories = BackgroundMusic.objects.values_list('category', flat=True).distinct()
        self.stdout.write(f'\\nAvailable categories: {", ".join(categories)}')

        # Show total count
        total_presets = BackgroundMusic.objects.filter(is_preset=True).count()
        total_user_uploads = BackgroundMusic.objects.filter(is_preset=False).count()

        self.stdout.write(f'Total preset tracks: {total_presets}')
        self.stdout.write(f'Total user uploads: {total_user_uploads}')