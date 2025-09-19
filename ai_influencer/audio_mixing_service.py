"""
Audio Mixing Service for TTS + Background Music
Professional audio mixing for content creation
"""
import os
import logging
import subprocess
import tempfile
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioMixingService:
    """
    Professional audio mixing service for TTS + background music
    """

    def __init__(self):
        self.music_dir = "ai_influencer/background_music"
        os.makedirs(self.music_dir, exist_ok=True)

        # Initialize music library
        self._create_music_library()

    def _create_music_library(self):
        """Create a library of background music tracks"""
        self.music_library = {
            "corporate": {
                "name": "Corporate Background",
                "description": "Professional business music",
                "mood": "professional",
                "genre": "corporate",
                "duration": 60,  # seconds
                "file": "corporate_bg.mp3"
            },
            "upbeat": {
                "name": "Upbeat Energy",
                "description": "Energetic and motivational",
                "mood": "energetic",
                "genre": "pop",
                "duration": 45,
                "file": "upbeat_energy.mp3"
            },
            "chill": {
                "name": "Chill Vibes",
                "description": "Relaxed and calm",
                "mood": "relaxed",
                "genre": "ambient",
                "duration": 90,
                "file": "chill_vibes.mp3"
            },
            "tech": {
                "name": "Tech Innovation",
                "description": "Modern technology theme",
                "mood": "futuristic",
                "genre": "electronic",
                "duration": 75,
                "file": "tech_innovation.mp3"
            },
            "podcast": {
                "name": "Podcast Intro",
                "description": "Perfect for podcast intros",
                "mood": "professional",
                "genre": "ambient",
                "duration": 30,
                "file": "podcast_intro.mp3"
            },
            "2pac": {
                "name": "2Pac - Hit 'Em Up",
                "description": "Real hip-hop track for testing",
                "mood": "aggressive",
                "genre": "hip-hop",
                "duration": 300,  # Will be detected automatically
                "file": "2Pac - Hit 'Em Up (Dirty) (Music Video) HD.mp3",
                "is_real_file": True,
                "file_path": "./2Pac - Hit 'Em Up (Dirty) (Music Video) HD.mp3"
            }
        }

        # Generate music tracks if they don't exist
        self._generate_music_tracks()

    def _generate_music_tracks(self):
        """Generate background music tracks using FFmpeg tones"""
        for track_id, track_info in self.music_library.items():
            # Skip real files - they already exist
            if track_info.get("is_real_file", False):
                continue

            track_path = os.path.join(self.music_dir, track_info["file"])

            if not os.path.exists(track_path):
                try:
                    self._create_background_track(track_id, track_path, track_info)
                    logger.info(f"Generated music track: {track_id}")
                except Exception as e:
                    logger.error(f"Failed to generate track {track_id}: {e}")

    def _create_background_track(self, track_id: str, output_path: str, track_info: Dict):
        """Create a background music track using FFmpeg audio synthesis"""
        duration = track_info["duration"]

        # Simplified approach - single sine wave for each track
        if track_info["mood"] == "professional":
            # Corporate: Gentle low frequency
            frequency = 220
            volume = 0.15
        elif track_info["mood"] == "energetic":
            # Upbeat: Higher frequency
            frequency = 440
            volume = 0.2
        elif track_info["mood"] == "relaxed":
            # Chill: Very low, soft
            frequency = 110
            volume = 0.1
        elif track_info["mood"] == "futuristic":
            # Tech: Higher tech frequency
            frequency = 523
            volume = 0.15
        else:
            # Default: Medium frequency
            frequency = 261
            volume = 0.12

        # Simple single sine wave command
        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'sine=frequency={frequency}:duration={duration}',
            '-af', f'volume={volume}',
            '-c:a', 'mp3',
            '-b:a', '128k',
            '-y',
            output_path
        ]

        subprocess.run(cmd, capture_output=True, check=True)

    async def mix_tts_with_music(
        self,
        tts_audio_path: str,
        music_track: str = "corporate",
        voice_volume: float = 1.0,
        music_volume: float = 0.3,
        fade_in: float = 2.0,
        fade_out: float = 2.0,
        output_path: Optional[str] = None
    ) -> str:
        """
        Mix TTS audio with background music

        Args:
            tts_audio_path: Path to TTS audio file
            music_track: Music track ID from library
            voice_volume: Voice volume (0.0 to 1.0)
            music_volume: Music volume (0.0 to 1.0)
            fade_in: Fade in duration in seconds
            fade_out: Fade out duration in seconds
            output_path: Output file path

        Returns:
            Path to mixed audio file
        """
        try:
            if not os.path.exists(tts_audio_path):
                raise FileNotFoundError(f"TTS audio file not found: {tts_audio_path}")

            if music_track not in self.music_library:
                raise ValueError(f"Unknown music track: {music_track}")

            # Get music file path
            track_info = self.music_library[music_track]

            if track_info.get("is_real_file", False):
                # Use real file path
                music_path = track_info["file_path"]
            else:
                # Use generated file
                music_file = track_info["file"]
                music_path = os.path.join(self.music_dir, music_file)

                if not os.path.exists(music_path):
                    # Generate the track if it doesn't exist
                    self._create_background_track(
                        music_track,
                        music_path,
                        track_info
                    )

            # Create output path if not provided
            if output_path is None:
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                    output_path = tmp.name

            # Get TTS audio duration
            duration_result = subprocess.run([
                'ffprobe', '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                tts_audio_path
            ], capture_output=True, text=True)

            tts_duration = float(duration_result.stdout.strip()) if duration_result.returncode == 0 else 10.0

            # Mix audio with professional effects
            cmd = [
                'ffmpeg',
                '-i', tts_audio_path,  # Voice input
                '-i', music_path,      # Music input
                '-filter_complex',
                f'[1:a]volume={music_volume},afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0, tts_duration-fade_out)}:d={fade_out}[music];'
                f'[0:a]volume={voice_volume}[voice];'
                f'[voice][music]amix=inputs=2:duration=first:weights=1.0 0.8[mixed];'
                f'[mixed]highpass=f=80,lowpass=f=15000,dynaudnorm=p=0.71:m=12.0:s=5.0[final]',
                '-map', '[final]',
                '-c:a', 'mp3',
                '-b:a', '192k',
                '-ar', '44100',
                '-y',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Successfully mixed TTS with background music: {output_path}")
                return output_path
            else:
                logger.error(f"Audio mixing failed: {result.stderr}")
                raise RuntimeError(f"Audio mixing failed: {result.stderr}")

        except Exception as e:
            logger.error(f"Failed to mix audio: {e}")
            raise

    def get_available_music(self) -> Dict:
        """Get available background music tracks"""
        return {
            track_id: {
                "name": info["name"],
                "description": info["description"],
                "mood": info["mood"],
                "genre": info["genre"],
                "duration": info["duration"]
            }
            for track_id, info in self.music_library.items()
        }

    async def apply_audio_effects(
        self,
        audio_path: str,
        effects: Dict,
        output_path: Optional[str] = None
    ) -> str:
        """
        Apply audio effects to an audio file

        Args:
            audio_path: Input audio file
            effects: Dictionary of effects to apply
            output_path: Output file path

        Effects can include:
            - reverb: bool
            - echo: bool
            - normalize: bool
            - compress: bool
            - speed: float (0.5 to 2.0)
            - pitch: float (-12 to 12 semitones)
        """
        try:
            if output_path is None:
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                    output_path = tmp.name

            # Build filter chain
            filters = []

            # Speed adjustment
            if effects.get('speed', 1.0) != 1.0:
                speed = max(0.5, min(2.0, effects['speed']))
                filters.append(f'atempo={speed}')

            # Pitch adjustment
            if effects.get('pitch', 0) != 0:
                pitch = max(-12, min(12, effects['pitch']))
                # Convert semitones to frequency ratio
                ratio = 2 ** (pitch / 12)
                filters.append(f'asetrate=44100*{ratio},aresample=44100')

            # Reverb effect
            if effects.get('reverb', False):
                filters.append('aecho=0.8:0.9:500:0.3')

            # Echo effect
            if effects.get('echo', False):
                filters.append('aecho=0.8:0.88:60:0.4')

            # Compression
            if effects.get('compress', False):
                filters.append('acompressor=threshold=0.089:ratio=9:attack=200:release=1000')

            # Normalization
            if effects.get('normalize', True):
                filters.append('loudnorm=I=-16:LRA=11:TP=-1.5')

            # Create FFmpeg command
            if filters:
                filter_string = ','.join(filters)
                cmd = [
                    'ffmpeg',
                    '-i', audio_path,
                    '-af', filter_string,
                    '-c:a', 'mp3',
                    '-b:a', '192k',
                    '-y',
                    output_path
                ]
            else:
                # No effects, just copy
                cmd = [
                    'ffmpeg',
                    '-i', audio_path,
                    '-c:a', 'mp3',
                    '-b:a', '192k',
                    '-y',
                    output_path
                ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Applied audio effects successfully: {output_path}")
                return output_path
            else:
                logger.error(f"Audio effects failed: {result.stderr}")
                raise RuntimeError(f"Audio effects failed: {result.stderr}")

        except Exception as e:
            logger.error(f"Failed to apply audio effects: {e}")
            raise

    async def create_professional_audio(
        self,
        tts_audio_path: str,
        music_track: str = "corporate",
        voice_volume: float = 1.0,
        music_volume: float = 0.3,
        effects: Optional[Dict] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Create professional-quality audio with music + effects

        This is the main function that combines TTS + music + effects
        """
        try:
            # Step 1: Mix TTS with background music
            mixed_path = await self.mix_tts_with_music(
                tts_audio_path=tts_audio_path,
                music_track=music_track,
                voice_volume=voice_volume,
                music_volume=music_volume
            )

            # Step 2: Apply audio effects if specified
            if effects:
                final_path = await self.apply_audio_effects(
                    audio_path=mixed_path,
                    effects=effects,
                    output_path=output_path
                )

                # Clean up intermediate file
                if os.path.exists(mixed_path) and mixed_path != final_path:
                    os.unlink(mixed_path)

                return final_path
            else:
                # No effects, just return mixed audio
                if output_path and mixed_path != output_path:
                    import shutil
                    shutil.move(mixed_path, output_path)
                    return output_path
                return mixed_path

        except Exception as e:
            logger.error(f"Failed to create professional audio: {e}")
            raise

    def get_audio_info(self, audio_path: str) -> Dict:
        """Get information about an audio file"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)

                format_info = data.get('format', {})
                streams = data.get('streams', [])
                audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), {})

                return {
                    'duration': float(format_info.get('duration', 0)),
                    'size': int(format_info.get('size', 0)),
                    'bitrate': int(format_info.get('bit_rate', 0)),
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'channels': int(audio_stream.get('channels', 0)),
                    'codec': audio_stream.get('codec_name', 'unknown')
                }
            else:
                return {}

        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            return {}