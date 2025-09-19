"""
Management command to setup AI influencer data
"""
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from ai_influencer.models import AvatarCharacter, VoiceProfile
import base64
import io
from PIL import Image


class Command(BaseCommand):
    help = 'Setup initial AI influencer data (characters and voices)'

    def handle(self, *args, **options):
        self.stdout.write("Setting up AI influencer data...")

        # Create voice profiles
        self.create_voice_profiles()

        # Create sample avatar characters
        self.create_avatar_characters()

        self.stdout.write(
            self.style.SUCCESS("Successfully set up AI influencer data!")
        )

    def create_voice_profiles(self):
        """Create voice profiles for Edge TTS"""
        voices = [
            {
                'name': 'Aria - US English Female',
                'voice_id': 'en-US-AriaNeural',
                'language': 'en-US',
                'gender': 'female',
                'engine': 'edge_tts',
                'sample_rate': 22050,
                'is_premium': False,
            },
            {
                'name': 'Jenny - US English Female',
                'voice_id': 'en-US-JennyNeural',
                'language': 'en-US',
                'gender': 'female',
                'engine': 'edge_tts',
                'sample_rate': 22050,
                'is_premium': False,
            },
            {
                'name': 'Guy - US English Male',
                'voice_id': 'en-US-GuyNeural',
                'language': 'en-US',
                'gender': 'male',
                'engine': 'edge_tts',
                'sample_rate': 22050,
                'is_premium': False,
            },
            {
                'name': 'Davis - US English Male',
                'voice_id': 'en-US-DavisNeural',
                'language': 'en-US',
                'gender': 'male',
                'engine': 'edge_tts',
                'sample_rate': 22050,
                'is_premium': False,
            },
            {
                'name': 'Sonia - UK English Female',
                'voice_id': 'en-GB-SoniaNeural',
                'language': 'en-GB',
                'gender': 'female',
                'engine': 'edge_tts',
                'sample_rate': 22050,
                'is_premium': False,
            },
            {
                'name': 'Ryan - UK English Male',
                'voice_id': 'en-GB-RyanNeural',
                'language': 'en-GB',
                'gender': 'male',
                'engine': 'edge_tts',
                'sample_rate': 22050,
                'is_premium': False,
            },
        ]

        for voice_data in voices:
            voice, created = VoiceProfile.objects.get_or_create(
                voice_id=voice_data['voice_id'],
                engine=voice_data['engine'],
                defaults=voice_data
            )
            if created:
                self.stdout.write(f"Created voice: {voice.name}")
            else:
                self.stdout.write(f"Voice already exists: {voice.name}")

    def create_avatar_characters(self):
        """Create sample avatar characters"""
        characters = [
            {
                'name': 'Sarah Tech',
                'description': 'Professional tech presenter with a friendly demeanor. Perfect for technology reviews and tutorials.',
                'gender': 'female',
                'voice_style': 'professional',
            },
            {
                'name': 'Mike Casual',
                'description': 'Relaxed and approachable lifestyle influencer. Great for casual content and product reviews.',
                'gender': 'male',
                'voice_style': 'casual',
            },
            {
                'name': 'Emma Business',
                'description': 'Confident business professional ideal for corporate presentations and professional content.',
                'gender': 'female',
                'voice_style': 'professional',
            },
            {
                'name': 'Alex Energy',
                'description': 'High-energy presenter perfect for fitness, gaming, and energetic content.',
                'gender': 'neutral',
                'voice_style': 'energetic',
            },
            {
                'name': 'Luna Calm',
                'description': 'Serene and calming presence ideal for meditation, wellness, and educational content.',
                'gender': 'female',
                'voice_style': 'calm',
            },
        ]

        for char_data in characters:
            character, created = AvatarCharacter.objects.get_or_create(
                name=char_data['name'],
                defaults=char_data
            )

            if created:
                # Create a simple placeholder image
                placeholder_image = self.create_placeholder_image(char_data['name'])
                character.avatar_image.save(
                    f"{char_data['name'].lower().replace(' ', '_')}.jpg",
                    placeholder_image,
                    save=True
                )
                self.stdout.write(f"Created character: {character.name}")
            else:
                self.stdout.write(f"Character already exists: {character.name}")

    def create_placeholder_image(self, name):
        """Create a simple placeholder image for the character"""
        # Create a simple colored rectangle with text
        img = Image.new('RGB', (400, 400), color='lightblue')

        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=85)
        img_buffer.seek(0)

        return ContentFile(img_buffer.getvalue(), name=f"{name.lower().replace(' ', '_')}.jpg")