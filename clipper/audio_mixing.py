"""
Audio processing and background music mixing for video clips
"""
import os
import logging
import tempfile
import subprocess
from typing import Optional, Tuple
from django.conf import settings
from core.models import BackgroundMusic

logger = logging.getLogger(__name__)

class AudioMixer:
    """
    Handles background music mixing and audio processing for video clips
    """

    def __init__(self):
        self.supported_formats = ['.mp3', '.wav', '.aac', '.m4a', '.ogg']

    def mix_background_music(
        self,
        video_path: str,
        output_path: str,
        background_music: BackgroundMusic,
        music_volume: float = 0.3,
        original_volume: float = 1.0,
        enable_ducking: bool = True,
        fade_in: float = 2.0,
        fade_out: float = 2.0
    ) -> str:
        """
        Mix background music with original video audio

        Args:
            video_path: Path to input video file
            output_path: Path for output video file
            background_music: BackgroundMusic model instance
            music_volume: Background music volume (0.0-1.0)
            original_volume: Original audio volume (0.0-1.0)
            enable_ducking: Whether to lower music when speech is detected
            fade_in: Fade in duration (seconds)
            fade_out: Fade out duration (seconds)

        Returns:
            Path to output video with mixed audio
        """
        try:
            logger.info(f"Starting audio mixing: {video_path} + {background_music.name}")

            # Get video duration
            video_duration = self._get_video_duration(video_path)
            music_duration = background_music.duration_seconds

            # Prepare background music audio
            temp_music_path = self._prepare_background_music(
                background_music.file.path,
                video_duration,
                music_volume,
                fade_in,
                fade_out
            )

            # Build FFmpeg command
            if enable_ducking:
                # Advanced mixing with audio ducking
                output = self._mix_with_ducking(
                    video_path, temp_music_path, output_path,
                    original_volume, music_volume
                )
            else:
                # Simple mixing without ducking
                output = self._mix_simple(
                    video_path, temp_music_path, output_path,
                    original_volume, music_volume
                )

            # Cleanup temporary files
            if os.path.exists(temp_music_path):
                os.remove(temp_music_path)

            logger.info(f"Audio mixing completed: {output}")
            return output

        except Exception as e:
            logger.error(f"Audio mixing failed: {e}")
            raise

    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            import json
            data = json.loads(result.stdout)
            return float(data['format']['duration'])

        except Exception as e:
            logger.error(f"Failed to get video duration: {e}")
            return 30.0  # Default fallback

    def _prepare_background_music(
        self,
        music_path: str,
        target_duration: float,
        volume: float,
        fade_in: float,
        fade_out: float
    ) -> str:
        """
        Prepare background music: loop if needed, adjust volume, add fades
        """
        temp_path = os.path.join(tempfile.gettempdir(), f"bg_music_{os.getpid()}.wav")

        try:
            # Build FFmpeg filter for background music processing
            filters = []

            # Loop music if video is longer than music
            music_duration = self._get_audio_duration(music_path)
            if target_duration > music_duration:
                # Calculate how many loops needed
                loops = int(target_duration / music_duration) + 1
                filters.append(f"aloop=loop={loops}:size={int(music_duration * 48000)}")

            # Trim to exact duration
            filters.append(f"atrim=end={target_duration}")

            # Apply volume adjustment
            if volume != 1.0:
                filters.append(f"volume={volume}")

            # Add fade in/out
            if fade_in > 0:
                filters.append(f"afade=t=in:st=0:d={fade_in}")
            if fade_out > 0:
                filters.append(f"afade=t=out:st={target_duration - fade_out}:d={fade_out}")

            # Combine all filters
            filter_complex = ",".join(filters)

            cmd = [
                'ffmpeg', '-i', music_path,
                '-af', filter_complex,
                '-y', temp_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Prepared background music: {temp_path}")
            return temp_path

        except Exception as e:
            logger.error(f"Failed to prepare background music: {e}")
            raise

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio file duration in seconds"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            import json
            data = json.loads(result.stdout)
            return float(data['format']['duration'])

        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 30.0  # Default fallback

    def _mix_simple(
        self,
        video_path: str,
        music_path: str,
        output_path: str,
        original_volume: float,
        music_volume: float
    ) -> str:
        """Simple audio mixing without ducking"""

        cmd = [
            'ffmpeg',
            '-i', video_path,      # Input video
            '-i', music_path,      # Input background music
            '-filter_complex',
            f'[0:a]volume={original_volume}[a0];'
            f'[1:a]volume={music_volume}[a1];'
            f'[a0][a1]amix=inputs=2:duration=first[aout]',
            '-map', '0:v',         # Keep original video
            '-map', '[aout]',      # Use mixed audio
            '-c:v', 'copy',        # Copy video without re-encoding
            '-c:a', 'aac',         # Encode audio as AAC
            '-y',                  # Overwrite output
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return output_path

    def _mix_with_ducking(
        self,
        video_path: str,
        music_path: str,
        output_path: str,
        original_volume: float,
        music_volume: float
    ) -> str:
        """
        Advanced mixing with audio ducking (lower music when speech detected)
        """

        # More complex filter for ducking effect
        filter_complex = (
            f'[0:a]volume={original_volume}[a0];'
            f'[1:a]volume={music_volume}[a1];'
            f'[a0][a1]sidechaincompress=threshold=0.1:ratio=4:attack=5:release=50[aout]'
        )

        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-i', music_path,
            '-filter_complex', filter_complex,
            '-map', '0:v',
            '-map', '[aout]',
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-y',
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return output_path
        except subprocess.CalledProcessError:
            # Fallback to simple mixing if ducking fails
            logger.warning("Audio ducking failed, falling back to simple mixing")
            return self._mix_simple(video_path, music_path, output_path, original_volume, music_volume)

    def validate_audio_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate if audio file is supported and get its properties

        Returns:
            (is_valid, error_message_or_info)
        """
        try:
            if not os.path.exists(file_path):
                return False, "File does not exist"

            # Check file extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in self.supported_formats:
                return False, f"Unsupported format. Supported: {', '.join(self.supported_formats)}"

            # Check if FFmpeg can read the file
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            import json
            data = json.loads(result.stdout)

            # Validate it has audio streams
            audio_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'audio']
            if not audio_streams:
                return False, "No audio streams found"

            duration = float(data['format']['duration'])
            if duration < 10:
                return False, "Audio must be at least 10 seconds long"
            if duration > 600:  # 10 minutes
                return False, "Audio must be shorter than 10 minutes"

            return True, f"Valid audio file: {duration:.1f}s, {audio_streams[0].get('codec_name', 'unknown')}"

        except Exception as e:
            return False, f"Error validating audio: {e}"


def create_preset_music_tracks():
    """
    Create some preset background music tracks from royalty-free sources
    Note: In production, you would add actual music files to your media directory
    """

    preset_tracks = [
        {
            'name': 'Upbeat Corporate',
            'category': 'corporate',
            'duration_seconds': 120.0,
            'bpm': 120,
            'artist': 'AudioJungle',
            'license_info': 'Royalty-free corporate background music'
        },
        {
            'name': 'Chill Vibes',
            'category': 'chill',
            'duration_seconds': 180.0,
            'bpm': 85,
            'artist': 'Freesound',
            'license_info': 'Creative Commons License'
        },
        {
            'name': 'Gaming Energy',
            'category': 'gaming',
            'duration_seconds': 150.0,
            'bpm': 140,
            'artist': 'Zapsplat',
            'license_info': 'Royalty-free electronic music'
        }
    ]

    created_tracks = []

    for track_data in preset_tracks:
        track, created = BackgroundMusic.objects.get_or_create(
            name=track_data['name'],
            category=track_data['category'],
            defaults={
                'duration_seconds': track_data['duration_seconds'],
                'is_preset': True,
                'bpm': track_data['bpm'],
                'artist': track_data['artist'],
                'license_info': track_data['license_info']
            }
        )

        if created:
            created_tracks.append(track)
            logger.info(f"Created preset track: {track.name}")

    return created_tracks