from typing import Dict, Optional, Tuple
import logging
import os
logger = logging.getLogger(__name__)

class VideoQualityManager:
    """
    Manages video quality presets and encoding settings
    """

    QUALITY_PRESETS = {
        '480p': {
            'name': '480p - Standard',
            'resolution': (854, 480),
            'bitrate': '1000k',
            'crf': 28,
            'preset': 'medium',
            'audio_bitrate': '96k',
            'file_size_multiplier': 0.3
        },
        '720p': {
            'name': '720p - HD',
            'resolution': (1280, 720),
            'bitrate': '2500k',
            'crf': 23,
            'preset': 'medium',
            'audio_bitrate': '128k',
            'file_size_multiplier': 0.6
        },
        '1080p': {
            'name': '1080p - Full HD',
            'resolution': (1920, 1080),
            'bitrate': '5000k',
            'crf': 21,
            'preset': 'medium',
            'audio_bitrate': '192k',
            'file_size_multiplier': 1.0
        },
        '1440p': {
            'name': '1440p - 2K',
            'resolution': (2560, 1440),
            'bitrate': '8000k',
            'crf': 19,
            'preset': 'slow',
            'audio_bitrate': '256k',
            'file_size_multiplier': 1.8
        },
        '2160p': {
            'name': '4K - Ultra HD',
            'resolution': (3840, 2160),
            'bitrate': '15000k',
            'crf': 17,
            'preset': 'slow',
            'audio_bitrate': '320k',
            'file_size_multiplier': 3.5
        }
    }

    COMPRESSION_LEVELS = {
        'high_quality': {
            'name': 'High Quality (Larger files)',
            'crf_modifier': -2,
            'preset': 'slow',
            'profile': 'high',
            'level': '4.1'
        },
        'balanced': {
            'name': 'Balanced (Recommended)',
            'crf_modifier': 0,
            'preset': 'medium',
            'profile': 'high',
            'level': '4.0'
        },
        'compressed': {
            'name': 'Compressed (Smaller files)',
            'crf_modifier': 3,
            'preset': 'fast',
            'profile': 'main',
            'level': '3.1'
        }
    }

    def __init__(self, quality: str = '720p', compression: str = 'balanced'):
        self.quality_preset = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS['720p'])
        self.compression_level = self.COMPRESSION_LEVELS.get(compression, self.COMPRESSION_LEVELS['balanced'])
        self.quality_name = quality
        self.compression_name = compression

    def get_ffmpeg_video_params(self) -> Dict[str, str]:
        """
        Generate FFmpeg parameters for video encoding
        """
        # Calculate final CRF value
        base_crf = self.quality_preset['crf']
        crf_modifier = self.compression_level['crf_modifier']
        final_crf = max(15, min(35, base_crf + crf_modifier))

        params = {
            'vcodec': 'libx264',
            'crf': str(final_crf),
            'preset': self.compression_level['preset'],
            'profile:v': self.compression_level['profile'],
            'level': self.compression_level['level'],
            'maxrate': self.quality_preset['bitrate'],
            'bufsize': str(int(self.quality_preset['bitrate'].replace('k', '')) * 2) + 'k',
            'movflags': '+faststart',  # For web optimization
            'pix_fmt': 'yuv420p'  # Compatibility
        }

        # Add resolution scaling if needed
        width, height = self.quality_preset['resolution']
        params['vf'] = f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2'

        return params

    def get_ffmpeg_audio_params(self) -> Dict[str, str]:
        """
        Generate FFmpeg parameters for audio encoding
        """
        return {
            'acodec': 'aac',
            'ab': self.quality_preset['audio_bitrate'],
            'ac': '2',  # Stereo
            'ar': '44100'  # Sample rate
        }

    def get_moviepy_params(self) -> Dict:
        """
        Generate parameters for MoviePy video processing
        """
        return {
            'codec': 'libx264',
            'bitrate': self.quality_preset['bitrate'],
            'preset': self.compression_level['preset'],
            'ffmpeg_params': [
                '-crf', str(self.quality_preset['crf'] + self.compression_level['crf_modifier']),
                '-profile:v', self.compression_level['profile'],
                '-level', self.compression_level['level'],
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart'
            ]
        }

    def estimate_file_size(self, duration_seconds: float) -> Tuple[float, str]:
        """
        Estimate output file size in MB
        """
        # Basic estimation formula
        video_bitrate_kbps = int(self.quality_preset['bitrate'].replace('k', ''))
        audio_bitrate_kbps = int(self.quality_preset['audio_bitrate'].replace('k', ''))
        total_bitrate_kbps = video_bitrate_kbps + audio_bitrate_kbps

        # Convert to MB (bitrate is in kilobits, we want megabytes)
        estimated_mb = (total_bitrate_kbps * duration_seconds) / (8 * 1024)

        # Apply compression modifier
        compression_factor = 1.0
        if self.compression_name == 'high_quality':
            compression_factor = 1.3
        elif self.compression_name == 'compressed':
            compression_factor = 0.7

        final_size_mb = estimated_mb * compression_factor

        # Format size string
        if final_size_mb < 1:
            size_str = f"{final_size_mb * 1024:.0f} KB"
        elif final_size_mb < 1024:
            size_str = f"{final_size_mb:.1f} MB"
        else:
            size_str = f"{final_size_mb / 1024:.1f} GB"

        return final_size_mb, size_str

    def get_quality_info(self) -> Dict:
        """
        Get detailed information about current quality settings
        """
        width, height = self.quality_preset['resolution']
        return {
            'quality_name': self.quality_preset['name'],
            'compression_name': self.compression_level['name'],
            'resolution': f"{width}x{height}",
            'video_bitrate': self.quality_preset['bitrate'],
            'audio_bitrate': self.quality_preset['audio_bitrate'],
            'crf': self.quality_preset['crf'] + self.compression_level['crf_modifier'],
            'preset': self.compression_level['preset']
        }

