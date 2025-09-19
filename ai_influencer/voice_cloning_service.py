"""
Voice Cloning Service for AI TTS
Train custom voices and generate speech with cloned voices
"""
import os
import logging
import tempfile
import subprocess
import shutil
import json
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


class VoiceCloningService:
    """
    Voice cloning service for creating custom AI voices
    """

    def __init__(self):
        self.voices_dir = "ai_influencer/cloned_voices"
        self.models_dir = "ai_influencer/voice_models"
        self.samples_dir = "ai_influencer/voice_samples"

        # Create directories
        os.makedirs(self.voices_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.samples_dir, exist_ok=True)

        # Initialize with some pre-made voice profiles
        self._create_sample_voices()

    def _create_sample_voices(self):
        """Create sample voice profiles for demo"""
        self.sample_voices = {
            "professional_male": {
                "name": "Professional Male Voice",
                "description": "Deep, authoritative business voice",
                "gender": "male",
                "age_range": "30-45",
                "style": "professional",
                "quality": "high",
                "trained": True,
                "sample_count": 25
            },
            "friendly_female": {
                "name": "Friendly Female Voice",
                "description": "Warm, conversational female voice",
                "gender": "female",
                "age_range": "25-35",
                "style": "casual",
                "quality": "high",
                "trained": True,
                "sample_count": 30
            },
            "energetic_young": {
                "name": "Energetic Young Voice",
                "description": "Upbeat, youthful voice for content",
                "gender": "neutral",
                "age_range": "18-28",
                "style": "energetic",
                "quality": "medium",
                "trained": True,
                "sample_count": 20
            },
            "narrator_voice": {
                "name": "Audiobook Narrator",
                "description": "Clear, storytelling voice",
                "gender": "male",
                "age_range": "40-55",
                "style": "narrative",
                "quality": "high",
                "trained": True,
                "sample_count": 35
            }
        }

    async def create_voice_profile(
        self,
        voice_name: str,
        description: str,
        audio_samples: List[str],
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Create a new voice profile from audio samples

        Args:
            voice_name: Name for the cloned voice
            description: Description of the voice
            audio_samples: List of paths to audio sample files
            user_id: User ID who owns this voice

        Returns:
            Voice profile information
        """
        try:
            logger.info(f"Creating voice profile: {voice_name}")

            # Validate audio samples
            validated_samples = await self._validate_audio_samples(audio_samples)

            if len(validated_samples) < 3:
                raise ValueError("Need at least 3 audio samples for voice cloning")

            # Create voice profile
            voice_id = self._generate_voice_id(voice_name, user_id)

            # Process audio samples
            processed_samples = await self._process_audio_samples(
                validated_samples, voice_id
            )

            # Analyze voice characteristics
            voice_characteristics = await self._analyze_voice_characteristics(
                processed_samples
            )

            # Create voice model (simplified approach for now)
            model_path = await self._create_voice_model(
                voice_id, processed_samples, voice_characteristics
            )

            # Create voice profile
            voice_profile = {
                "voice_id": voice_id,
                "name": voice_name,
                "description": description,
                "user_id": user_id,
                "gender": voice_characteristics.get("gender", "unknown"),
                "age_range": voice_characteristics.get("age_range", "unknown"),
                "style": voice_characteristics.get("style", "neutral"),
                "quality": voice_characteristics.get("quality", "medium"),
                "trained": True,
                "sample_count": len(processed_samples),
                "model_path": model_path,
                "created_date": self._get_current_timestamp(),
                "characteristics": voice_characteristics
            }

            # Save voice profile
            await self._save_voice_profile(voice_id, voice_profile)

            logger.info(f"Voice profile created successfully: {voice_id}")
            return voice_profile

        except Exception as e:
            logger.error(f"Failed to create voice profile: {e}")
            raise

    async def _validate_audio_samples(self, audio_samples: List[str]) -> List[str]:
        """Validate and filter audio samples"""
        validated = []

        for sample_path in audio_samples:
            if not os.path.exists(sample_path):
                logger.warning(f"Audio sample not found: {sample_path}")
                continue

            # Check if it's a valid audio file
            try:
                # Get audio info using ffprobe
                cmd = [
                    'ffprobe', '-v', 'quiet',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    sample_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    duration = float(result.stdout.strip())

                    # Check duration (should be between 2-30 seconds for good samples)
                    if 2.0 <= duration <= 30.0:
                        validated.append(sample_path)
                    else:
                        logger.warning(f"Audio sample duration out of range: {duration}s")
                else:
                    logger.warning(f"Invalid audio file: {sample_path}")

            except Exception as e:
                logger.warning(f"Error validating audio sample {sample_path}: {e}")

        return validated

    async def _process_audio_samples(self, audio_samples: List[str], voice_id: str) -> List[str]:
        """Process and normalize audio samples"""
        processed_samples = []

        voice_samples_dir = os.path.join(self.samples_dir, voice_id)
        os.makedirs(voice_samples_dir, exist_ok=True)

        for i, sample_path in enumerate(audio_samples):
            try:
                # Create processed sample filename
                processed_filename = f"sample_{i+1:03d}.wav"
                processed_path = os.path.join(voice_samples_dir, processed_filename)

                # Normalize audio: 16kHz, mono, remove silence
                cmd = [
                    'ffmpeg',
                    '-i', sample_path,
                    '-ar', '16000',  # 16kHz sample rate
                    '-ac', '1',      # Mono
                    '-af', 'silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB,silenceremove=stop_periods=1:stop_silence=0.1:stop_threshold=-50dB,loudnorm',
                    '-y',
                    processed_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0 and os.path.exists(processed_path):
                    processed_samples.append(processed_path)
                    logger.info(f"Processed audio sample: {processed_filename}")
                else:
                    logger.error(f"Failed to process sample {i+1}: {result.stderr}")

            except Exception as e:
                logger.error(f"Error processing audio sample {i+1}: {e}")

        return processed_samples

    async def _analyze_voice_characteristics(self, processed_samples: List[str]) -> Dict:
        """Analyze voice characteristics from processed samples"""
        try:
            characteristics = {
                "gender": "unknown",
                "age_range": "unknown",
                "style": "neutral",
                "quality": "medium",
                "pitch_range": "medium",
                "tone": "neutral"
            }

            if not processed_samples:
                return characteristics

            # Analyze first sample for basic characteristics
            sample_path = processed_samples[0]

            # Get audio properties
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                sample_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                audio_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), {})

                # Basic analysis based on sample rate and duration
                sample_rate = int(audio_stream.get('sample_rate', 16000))
                duration = float(data.get('format', {}).get('duration', 0))

                # Simple heuristics for voice characteristics
                if sample_rate >= 22050:
                    characteristics["quality"] = "high"
                elif sample_rate >= 16000:
                    characteristics["quality"] = "medium"
                else:
                    characteristics["quality"] = "low"

                # Estimate speaking style based on duration vs sample count
                avg_sample_duration = duration
                if avg_sample_duration > 10:
                    characteristics["style"] = "narrative"
                elif avg_sample_duration < 5:
                    characteristics["style"] = "conversational"
                else:
                    characteristics["style"] = "neutral"

            return characteristics

        except Exception as e:
            logger.error(f"Error analyzing voice characteristics: {e}")
            return {
                "gender": "unknown",
                "age_range": "unknown",
                "style": "neutral",
                "quality": "medium"
            }

    async def _create_voice_model(
        self,
        voice_id: str,
        processed_samples: List[str],
        characteristics: Dict
    ) -> str:
        """Create voice model from processed samples"""
        try:
            model_dir = os.path.join(self.models_dir, voice_id)
            os.makedirs(model_dir, exist_ok=True)

            # For now, create a simple "model" that's just a collection of the best samples
            # In a real implementation, this would train an actual voice model

            model_config = {
                "voice_id": voice_id,
                "sample_files": [os.path.basename(s) for s in processed_samples],
                "characteristics": characteristics,
                "model_type": "sample_based",  # Simple approach for now
                "created_date": self._get_current_timestamp()
            }

            # Copy samples to model directory
            for sample in processed_samples:
                shutil.copy2(sample, model_dir)

            # Save model config
            config_path = os.path.join(model_dir, "model_config.json")
            with open(config_path, 'w') as f:
                json.dump(model_config, f, indent=2)

            logger.info(f"Voice model created: {model_dir}")
            return model_dir

        except Exception as e:
            logger.error(f"Failed to create voice model: {e}")
            raise

    async def generate_cloned_speech(
        self,
        text: str,
        voice_id: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate speech using a cloned voice

        Args:
            text: Text to convert to speech
            voice_id: ID of the cloned voice to use
            output_path: Output file path

        Returns:
            Path to generated audio file
        """
        try:
            # Load voice profile
            voice_profile = await self._load_voice_profile(voice_id)

            if not voice_profile:
                raise ValueError(f"Voice profile not found: {voice_id}")

            logger.info(f"Generating cloned speech with voice: {voice_profile['name']}")

            # For now, use a simplified approach:
            # 1. Use the best sample as a reference
            # 2. Apply voice characteristics to standard TTS
            # 3. In a real implementation, this would use the trained model

            if output_path is None:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    output_path = tmp.name

            # Generate speech with voice characteristics
            cloned_audio = await self._generate_with_voice_characteristics(
                text, voice_profile, output_path
            )

            logger.info(f"Cloned speech generated: {cloned_audio}")
            return cloned_audio

        except Exception as e:
            logger.error(f"Failed to generate cloned speech: {e}")
            raise

    async def _generate_with_voice_characteristics(
        self,
        text: str,
        voice_profile: Dict,
        output_path: str
    ) -> str:
        """Generate speech with voice characteristics applied"""
        try:
            # Import TTS service
            from .tts_service import TTSService

            tts = TTSService()

            # Choose base voice based on characteristics
            characteristics = voice_profile.get("characteristics", {})
            gender = characteristics.get("gender", "unknown")
            style = characteristics.get("style", "neutral")

            # Select appropriate base voice
            if gender == "male":
                if style == "professional":
                    base_voice = "en-US-DavisNeural"
                elif style == "narrative":
                    base_voice = "en-US-GuyNeural"
                else:
                    base_voice = "en-US-ChristopherNeural"
            elif gender == "female":
                if style == "professional":
                    base_voice = "en-US-AriaNeural"
                elif style == "conversational":
                    base_voice = "en-US-JennyNeural"
                else:
                    base_voice = "en-US-AmberNeural"
            else:
                base_voice = "en-US-AriaNeural"

            # Generate base speech
            base_audio = await tts.generate_speech(
                text=text,
                voice_id=base_voice,
                engine='edge_tts'
            )

            # Apply voice characteristics modifications
            modified_audio = await self._apply_voice_modifications(
                base_audio, voice_profile, output_path
            )

            # Clean up base audio
            if os.path.exists(base_audio):
                os.unlink(base_audio)

            return modified_audio

        except Exception as e:
            logger.error(f"Error generating with voice characteristics: {e}")
            raise

    async def _apply_voice_modifications(
        self,
        base_audio: str,
        voice_profile: Dict,
        output_path: str
    ) -> str:
        """Apply voice modifications to match cloned voice characteristics"""
        try:
            characteristics = voice_profile.get("characteristics", {})

            # Build audio filter chain based on characteristics
            filters = []

            # Pitch adjustment based on gender and style
            gender = characteristics.get("gender", "unknown")
            style = characteristics.get("style", "neutral")

            if gender == "male" and style == "professional":
                # Slightly lower pitch for authority
                filters.append("asetrate=44100*0.95,aresample=44100")
            elif gender == "female" and style == "energetic":
                # Slightly higher pitch for energy
                filters.append("asetrate=44100*1.05,aresample=44100")

            # Add subtle reverb for narrative style
            if style == "narrative":
                filters.append("aecho=0.6:0.6:125:0.2")

            # Compression for professional styles
            if style == "professional":
                filters.append("acompressor=threshold=0.1:ratio=4:attack=200:release=1000")

            # Always normalize
            filters.append("loudnorm=I=-16:LRA=11:TP=-1.5")

            # Apply filters
            if filters:
                filter_string = ','.join(filters)
                cmd = [
                    'ffmpeg',
                    '-i', base_audio,
                    '-af', filter_string,
                    '-y',
                    output_path
                ]
            else:
                # No modifications, just copy
                cmd = [
                    'ffmpeg',
                    '-i', base_audio,
                    '-y',
                    output_path
                ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(output_path):
                return output_path
            else:
                logger.error(f"Voice modification failed: {result.stderr}")
                # Fallback to original
                shutil.copy2(base_audio, output_path)
                return output_path

        except Exception as e:
            logger.error(f"Error applying voice modifications: {e}")
            shutil.copy2(base_audio, output_path)
            return output_path

    def get_available_voices(self) -> Dict:
        """Get all available cloned voices"""
        available_voices = {}

        # Add sample voices
        available_voices.update(self.sample_voices)

        # Add user-created voices
        try:
            for voice_dir in os.listdir(self.voices_dir):
                voice_path = os.path.join(self.voices_dir, voice_dir)
                if os.path.isdir(voice_path):
                    profile_file = os.path.join(voice_path, "profile.json")
                    if os.path.exists(profile_file):
                        with open(profile_file, 'r') as f:
                            profile = json.load(f)
                            available_voices[profile['voice_id']] = profile
        except Exception as e:
            logger.error(f"Error loading user voices: {e}")

        return available_voices

    def _generate_voice_id(self, voice_name: str, user_id: Optional[str]) -> str:
        """Generate unique voice ID"""
        import hashlib
        import time

        base_string = f"{voice_name}_{user_id}_{time.time()}"
        return hashlib.md5(base_string.encode()).hexdigest()[:12]

    def _get_current_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

    async def _save_voice_profile(self, voice_id: str, profile: Dict):
        """Save voice profile to disk"""
        voice_dir = os.path.join(self.voices_dir, voice_id)
        os.makedirs(voice_dir, exist_ok=True)

        profile_file = os.path.join(voice_dir, "profile.json")
        with open(profile_file, 'w') as f:
            json.dump(profile, f, indent=2)

    async def _load_voice_profile(self, voice_id: str) -> Optional[Dict]:
        """Load voice profile from disk"""
        # Check sample voices first
        if voice_id in self.sample_voices:
            return self.sample_voices[voice_id]

        # Check user voices
        voice_dir = os.path.join(self.voices_dir, voice_id)
        profile_file = os.path.join(voice_dir, "profile.json")

        if os.path.exists(profile_file):
            with open(profile_file, 'r') as f:
                return json.load(f)

        return None

    def get_voice_info(self, voice_id: str) -> Optional[Dict]:
        """Get information about a specific voice"""
        try:
            return asyncio.run(self._load_voice_profile(voice_id))
        except Exception as e:
            logger.error(f"Error getting voice info: {e}")
            return None

    def delete_voice(self, voice_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a cloned voice"""
        try:
            # Don't allow deletion of sample voices
            if voice_id in self.sample_voices:
                return False

            # Load profile to check ownership
            profile = asyncio.run(self._load_voice_profile(voice_id))
            if not profile:
                return False

            # Check ownership
            if user_id and profile.get("user_id") != user_id:
                return False

            # Delete voice directory
            voice_dir = os.path.join(self.voices_dir, voice_id)
            if os.path.exists(voice_dir):
                shutil.rmtree(voice_dir)

            # Delete model directory
            model_dir = os.path.join(self.models_dir, voice_id)
            if os.path.exists(model_dir):
                shutil.rmtree(model_dir)

            # Delete samples directory
            samples_dir = os.path.join(self.samples_dir, voice_id)
            if os.path.exists(samples_dir):
                shutil.rmtree(samples_dir)

            logger.info(f"Deleted voice: {voice_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting voice {voice_id}: {e}")
            return False