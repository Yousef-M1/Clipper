"""
Text-to-Speech service for AI influencer videos
Supports multiple TTS engines: Edge TTS, Chatterbox, OpenAI TTS
"""
import asyncio
import logging
import os
import tempfile
from typing import Optional, Dict, Any, List
import subprocess

logger = logging.getLogger(__name__)


class TTSService:
    """
    Text-to-Speech service with multiple engine support
    """

    def __init__(self):
        self.supported_engines = ['edge_tts', 'elevenlabs', 'chatterbox', 'openai']

    async def generate_speech(
        self,
        text: str,
        voice_id: str,
        engine: str = 'edge_tts',
        speed: float = 1.0,
        pitch: float = 1.0,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate speech from text using specified TTS engine

        Args:
            text: Text to convert to speech
            voice_id: Voice identifier for the engine
            engine: TTS engine to use
            speed: Speech speed multiplier (0.5-2.0)
            pitch: Speech pitch multiplier (0.5-2.0)
            output_path: Output file path (auto-generated if None)

        Returns:
            Path to generated audio file
        """
        try:
            if engine not in self.supported_engines:
                raise ValueError(f"Unsupported TTS engine: {engine}")

            if output_path is None:
                # Create temporary file for output
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    output_path = tmp.name

            logger.info(f"Generating speech with {engine} engine: {voice_id}")

            if engine == 'edge_tts':
                return await self._generate_edge_tts(text, voice_id, speed, pitch, output_path)
            elif engine == 'elevenlabs':
                return await self._generate_elevenlabs(text, voice_id, speed, pitch, output_path)
            elif engine == 'chatterbox':
                return await self._generate_chatterbox(text, voice_id, speed, pitch, output_path)
            elif engine == 'openai':
                return await self._generate_openai_tts(text, voice_id, speed, pitch, output_path)

        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            raise

    async def _generate_edge_tts(
        self,
        text: str,
        voice_id: str,
        speed: float,
        pitch: float,
        output_path: str
    ) -> str:
        """Generate speech using Edge TTS (Microsoft)"""
        try:
            # Import edge_tts (will need to install: pip install edge-tts)
            import edge_tts

            # Clean the text thoroughly
            clean_text = text.strip()

            # Remove any potential problematic characters
            clean_text = clean_text.replace('\r', ' ').replace('\n', ' ')

            # Normalize whitespace
            clean_text = ' '.join(clean_text.split())

            # Ensure text is not empty
            if not clean_text:
                raise ValueError("Text is empty after cleaning")

            # For Edge TTS, use the simplest possible approach
            # Use default rate to avoid any parameter issues
            communicate = edge_tts.Communicate(clean_text, voice_id)
            await communicate.save(output_path)

            logger.info(f"Edge TTS audio generated: {output_path}")
            return output_path

        except ImportError:
            logger.error("edge-tts not installed. Install with: pip install edge-tts")
            raise
        except Exception as e:
            logger.error(f"Edge TTS generation failed: {e}")
            raise

    async def _generate_elevenlabs(
        self,
        text: str,
        voice_id: str,
        speed: float,
        pitch: float,
        output_path: str
    ) -> str:
        """Generate speech using ElevenLabs TTS"""
        try:
            # Import ElevenLabs (will need: pip install elevenlabs)
            from elevenlabs import AsyncElevenLabs
            from django.conf import settings

            # Initialize ElevenLabs client
            client = AsyncElevenLabs(api_key=getattr(settings, 'ELEVENLABS_API_KEY', None))

            if not hasattr(settings, 'ELEVENLABS_API_KEY') or not settings.ELEVENLABS_API_KEY:
                raise ValueError("ELEVENLABS_API_KEY not configured in settings")

            # Generate audio with ElevenLabs
            audio_generator = await client.generate(
                text=text,
                voice=voice_id,
                model="eleven_monolingual_v1",  # or "eleven_multilingual_v2"
                stream=False
            )

            # Convert generator to bytes
            audio_bytes = b''.join(audio_generator)

            # Save audio file
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)

            logger.info(f"ElevenLabs TTS audio generated: {output_path}")
            return output_path

        except ImportError:
            logger.error("elevenlabs package not installed. Install with: pip install elevenlabs")
            raise
        except Exception as e:
            logger.error(f"ElevenLabs TTS generation failed: {e}")
            raise

    async def _generate_chatterbox(
        self,
        text: str,
        voice_id: str,
        speed: float,
        pitch: float,
        output_path: str
    ) -> str:
        """Generate speech using Chatterbox TTS"""
        try:
            # Note: This is a placeholder for Chatterbox integration
            # You would need to install and configure Chatterbox TTS
            logger.warning("Chatterbox TTS integration not yet implemented")
            raise NotImplementedError("Chatterbox TTS coming soon")

        except Exception as e:
            logger.error(f"Chatterbox TTS generation failed: {e}")
            raise

    async def _generate_openai_tts(
        self,
        text: str,
        voice_id: str,
        speed: float,
        pitch: float,
        output_path: str
    ) -> str:
        """Generate speech using OpenAI TTS"""
        try:
            # Import OpenAI (will need openai package)
            from openai import AsyncOpenAI
            from django.conf import settings

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            # OpenAI TTS doesn't support pitch, only speed
            response = await client.audio.speech.create(
                model="tts-1",  # or "tts-1-hd" for higher quality
                voice=voice_id,  # OpenAI voices: alloy, echo, fable, onyx, nova, shimmer
                input=text,
                speed=speed  # 0.25 to 4.0
            )

            # Save the audio file
            with open(output_path, 'wb') as f:
                async for chunk in response.iter_bytes():
                    f.write(chunk)

            logger.info(f"OpenAI TTS audio generated: {output_path}")
            return output_path

        except ImportError:
            logger.error("openai package not installed. Install with: pip install openai")
            raise
        except Exception as e:
            logger.error(f"OpenAI TTS generation failed: {e}")
            raise

    def get_available_voices(self, engine: str = 'edge_tts') -> Dict[str, Any]:
        """
        Get available voices for specified engine

        Returns:
            Dictionary of available voices with metadata
        """
        if engine == 'edge_tts':
            return self._get_edge_tts_voices()
        elif engine == 'elevenlabs':
            return self._get_elevenlabs_voices()
        elif engine == 'openai':
            return self._get_openai_voices()
        else:
            return {}

    def _get_edge_tts_voices(self) -> Dict[str, Any]:
        """Get Edge TTS available voices"""
        return {
            # US English Voices
            'en-US-AriaNeural': {
                'name': 'Aria - US English Female',
                'gender': 'female',
                'language': 'en-US',
                'style': 'friendly'
            },
            'en-US-JennyNeural': {
                'name': 'Jenny - US English Female',
                'gender': 'female',
                'language': 'en-US',
                'style': 'professional'
            },
            'en-US-GuyNeural': {
                'name': 'Guy - US English Male',
                'gender': 'male',
                'language': 'en-US',
                'style': 'natural'
            },
            'en-US-DavisNeural': {
                'name': 'Davis - US English Male',
                'gender': 'male',
                'language': 'en-US',
                'style': 'energetic'
            },
            'en-US-JaneNeural': {
                'name': 'Jane - US English Female',
                'gender': 'female',
                'language': 'en-US',
                'style': 'casual'
            },
            'en-US-JasonNeural': {
                'name': 'Jason - US English Male',
                'gender': 'male',
                'language': 'en-US',
                'style': 'casual'
            },
            'en-US-TonyNeural': {
                'name': 'Tony - US English Male',
                'gender': 'male',
                'language': 'en-US',
                'style': 'narration'
            },
            'en-US-SaraNeural': {
                'name': 'Sara - US English Female',
                'gender': 'female',
                'language': 'en-US',
                'style': 'cheerful'
            },
            'en-US-NancyNeural': {
                'name': 'Nancy - US English Female',
                'gender': 'female',
                'language': 'en-US',
                'style': 'angry'
            },
            'en-US-AmberNeural': {
                'name': 'Amber - US English Female',
                'gender': 'female',
                'language': 'en-US',
                'style': 'excited'
            },
            # UK English Voices
            'en-GB-SoniaNeural': {
                'name': 'Sonia - UK English Female',
                'gender': 'female',
                'language': 'en-GB',
                'style': 'professional'
            },
            'en-GB-RyanNeural': {
                'name': 'Ryan - UK English Male',
                'gender': 'male',
                'language': 'en-GB',
                'style': 'calm'
            },
            'en-GB-LibbyNeural': {
                'name': 'Libby - UK English Female',
                'gender': 'female',
                'language': 'en-GB',
                'style': 'cheerful'
            },
            'en-GB-MaisieNeural': {
                'name': 'Maisie - UK English Female',
                'gender': 'female',
                'language': 'en-GB',
                'style': 'casual'
            },
            # Australian English
            'en-AU-NatashaNeural': {
                'name': 'Natasha - Australian English Female',
                'gender': 'female',
                'language': 'en-AU',
                'style': 'friendly'
            },
            'en-AU-WilliamNeural': {
                'name': 'William - Australian English Male',
                'gender': 'male',
                'language': 'en-AU',
                'style': 'casual'
            },
            # Canadian English
            'en-CA-ClaraNeural': {
                'name': 'Clara - Canadian English Female',
                'gender': 'female',
                'language': 'en-CA',
                'style': 'friendly'
            },
            'en-CA-LiamNeural': {
                'name': 'Liam - Canadian English Male',
                'gender': 'male',
                'language': 'en-CA',
                'style': 'casual'
            },
            # Indian English
            'en-IN-NeerjaNeural': {
                'name': 'Neerja - Indian English Female',
                'gender': 'female',
                'language': 'en-IN',
                'style': 'friendly'
            },
            'en-IN-PrabhatNeural': {
                'name': 'Prabhat - Indian English Male',
                'gender': 'male',
                'language': 'en-IN',
                'style': 'professional'
            }
        }

    def _get_elevenlabs_voices(self) -> Dict[str, Any]:
        """Get ElevenLabs available voices"""
        return {
            # Premium voices (require ElevenLabs subscription)
            'Rachel': {
                'name': 'Rachel - Calm Female Voice',
                'gender': 'female',
                'language': 'en-US',
                'style': 'calm',
                'is_premium': True
            },
            'Drew': {
                'name': 'Drew - Well-rounded Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'natural',
                'is_premium': True
            },
            'Clyde': {
                'name': 'Clyde - War Veteran Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'authoritative',
                'is_premium': True
            },
            'Paul': {
                'name': 'Paul - Middle-aged Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'professional',
                'is_premium': True
            },
            'Domi': {
                'name': 'Domi - Strong Female Voice',
                'gender': 'female',
                'language': 'en-US',
                'style': 'confident',
                'is_premium': True
            },
            'Dave': {
                'name': 'Dave - Young Adult Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'casual',
                'is_premium': True
            },
            'Fin': {
                'name': 'Fin - Old Irish Male Voice',
                'gender': 'male',
                'language': 'en-IE',
                'style': 'irish',
                'is_premium': True
            },
            'Bella': {
                'name': 'Bella - Soft Female Voice',
                'gender': 'female',
                'language': 'en-US',
                'style': 'soft',
                'is_premium': True
            },
            'Antoni': {
                'name': 'Antoni - Well-rounded Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'well-rounded',
                'is_premium': True
            },
            'Thomas': {
                'name': 'Thomas - Calm Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'calm',
                'is_premium': True
            },
            'Charlie': {
                'name': 'Charlie - Natural Female Voice',
                'gender': 'female',
                'language': 'en-US',
                'style': 'natural',
                'is_premium': True
            },
            'Emily': {
                'name': 'Emily - Calm Female Voice',
                'gender': 'female',
                'language': 'en-US',
                'style': 'calm',
                'is_premium': True
            },
            'Elli': {
                'name': 'Elli - Emotional Female Voice',
                'gender': 'female',
                'language': 'en-US',
                'style': 'emotional',
                'is_premium': True
            },
            'Callum': {
                'name': 'Callum - Intense Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'intense',
                'is_premium': True
            },
            'Patrick': {
                'name': 'Patrick - Pleasant Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'pleasant',
                'is_premium': True
            },
            'Harry': {
                'name': 'Harry - Anxious Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'anxious',
                'is_premium': True
            },
            'Liam': {
                'name': 'Liam - Articulate Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'articulate',
                'is_premium': True
            },
            'Dorothy': {
                'name': 'Dorothy - Pleasant Female Voice',
                'gender': 'female',
                'language': 'en-US',
                'style': 'pleasant',
                'is_premium': True
            },
            'Josh': {
                'name': 'Josh - Deep Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'deep',
                'is_premium': True
            },
            'Arnold': {
                'name': 'Arnold - Crisp Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'crisp',
                'is_premium': True
            },
            'Charlotte': {
                'name': 'Charlotte - Natural Female Voice',
                'gender': 'female',
                'language': 'en-US',
                'style': 'natural',
                'is_premium': True
            },
            'Matilda': {
                'name': 'Matilda - Warm Female Voice',
                'gender': 'female',
                'language': 'en-US',
                'style': 'warm',
                'is_premium': True
            },
            'Matthew': {
                'name': 'Matthew - Expressive Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'expressive',
                'is_premium': True
            },
            'James': {
                'name': 'James - Calm Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'calm',
                'is_premium': True
            }
        }

    def _get_openai_voices(self) -> Dict[str, Any]:
        """Get OpenAI TTS available voices"""
        return {
            'alloy': {
                'name': 'Alloy - Neutral Voice',
                'gender': 'neutral',
                'language': 'en-US',
                'style': 'balanced'
            },
            'echo': {
                'name': 'Echo - Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'natural'
            },
            'fable': {
                'name': 'Fable - Expressive Voice',
                'gender': 'neutral',
                'language': 'en-US',
                'style': 'expressive'
            },
            'onyx': {
                'name': 'Onyx - Deep Male Voice',
                'gender': 'male',
                'language': 'en-US',
                'style': 'deep'
            },
            'nova': {
                'name': 'Nova - Friendly Female Voice',
                'gender': 'female',
                'language': 'en-US',
                'style': 'friendly'
            },
            'shimmer': {
                'name': 'Shimmer - Warm Female Voice',
                'gender': 'female',
                'language': 'en-US',
                'style': 'warm'
            }
        }

    def convert_audio_format(self, input_path: str, output_path: str, target_format: str = 'wav') -> str:
        """
        Convert audio file to target format using FFmpeg

        Args:
            input_path: Input audio file path
            output_path: Output audio file path
            target_format: Target audio format (wav, mp3, etc.)

        Returns:
            Path to converted audio file
        """
        try:
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-acodec', 'pcm_s16le',  # 16-bit PCM for compatibility
                '-ar', '22050',  # 22kHz sample rate
                '-ac', '1',  # Mono audio
                '-y',  # Overwrite output
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Audio converted to {target_format}: {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            logger.error(f"Audio conversion failed: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Audio conversion error: {e}")
            raise

    async def generate_professional_audio(
        self,
        text: str,
        voice_id: str,
        engine: str = 'edge_tts',
        music_track: str = "corporate",
        voice_volume: float = 1.0,
        music_volume: float = 0.3,
        effects: Optional[Dict] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate professional TTS audio with background music and effects

        Args:
            text: Text to convert to speech
            voice_id: Voice identifier for the engine
            engine: TTS engine to use
            music_track: Background music track ID
            voice_volume: Voice volume (0.0 to 1.0)
            music_volume: Music volume (0.0 to 1.0)
            effects: Audio effects to apply
            output_path: Output file path

        Returns:
            Path to professional audio file with music and effects
        """
        try:
            # Import audio mixing service
            from .audio_mixing_service import AudioMixingService

            logger.info(f"Generating professional audio with music: {music_track}")

            # Step 1: Generate basic TTS audio
            tts_audio = await self.generate_speech(
                text=text,
                voice_id=voice_id,
                engine=engine
            )

            # Step 2: Mix with background music and apply effects
            mixing_service = AudioMixingService()

            professional_audio = await mixing_service.create_professional_audio(
                tts_audio_path=tts_audio,
                music_track=music_track,
                voice_volume=voice_volume,
                music_volume=music_volume,
                effects=effects or {},
                output_path=output_path
            )

            # Clean up temporary TTS file
            if os.path.exists(tts_audio):
                os.unlink(tts_audio)

            logger.info(f"Professional audio created: {professional_audio}")
            return professional_audio

        except Exception as e:
            logger.error(f"Failed to generate professional audio: {e}")
            raise

    def get_available_music_tracks(self) -> Dict:
        """Get available background music tracks"""
        try:
            from .audio_mixing_service import AudioMixingService
            mixing_service = AudioMixingService()
            return mixing_service.get_available_music()
        except Exception as e:
            logger.error(f"Failed to get music tracks: {e}")
            return {}

    async def generate_cloned_voice_audio(
        self,
        text: str,
        voice_id: str,
        music_track: Optional[str] = None,
        voice_volume: float = 1.0,
        music_volume: float = 0.3,
        effects: Optional[Dict] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate professional audio using a cloned voice

        Args:
            text: Text to convert to speech
            voice_id: Cloned voice ID to use
            music_track: Background music track (optional)
            voice_volume: Voice volume (0.0 to 1.0)
            music_volume: Music volume (0.0 to 1.0)
            effects: Audio effects to apply
            output_path: Output file path

        Returns:
            Path to professional audio with cloned voice
        """
        try:
            # Import voice cloning service
            from .voice_cloning_service import VoiceCloningService

            logger.info(f"Generating cloned voice audio: {voice_id}")

            # Step 1: Generate cloned voice audio
            voice_cloning = VoiceCloningService()

            cloned_audio = await voice_cloning.generate_cloned_speech(
                text=text,
                voice_id=voice_id
            )

            # Step 2: Apply music and effects if requested
            if music_track or effects:
                from .audio_mixing_service import AudioMixingService
                mixing_service = AudioMixingService()

                if music_track:
                    # Mix with background music + effects
                    professional_audio = await mixing_service.create_professional_audio(
                        tts_audio_path=cloned_audio,
                        music_track=music_track,
                        voice_volume=voice_volume,
                        music_volume=music_volume,
                        effects=effects or {},
                        output_path=output_path
                    )
                else:
                    # Just apply effects
                    professional_audio = await mixing_service.apply_audio_effects(
                        audio_path=cloned_audio,
                        effects=effects or {},
                        output_path=output_path
                    )

                # Clean up temporary cloned audio
                if os.path.exists(cloned_audio):
                    os.unlink(cloned_audio)

                return professional_audio
            else:
                # No music or effects, just return cloned voice
                if output_path and cloned_audio != output_path:
                    import shutil
                    shutil.move(cloned_audio, output_path)
                    return output_path
                return cloned_audio

        except Exception as e:
            logger.error(f"Failed to generate cloned voice audio: {e}")
            raise

    def get_available_cloned_voices(self) -> Dict:
        """Get available cloned voices"""
        try:
            from .voice_cloning_service import VoiceCloningService
            voice_cloning = VoiceCloningService()
            return voice_cloning.get_available_voices()
        except Exception as e:
            logger.error(f"Failed to get cloned voices: {e}")
            return {}

    def get_cloned_voice_info(self, voice_id: str) -> Optional[Dict]:
        """Get information about a cloned voice"""
        try:
            from .voice_cloning_service import VoiceCloningService
            voice_cloning = VoiceCloningService()
            return voice_cloning.get_voice_info(voice_id)
        except Exception as e:
            logger.error(f"Failed to get cloned voice info: {e}")
            return None

    async def create_user_voice_clone(
        self,
        user_id: str,
        voice_name: str,
        audio_files: List[str],
        description: Optional[str] = None
    ) -> Dict:
        """
        Create a personalized voice clone from user's audio files

        Args:
            user_id: Unique user identifier
            voice_name: Name for the cloned voice
            audio_files: List of paths to user's audio files
            description: Optional description

        Returns:
            Voice clone information
        """
        try:
            from .real_voice_cloning import RealVoiceCloningService

            logger.info(f"Creating user voice clone: {voice_name} for user {user_id}")

            real_cloning = RealVoiceCloningService()

            voice_clone = await real_cloning.create_user_voice_clone(
                user_id=user_id,
                voice_name=voice_name,
                audio_files=audio_files,
                description=description
            )

            return voice_clone

        except Exception as e:
            logger.error(f"Failed to create user voice clone: {e}")
            raise

    async def generate_user_voice_audio(
        self,
        text: str,
        voice_id: str,
        user_id: str,
        music_track: Optional[str] = None,
        voice_volume: float = 1.0,
        music_volume: float = 0.3,
        effects: Optional[Dict] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate professional audio using user's cloned voice

        Args:
            text: Text to convert to speech
            voice_id: User's cloned voice ID
            user_id: User ID (for verification)
            music_track: Background music track (optional)
            voice_volume: Voice volume (0.0 to 1.0)
            music_volume: Music volume (0.0 to 1.0)
            effects: Audio effects to apply
            output_path: Output file path

        Returns:
            Path to professional audio with user's cloned voice
        """
        try:
            from .real_voice_cloning import RealVoiceCloningService

            logger.info(f"Generating user voice audio: {voice_id} for user {user_id}")

            # Step 1: Generate user cloned voice audio
            real_cloning = RealVoiceCloningService()

            user_audio = await real_cloning.generate_user_cloned_speech(
                text=text,
                voice_id=voice_id,
                user_id=user_id
            )

            # Step 2: Apply music and effects if requested
            if music_track or effects:
                from .audio_mixing_service import AudioMixingService
                mixing_service = AudioMixingService()

                if music_track:
                    # Mix with background music + effects
                    professional_audio = await mixing_service.create_professional_audio(
                        tts_audio_path=user_audio,
                        music_track=music_track,
                        voice_volume=voice_volume,
                        music_volume=music_volume,
                        effects=effects or {},
                        output_path=output_path
                    )
                else:
                    # Just apply effects
                    professional_audio = await mixing_service.apply_audio_effects(
                        audio_path=user_audio,
                        effects=effects or {},
                        output_path=output_path
                    )

                # Clean up temporary user audio
                if os.path.exists(user_audio):
                    os.unlink(user_audio)

                return professional_audio
            else:
                # No music or effects, just return user cloned voice
                if output_path and user_audio != output_path:
                    import shutil
                    shutil.move(user_audio, output_path)
                    return output_path
                return user_audio

        except Exception as e:
            logger.error(f"Failed to generate user voice audio: {e}")
            raise

    def get_user_voices(self, user_id: str) -> List[Dict]:
        """Get all voice clones for a specific user"""
        try:
            from .real_voice_cloning import RealVoiceCloningService
            real_cloning = RealVoiceCloningService()
            return real_cloning.get_user_voices(user_id)
        except Exception as e:
            logger.error(f"Failed to get user voices: {e}")
            return []

    def delete_user_voice(self, voice_id: str, user_id: str) -> bool:
        """Delete a user's voice clone"""
        try:
            from .real_voice_cloning import RealVoiceCloningService
            real_cloning = RealVoiceCloningService()
            return real_cloning.delete_user_voice(voice_id, user_id)
        except Exception as e:
            logger.error(f"Failed to delete user voice: {e}")
            return False

    def get_available_effects(self) -> Dict:
        """Get available audio effects"""
        return {
            "reverb": {
                "name": "Reverb",
                "description": "Add natural room reverb",
                "type": "boolean",
                "default": False
            },
            "echo": {
                "name": "Echo",
                "description": "Add echo effect",
                "type": "boolean",
                "default": False
            },
            "compress": {
                "name": "Compression",
                "description": "Dynamic range compression",
                "type": "boolean",
                "default": False
            },
            "normalize": {
                "name": "Normalize",
                "description": "Normalize audio levels",
                "type": "boolean",
                "default": True
            },
            "speed": {
                "name": "Speed",
                "description": "Playback speed",
                "type": "float",
                "min": 0.5,
                "max": 2.0,
                "default": 1.0
            },
            "pitch": {
                "name": "Pitch",
                "description": "Pitch adjustment (semitones)",
                "type": "float",
                "min": -12,
                "max": 12,
                "default": 0
            }
        }