def create_quality_controlled_clip(
    input_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    quality: str = '720p',
    compression: str = 'balanced',
    subtitles_srt: Optional[str] = None,
    output_format: str = 'horizontal',
    custom_width: Optional[int] = None,
    custom_height: Optional[int] = None
):
    """
    Enhanced version of create_clip with quality control and subtitle burning
    """
    import subprocess

    quality_manager = VideoQualityManager(quality, compression)

    try:
        # Make sure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Build FFmpeg command with quality settings and subtitle burning
        cmd = [
            "ffmpeg",
            "-y",  # overwrite output
            "-ss", str(start_time),  # start time
            "-i", input_path,  # input video
            "-t", str(end_time - start_time),  # duration
            "-c:v", "libx264",
            "-c:a", "aac",
            "-crf", str(quality_manager.quality_preset['crf'] + quality_manager.compression_level['crf_modifier']),
            "-preset", quality_manager.compression_level['preset'],
            "-profile:v", quality_manager.compression_level['profile'],
            "-level", quality_manager.compression_level['level'],
            "-b:a", quality_manager.quality_preset['audio_bitrate'],
            "-ar", "44100",
            "-ac", "2",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart"
        ]

        # Import video format manager
        from .video_formats import VideoFormatManager

        # Determine target dimensions based on format
        if output_format == 'custom' and custom_width and custom_height:
            target_width, target_height = custom_width, custom_height
        else:
            # Get dimensions from format manager
            dimensions = VideoFormatManager.get_dimensions_for_quality(output_format, quality)
            if dimensions:
                target_width, target_height = dimensions
            else:
                # Fallback to default quality preset
                target_width, target_height = quality_manager.quality_preset['resolution']

        logger.info(f"Target output format: {output_format} ({target_width}x{target_height})")

        # Build video filter chain
        video_filters = []

        # First, get input dimensions for cropping calculation
        try:
            # Use ffprobe to get input video dimensions
            probe_cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", "-select_streams", "v:0", input_path
            ]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            import json
            probe_data = json.loads(probe_result.stdout)
            input_width = int(probe_data['streams'][0]['width'])
            input_height = int(probe_data['streams'][0]['height'])

            # Add crop filter if needed to maintain aspect ratio
            crop_filter = VideoFormatManager.get_crop_filter(output_format, input_width, input_height)
            if crop_filter:
                video_filters.append(crop_filter)
                logger.info(f"Adding crop filter: {crop_filter}")

        except Exception as e:
            logger.warning(f"Could not determine input dimensions for cropping: {e}")

        # Add scaling filter
        scale_filter = f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black"
        video_filters.append(scale_filter)

        # Add subtitle filter if subtitles exist
        if subtitles_srt and os.path.exists(subtitles_srt):
            # Escape the subtitle path for FFmpeg
            escaped_srt = subtitles_srt.replace("\\", "\\\\").replace(":", "\\:")
            video_filters.append(f"subtitles={escaped_srt}")

            logger.info(f"Using subtitle file: {subtitles_srt}")
        else:
            logger.warning(f"No subtitle file found or file doesn't exist: {subtitles_srt}")

        # Combine all video filters
        video_filter = ",".join(video_filters)
        cmd.extend(["-vf", video_filter])

        logger.info(f"FFmpeg video filter chain: {video_filter}")

        # Add output file
        cmd.append(output_path)

        # Run FFmpeg command
        logger.info(f"Creating quality-controlled clip with subtitles: {output_path}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Estimate and log file size
        duration = end_time - start_time
        estimated_size_mb, size_str = quality_manager.estimate_file_size(duration)

        logger.info(f"Created {quality} clip: {output_path}")
        logger.info(f"Quality: {quality_manager.get_quality_info()}")
        logger.info(f"Estimated size: {size_str}")

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        raise Exception(f"Failed to create quality controlled clip: {e.stderr}")
    except Exception as e:
        logger.error(f"Failed to create quality controlled clip: {e}")
        raise

def get_available_quality_presets() -> Dict[str, Dict]:
    """
    Return all available quality presets
    """
    return VideoQualityManager.QUALITY_PRESETS

def get_available_compression_levels() -> Dict[str, Dict]:
    """
    Return all available compression levels
    """
    return VideoQualityManager.COMPRESSION_LEVELS

# Integration example for your models.py
class VideoProcessingSettings:
    """
    Add this to your models or as a separate settings class
    """
    def __init__(self):
        self.quality_preset = '720p'
        self.compression_level = 'balanced'
        self.caption_style = 'modern_purple'
        self.moment_detection_type = 'ai_powered'  # or 'fixed_intervals'
        self.max_clips = 10
        self.clip_duration = 30