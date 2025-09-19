"""
Django management command to populate VoiceProfile database with available TTS voices
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from ai_influencer.models import VoiceProfile
from ai_influencer.tts_service import TTSService


class Command(BaseCommand):
    help = 'Populate VoiceProfile database with available TTS voices from all engines'

    def add_arguments(self, parser):
        parser.add_argument(
            '--engine',
            type=str,
            choices=['edge_tts', 'elevenlabs', 'openai', 'all'],
            default='all',
            help='Specify which TTS engine voices to populate (default: all)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing voice profiles before populating'
        )

    def handle(self, *args, **options):
        engine_filter = options['engine']
        clear_existing = options['clear']

        self.stdout.write(
            self.style.SUCCESS(f'Starting voice population for engine: {engine_filter}')
        )

        if clear_existing:
            self.stdout.write('Clearing existing voice profiles...')
            VoiceProfile.objects.all().delete()
            self.stdout.write(self.style.WARNING('Existing voice profiles cleared'))

        tts_service = TTSService()
        engines_to_process = []

        if engine_filter == 'all':
            engines_to_process = ['edge_tts', 'elevenlabs', 'openai']
        else:
            engines_to_process = [engine_filter]

        total_created = 0
        total_updated = 0

        with transaction.atomic():
            for engine in engines_to_process:
                self.stdout.write(f'\nProcessing {engine} voices...')

                voices = tts_service.get_available_voices(engine)
                created_count = 0
                updated_count = 0

                for voice_id, voice_data in voices.items():
                    # Create or update voice profile
                    voice_profile, created = VoiceProfile.objects.update_or_create(
                        voice_id=voice_id,
                        engine=engine,
                        defaults={
                            'name': voice_data['name'],
                            'language': voice_data['language'],
                            'gender': voice_data['gender'],
                            'is_premium': voice_data.get('is_premium', False),
                            'is_active': True,
                        }
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(f'  ✓ Created: {voice_profile.name}')
                    else:
                        updated_count += 1
                        self.stdout.write(f'  ↻ Updated: {voice_profile.name}')

                self.stdout.write(
                    self.style.SUCCESS(
                        f'{engine}: {created_count} created, {updated_count} updated'
                    )
                )
                total_created += created_count
                total_updated += updated_count

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Voice population completed!\n'
                f'Total voices created: {total_created}\n'
                f'Total voices updated: {total_updated}\n'
                f'Total voices in database: {VoiceProfile.objects.count()}'
            )
        )

        # Show summary by engine
        self.stdout.write('\n📊 Voice Summary by Engine:')
        for engine in VoiceProfile.objects.values_list('engine', flat=True).distinct():
            count = VoiceProfile.objects.filter(engine=engine).count()
            premium_count = VoiceProfile.objects.filter(engine=engine, is_premium=True).count()
            self.stdout.write(f'  {engine}: {count} voices ({premium_count} premium)')