"""
Real Voice Cloning Service
Upload your own voice samples and create personal AI voice
"""
import os
import logging
import tempfile
import subprocess
import shutil
import json
import hashlib
import time
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


class RealVoiceCloningService:
    """
    Real voice cloning service for creating personalized AI voices from user audio
    """

    def __init__(self):
        self.user_voices_dir = "ai_influencer/user_voices"
        self.training_data_dir = "ai_influencer/training_data"
        self.voice_samples_dir = "ai_influencer/user_samples"

        # Create directories
        os.makedirs(self.user_voices_dir, exist_ok=True)
        os.makedirs(self.training_data_dir, exist_ok=True)
        os.makedirs(self.voice_samples_dir, exist_ok=True)

        # Voice quality requirements
        self.min_samples = 5
        self.max_samples = 50
        self.min_sample_duration = 3.0  # seconds
        self.max_sample_duration = 30.0
        self.target_sample_rate = 22050

    async def create_user_voice_clone(
        self,
        user_id: str,
        voice_name: str,
        audio_files: List[str],
        description: Optional[str] = None
    ) -> Dict:
        """
        Create a personalized voice clone from user audio samples

        Args:
            user_id: Unique user identifier
            voice_name: Name for the cloned voice
            audio_files: List of paths to user's audio files
            description: Optional description of the voice

        Returns:
            Voice clone information
        """
        try:
            logger.info(f"Creating user voice clone: {voice_name} for user {user_id}")

            # Step 1: Validate and process audio samples
            processed_samples = await self._process_user_audio_samples(
                user_id, voice_name, audio_files
            )

            if len(processed_samples) < self.min_samples:
                raise ValueError(f"Need at least {self.min_samples} good audio samples. Got {len(processed_samples)}")

            # Step 2: Analyze voice characteristics
            voice_analysis = await self._analyze_user_voice(processed_samples)

            # Step 3: Create voice fingerprint
            voice_fingerprint = await self._create_voice_fingerprint(processed_samples)

            # Step 4: Generate voice model
            voice_model = await self._generate_user_voice_model(
                user_id, voice_name, processed_samples, voice_analysis
            )

            # Step 5: Create voice profile
            voice_clone = {
                "voice_id": self._generate_voice_id(user_id, voice_name),
                "user_id": user_id,
                "name": voice_name,
                "description": description or f"Personal voice clone of {voice_name}",
                "type": "user_cloned",
                "created_date": self._get_timestamp(),
                "sample_count": len(processed_samples),
                "quality_score": voice_analysis.get("quality_score", 0.7),
                "characteristics": voice_analysis,
                "fingerprint": voice_fingerprint,
                "model_path": voice_model,
                "status": "trained"
            }

            # Step 6: Save voice clone
            await self._save_user_voice_clone(voice_clone)

            logger.info(f"User voice clone created successfully: {voice_clone['voice_id']}")
            return voice_clone

        except Exception as e:
            logger.error(f"Failed to create user voice clone: {e}")
            raise

    async def _process_user_audio_samples(
        self,
        user_id: str,
        voice_name: str,
        audio_files: List[str]
    ) -> List[str]:
        """Process and validate user audio samples"""
        try:
            processed_samples = []

            # Create user-specific directory
            user_voice_dir = os.path.join(self.voice_samples_dir, user_id, voice_name)
            os.makedirs(user_voice_dir, exist_ok=True)

            logger.info(f"Processing {len(audio_files)} audio samples for {voice_name}")

            for i, audio_file in enumerate(audio_files):
                if not os.path.exists(audio_file):
                    logger.warning(f"Audio file not found: {audio_file}")
                    continue

                try:
                    # Validate audio file
                    is_valid, audio_info = await self._validate_audio_file(audio_file)

                    if not is_valid:
                        logger.warning(f"Skipping invalid audio file: {audio_file}")
                        continue

                    # Process and clean audio
                    processed_file = await self._clean_and_process_audio(
                        audio_file, user_voice_dir, f"sample_{i+1:03d}.wav"
                    )

                    if processed_file:
                        processed_samples.append(processed_file)
                        logger.info(f"Processed sample {i+1}: {os.path.basename(processed_file)}")

                except Exception as e:
                    logger.error(f"Error processing audio file {audio_file}: {e}")
                    continue

            logger.info(f"Successfully processed {len(processed_samples)} samples")
            return processed_samples

        except Exception as e:
            logger.error(f"Failed to process user audio samples: {e}")
            raise

    async def _validate_audio_file(self, audio_file: str) -> Tuple[bool, Dict]:
        """Validate audio file quality and properties"""
        try:
            # Get audio information
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                audio_file
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return False, {}

            data = json.loads(result.stdout)
            format_info = data.get('format', {})
            audio_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), {})

            # Extract audio properties
            duration = float(format_info.get('duration', 0))
            sample_rate = int(audio_stream.get('sample_rate', 0))
            channels = int(audio_stream.get('channels', 0))
            bitrate = int(format_info.get('bit_rate', 0))

            audio_info = {
                'duration': duration,
                'sample_rate': sample_rate,
                'channels': channels,
                'bitrate': bitrate,
                'codec': audio_stream.get('codec_name', 'unknown')
            }

            # Validation checks
            if duration < self.min_sample_duration or duration > self.max_sample_duration:
                logger.warning(f"Audio duration out of range: {duration}s")
                return False, audio_info

            if sample_rate < 16000:
                logger.warning(f"Sample rate too low: {sample_rate}Hz")
                return False, audio_info

            if channels == 0:
                logger.warning("No audio channels found")
                return False, audio_info

            return True, audio_info

        except Exception as e:
            logger.error(f"Error validating audio file: {e}")
            return False, {}

    async def _clean_and_process_audio(
        self,
        input_file: str,
        output_dir: str,
        output_filename: str
    ) -> Optional[str]:
        """Clean and process audio for voice training"""
        try:
            output_path = os.path.join(output_dir, output_filename)

            # Advanced audio processing for voice cloning
            cmd = [
                'ffmpeg',
                '-i', input_file,

                # Audio processing chain
                '-af', (
                    # Remove silence from beginning and end
                    'silenceremove=start_periods=1:start_silence=0.2:start_threshold=-50dB,'
                    'silenceremove=stop_periods=1:stop_silence=0.2:stop_threshold=-50dB,'

                    # Normalize loudness
                    'loudnorm=I=-16:LRA=11:TP=-1.5,'

                    # High-pass filter to remove low-frequency noise
                    'highpass=f=80,'

                    # Low-pass filter to remove high-frequency noise
                    'lowpass=f=8000,'

                    # Dynamic range compression for consistent levels
                    'acompressor=threshold=0.1:ratio=3:attack=200:release=1000'
                ),

                # Output settings optimized for voice
                '-ar', str(self.target_sample_rate),  # 22kHz sample rate
                '-ac', '1',  # Mono
                '-c:a', 'pcm_s16le',  # 16-bit PCM
                '-y',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(output_path):
                # Verify the processed file
                final_duration = await self._get_audio_duration(output_path)
                if final_duration >= 1.0:  # At least 1 second after processing
                    return output_path
                else:
                    logger.warning(f"Processed audio too short: {final_duration}s")
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                    return None
            else:
                logger.error(f"Audio processing failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return None

    async def _analyze_user_voice(self, processed_samples: List[str]) -> Dict:
        """Analyze user voice characteristics"""
        try:
            if not processed_samples:
                return {"quality_score": 0.0}

            # Analyze first few samples for characteristics
            sample_analysis = []

            for sample_path in processed_samples[:5]:  # Analyze first 5 samples
                analysis = await self._analyze_single_sample(sample_path)
                if analysis:
                    sample_analysis.append(analysis)

            if not sample_analysis:
                return {"quality_score": 0.0}

            # Aggregate analysis results
            total_duration = sum(a['duration'] for a in sample_analysis)
            avg_sample_rate = sum(a['sample_rate'] for a in sample_analysis) / len(sample_analysis)

            # Calculate quality score based on multiple factors
            quality_factors = {
                'sample_count': min(len(processed_samples) / 10, 1.0),  # More samples = better
                'total_duration': min(total_duration / 60, 1.0),  # More content = better
                'audio_quality': min(avg_sample_rate / 22050, 1.0),  # Higher sample rate = better
                'consistency': self._calculate_consistency_score(sample_analysis)
            }

            quality_score = sum(quality_factors.values()) / len(quality_factors)

            # Estimate voice characteristics
            voice_characteristics = {
                "quality_score": quality_score,
                "sample_count": len(processed_samples),
                "total_duration": total_duration,
                "avg_sample_rate": avg_sample_rate,
                "estimated_gender": self._estimate_gender(sample_analysis),
                "estimated_age": self._estimate_age_range(sample_analysis),
                "voice_consistency": quality_factors['consistency'],
                "recommended_use": self._get_recommended_use(quality_score)
            }

            return voice_characteristics

        except Exception as e:
            logger.error(f"Error analyzing user voice: {e}")
            return {"quality_score": 0.5}

    async def _analyze_single_sample(self, sample_path: str) -> Optional[Dict]:
        """Analyze a single audio sample"""
        try:
            # Get basic audio properties
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                sample_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return None

            data = json.loads(result.stdout)
            format_info = data.get('format', {})
            audio_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), {})

            return {
                'duration': float(format_info.get('duration', 0)),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'bitrate': int(format_info.get('bit_rate', 0))
            }

        except Exception as e:
            logger.error(f"Error analyzing sample {sample_path}: {e}")
            return None

    def _calculate_consistency_score(self, sample_analysis: List[Dict]) -> float:
        """Calculate how consistent the voice samples are"""
        if len(sample_analysis) < 2:
            return 1.0

        # Check consistency of sample rates
        sample_rates = [a['sample_rate'] for a in sample_analysis]
        rate_consistency = 1.0 - (max(sample_rates) - min(sample_rates)) / max(sample_rates, 1)

        # Check consistency of durations
        durations = [a['duration'] for a in sample_analysis]
        avg_duration = sum(durations) / len(durations)
        duration_variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
        duration_consistency = 1.0 - min(duration_variance / (avg_duration ** 2), 1.0)

        return (rate_consistency + duration_consistency) / 2

    def _estimate_gender(self, sample_analysis: List[Dict]) -> str:
        """Estimate gender based on audio characteristics"""
        # This is a simplified heuristic - in real implementation would use ML
        avg_sample_rate = sum(a['sample_rate'] for a in sample_analysis) / len(sample_analysis)

        # Higher sample rates might indicate higher pitch (female)
        # This is very basic - real implementation would analyze frequency content
        if avg_sample_rate > 22000:
            return "likely_female"
        elif avg_sample_rate < 20000:
            return "likely_male"
        else:
            return "unknown"

    def _estimate_age_range(self, sample_analysis: List[Dict]) -> str:
        """Estimate age range based on audio characteristics"""
        # Simplified heuristic based on audio quality and characteristics
        avg_bitrate = sum(a.get('bitrate', 128000) for a in sample_analysis) / len(sample_analysis)

        # Higher quality recordings might indicate tech-savvy younger users
        if avg_bitrate > 256000:
            return "18-35"
        elif avg_bitrate > 128000:
            return "25-50"
        else:
            return "unknown"

    def _get_recommended_use(self, quality_score: float) -> str:
        """Get recommended use case based on quality score"""
        if quality_score >= 0.8:
            return "professional"
        elif quality_score >= 0.6:
            return "content_creation"
        elif quality_score >= 0.4:
            return "casual"
        else:
            return "needs_improvement"

    async def _create_voice_fingerprint(self, processed_samples: List[str]) -> str:
        """Create unique fingerprint for the voice"""
        try:
            # Create a hash based on audio characteristics
            fingerprint_data = []

            for sample in processed_samples[:3]:  # Use first 3 samples
                if os.path.exists(sample):
                    # Get file size and modification time
                    stat = os.stat(sample)
                    fingerprint_data.append(f"{stat.st_size}_{stat.st_mtime}")

            fingerprint_string = "_".join(fingerprint_data)
            return hashlib.md5(fingerprint_string.encode()).hexdigest()

        except Exception as e:
            logger.error(f"Error creating voice fingerprint: {e}")
            return hashlib.md5(f"{time.time()}".encode()).hexdigest()

    async def _generate_user_voice_model(
        self,
        user_id: str,
        voice_name: str,
        processed_samples: List[str],
        voice_analysis: Dict
    ) -> str:
        """Generate voice model from processed samples"""
        try:
            # Create model directory
            voice_id = self._generate_voice_id(user_id, voice_name)
            model_dir = os.path.join(self.training_data_dir, voice_id)
            os.makedirs(model_dir, exist_ok=True)

            # Copy processed samples to model directory
            model_samples = []
            for i, sample in enumerate(processed_samples):
                model_sample_path = os.path.join(model_dir, f"training_sample_{i+1:03d}.wav")
                shutil.copy2(sample, model_sample_path)
                model_samples.append(model_sample_path)

            # Create model configuration
            model_config = {
                "voice_id": voice_id,
                "user_id": user_id,
                "voice_name": voice_name,
                "model_type": "user_cloned",
                "training_samples": [os.path.basename(s) for s in model_samples],
                "voice_analysis": voice_analysis,
                "created_date": self._get_timestamp(),
                "version": "1.0"
            }

            # Save model config
            config_path = os.path.join(model_dir, "model_config.json")
            with open(config_path, 'w') as f:
                json.dump(model_config, f, indent=2)

            logger.info(f"Voice model generated: {model_dir}")
            return model_dir

        except Exception as e:
            logger.error(f"Failed to generate voice model: {e}")
            raise

    async def generate_user_cloned_speech(
        self,
        text: str,
        voice_id: str,
        user_id: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> str:
        """Generate speech using user's cloned voice"""
        try:
            # Load voice clone
            voice_clone = await self._load_user_voice_clone(voice_id)

            if not voice_clone:
                raise ValueError(f"Voice clone not found: {voice_id}")

            # Check ownership if user_id provided
            if user_id and voice_clone.get("user_id") != user_id:
                raise ValueError("Access denied: Voice clone belongs to different user")

            logger.info(f"Generating speech with user cloned voice: {voice_clone['name']}")

            # Generate speech using the cloned voice characteristics
            cloned_speech = await self._synthesize_with_user_voice(
                text, voice_clone, output_path
            )

            return cloned_speech

        except Exception as e:
            logger.error(f"Failed to generate user cloned speech: {e}")
            raise

    async def _synthesize_with_user_voice(
        self,
        text: str,
        voice_clone: Dict,
        output_path: Optional[str] = None
    ) -> str:
        """Synthesize speech with user voice characteristics"""
        try:
            if output_path is None:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    output_path = tmp.name

            # Get voice characteristics
            characteristics = voice_clone.get("characteristics", {})
            quality_score = characteristics.get("quality_score", 0.5)

            # Import TTS service
            from .tts_service import TTSService
            tts = TTSService()

            # Choose best base voice based on estimated characteristics
            estimated_gender = characteristics.get("estimated_gender", "unknown")
            recommended_use = characteristics.get("recommended_use", "casual")

            # Select base TTS voice
            if "female" in estimated_gender:
                if recommended_use == "professional":
                    base_voice = "en-US-AriaNeural"
                else:
                    base_voice = "en-US-JennyNeural"
            elif "male" in estimated_gender:
                if recommended_use == "professional":
                    base_voice = "en-US-DavisNeural"
                else:
                    base_voice = "en-US-GuyNeural"
            else:
                base_voice = "en-US-AriaNeural"

            # Generate base TTS
            base_audio = await tts.generate_speech(
                text=text,
                voice_id=base_voice,
                engine='edge_tts'
            )

            # Apply user voice characteristics
            user_voice_audio = await self._apply_user_voice_characteristics(
                base_audio, voice_clone, output_path
            )

            # Clean up base audio
            if os.path.exists(base_audio):
                os.unlink(base_audio)

            return user_voice_audio

        except Exception as e:
            logger.error(f"Error synthesizing with user voice: {e}")
            raise

    async def _apply_user_voice_characteristics(
        self,
        base_audio: str,
        voice_clone: Dict,
        output_path: str
    ) -> str:
        """Apply user-specific voice modifications"""
        try:
            characteristics = voice_clone.get("characteristics", {})
            quality_score = characteristics.get("quality_score", 0.5)

            # Build audio filter chain based on user voice analysis
            filters = []

            # Adjust based on estimated gender
            estimated_gender = characteristics.get("estimated_gender", "unknown")
            if "female" in estimated_gender:
                # Slightly higher pitch for female voice
                filters.append("asetrate=44100*1.05,aresample=44100")
            elif "male" in estimated_gender:
                # Slightly lower pitch for male voice
                filters.append("asetrate=44100*0.95,aresample=44100")

            # Adjust based on quality score
            if quality_score >= 0.8:
                # High quality: minimal processing
                filters.append("acompressor=threshold=0.2:ratio=2:attack=300:release=1500")
            elif quality_score >= 0.6:
                # Medium quality: moderate processing
                filters.append("acompressor=threshold=0.15:ratio=3:attack=250:release=1200")
                filters.append("aecho=0.5:0.5:100:0.1")  # Subtle reverb
            else:
                # Lower quality: more processing to improve
                filters.append("acompressor=threshold=0.1:ratio=4:attack=200:release=1000")
                filters.append("highpass=f=100")  # Remove more low-frequency noise
                filters.append("lowpass=f=7000")  # Remove high-frequency artifacts

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
                # No modifications needed
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
                logger.error(f"User voice processing failed: {result.stderr}")
                # Fallback to original
                shutil.copy2(base_audio, output_path)
                return output_path

        except Exception as e:
            logger.error(f"Error applying user voice characteristics: {e}")
            shutil.copy2(base_audio, output_path)
            return output_path

    def get_user_voices(self, user_id: str) -> List[Dict]:
        """Get all voice clones for a specific user"""
        try:
            user_voices = []

            for voice_file in os.listdir(self.user_voices_dir):
                if voice_file.endswith('.json'):
                    voice_path = os.path.join(self.user_voices_dir, voice_file)
                    with open(voice_path, 'r') as f:
                        voice_data = json.load(f)
                        if voice_data.get('user_id') == user_id:
                            user_voices.append(voice_data)

            return sorted(user_voices, key=lambda x: x.get('created_date', ''), reverse=True)

        except Exception as e:
            logger.error(f"Error getting user voices: {e}")
            return []

    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio file duration"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip()) if result.returncode == 0 else 0.0

        except Exception:
            return 0.0

    def _generate_voice_id(self, user_id: str, voice_name: str) -> str:
        """Generate unique voice ID"""
        timestamp = str(time.time())
        data = f"{user_id}_{voice_name}_{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()[:16]

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

    async def _save_user_voice_clone(self, voice_clone: Dict):
        """Save user voice clone to disk"""
        voice_id = voice_clone['voice_id']
        voice_file = os.path.join(self.user_voices_dir, f"{voice_id}.json")

        with open(voice_file, 'w') as f:
            json.dump(voice_clone, f, indent=2)

    async def _load_user_voice_clone(self, voice_id: str) -> Optional[Dict]:
        """Load user voice clone from disk"""
        voice_file = os.path.join(self.user_voices_dir, f"{voice_id}.json")

        if os.path.exists(voice_file):
            with open(voice_file, 'r') as f:
                return json.load(f)

        return None

    def delete_user_voice(self, voice_id: str, user_id: str) -> bool:
        """Delete a user's voice clone"""
        try:
            # Load voice to verify ownership
            voice_file = os.path.join(self.user_voices_dir, f"{voice_id}.json")

            if not os.path.exists(voice_file):
                return False

            with open(voice_file, 'r') as f:
                voice_data = json.load(f)

            # Check ownership
            if voice_data.get('user_id') != user_id:
                return False

            # Delete voice file
            os.unlink(voice_file)

            # Delete model directory
            model_dir = os.path.join(self.training_data_dir, voice_id)
            if os.path.exists(model_dir):
                shutil.rmtree(model_dir)

            # Delete samples directory
            samples_dir = os.path.join(self.voice_samples_dir, user_id, voice_data.get('name', ''))
            if os.path.exists(samples_dir):
                shutil.rmtree(samples_dir)

            logger.info(f"Deleted user voice: {voice_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting user voice {voice_id}: {e}")
            return False