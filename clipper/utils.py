import os
import tempfile
import subprocess
import yt_dlp
from moviepy.editor import VideoFileClip
from openai import OpenAI, RateLimitError, APIError, BadRequestError
import whisper
import json
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def download_video(url: str) -> str:
    """Download YouTube video using yt-dlp and return file path."""
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        'format': 'best[ext=mp4]/best',  # Prefer mp4, fallback to best quality
        'outtmpl': output_path,
        'noplaylist': True,
        'extractaudio': False,  # Keep video with audio
        'writesubtitles': False,
        'writeautomaticsub': False
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return filename

def check_audio(video_path: str):
    """Check if video has audio streams."""
    try:
        cmd = ["ffprobe", "-v", "quiet", "-show_streams", "-select_streams", "a", video_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip():
            print(f"✓ Video has audio streams: {video_path}")
            return True
        else:
            print(f"✗ Video has NO audio streams: {video_path}")
            return False
    except Exception as e:
        print(f"Error checking audio: {e}")
        return False

def transcribe_with_whisper(video_path: str):
    """Transcribe video audio using OpenAI Whisper or local fallback."""
    try:
        with open(video_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json"  # Get timestamps
            )
        # Convert to segments format
        segments = []
        if hasattr(transcript, 'segments'):
            segments = transcript.segments
        else:
            # Fallback if no segments
            segments = [{"start": 0.0, "end": 30.0, "text": transcript.text}]

    except (RateLimitError, APIError, BadRequestError) as e:
        print(f"OpenAI API failed ({e}), using local Whisper fallback.")
        model = whisper.load_model("base")
        result = model.transcribe(video_path)
        segments = result.get("segments", [])
    return segments

def write_srt(segments, srt_path: str):
    """Write segments to an SRT subtitle file."""
    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            start_time = format_time(seg["start"])
            end_time = format_time(seg["end"])
            text = seg["text"].strip()
            f.write(f"{i+1}\n{start_time} --> {end_time}\n{text}\n\n")
    return srt_path

def detect_moments(video_path: str, clip_duration: float = 30.0):
    """Split video into clip moments based on duration."""
    moments = []
    with VideoFileClip(video_path) as video:
        total_duration = video.duration

    start = 0.0
    while start < total_duration:
        end = min(start + clip_duration, total_duration)
        moments.append({"start": start, "end": end})
        start = end
    return moments

def create_clip(video_path: str, start: float, end: float, output_path: str, subtitles_srt: str = None, quality_settings: dict = None):
    """
    Enhanced clip creation with quality control and subtitle styling.
    """
    # Make sure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Check if original video has audio
    check_audio(video_path)

    # Default quality settings
    if quality_settings is None:
        quality_settings = {
            'video_codec': 'libx264',
            'audio_codec': 'aac',
            'crf': 23,
            'preset': 'fast',
            'audio_bitrate': '128k',
            'audio_sample_rate': '44100',
            'audio_channels': '2'
        }

    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",                    # overwrite output
        "-ss", str(start),       # start time
        "-i", video_path,        # input video
        "-t", str(end - start),  # duration (not end time)
        "-c:v", quality_settings.get('video_codec', 'libx264'),
        "-c:a", quality_settings.get('audio_codec', 'aac'),
        "-b:a", quality_settings.get('audio_bitrate', '128k'),
        "-ar", quality_settings.get('audio_sample_rate', '44100'),
        "-ac", quality_settings.get('audio_channels', '2'),
        "-preset", quality_settings.get('preset', 'fast'),
        "-crf", str(quality_settings.get('crf', 23))
    ]

    # Add resolution scaling if specified
    if 'resolution' in quality_settings:
        width, height = quality_settings['resolution']
        scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"

        # Combine with subtitle filter if needed
        if subtitles_srt and os.path.exists(subtitles_srt):
            escaped_srt = subtitles_srt.replace("\\", "\\\\").replace(":", "\\:")
            combined_filter = f"{scale_filter},subtitles={escaped_srt}"
            cmd.extend(["-vf", combined_filter])
        else:
            cmd.extend(["-vf", scale_filter])
    elif subtitles_srt and os.path.exists(subtitles_srt):
        # Just burn subtitles without scaling
        escaped_srt = subtitles_srt.replace("\\", "\\\\").replace(":", "\\:")
        cmd.extend(["-vf", f"subtitles={escaped_srt}"])

    # Add additional quality parameters
    if 'profile' in quality_settings:
        cmd.extend(["-profile:v", quality_settings['profile']])
    if 'level' in quality_settings:
        cmd.extend(["-level", quality_settings['level']])
    if 'pix_fmt' in quality_settings:
        cmd.extend(["-pix_fmt", quality_settings['pix_fmt']])

    # Add output file
    cmd.append(output_path)

    # Run command with error handling
    try:
        logger.info(f"Creating clip: {start}s to {end}s -> {output_path}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"✓ Successfully created clip: {output_path}")

        # Verify the output has audio
        check_audio(output_path)

    except subprocess.CalledProcessError as e:
        logger.error(f"✗ FFmpeg error: {e.stderr}")
        raise Exception(f"Failed to create clip: {e.stderr}")

    return output_path

# NEW FUNCTIONS FOR ENHANCED FEATURES

def get_video_info(video_path: str) -> dict:
    """Get video information using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)

        # Extract relevant information
        video_stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)

        return {
            'duration': float(info['format']['duration']),
            'width': int(video_stream['width']) if video_stream else 0,
            'height': int(video_stream['height']) if video_stream else 0,
            'fps': eval(video_stream['r_frame_rate']) if video_stream else 0,
            'has_audio': audio_stream is not None,
            'file_size': int(info['format']['size']),
            'format_name': info['format']['format_name']
        }
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return {}

def analyze_audio_energy(video_path: str, segment_duration: float = 5.0) -> list:
    """
    Analyze audio energy levels across video segments.
    Returns list of energy scores for each segment.
    """
    try:
        # Use ffmpeg to extract audio energy data
        cmd = [
            "ffmpeg", "-i", video_path, "-af",
            "volumedetect,astats=metadata=1:reset=1",
            "-f", "null", "-"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse energy data from ffmpeg output
        # This is a simplified version - in production, you'd use librosa
        energy_scores = []

        with VideoFileClip(video_path) as video:
            total_duration = video.duration
            current_time = 0

            while current_time < total_duration:
                # Simplified energy calculation
                # In real implementation, analyze actual audio data
                energy_score = 5.0  # Placeholder
                energy_scores.append({
                    'start': current_time,
                    'end': min(current_time + segment_duration, total_duration),
                    'energy': energy_score
                })
                current_time += segment_duration

        return energy_scores

    except Exception as e:
        logger.error(f"Error analyzing audio energy: {e}")
        return []

def create_styled_clip(
    video_path: str,
    start: float,
    end: float,
    output_path: str,
    style_settings: dict = None,
    quality_settings: dict = None
):
    """
    Create a clip with advanced styling options.
    """
    if style_settings is None:
        style_settings = {}

    if quality_settings is None:
        quality_settings = {
            'crf': 23,
            'preset': 'fast',
            'resolution': None
        }

    # Merge quality settings for create_clip
    enhanced_quality = {
        **quality_settings,
        'video_codec': 'libx264',
        'audio_codec': 'aac',
        'audio_bitrate': '128k',
        'audio_sample_rate': '44100',
        'audio_channels': '2',
        'pix_fmt': 'yuv420p',
        'profile': 'high',
        'level': '4.0'
    }

    # Create the clip using enhanced settings
    return create_clip(
        video_path,
        start,
        end,
        output_path,
        subtitles_srt=style_settings.get('subtitles_srt'),
        quality_settings=enhanced_quality
    )

def validate_processing_settings(settings: dict) -> dict:
    """Validate and sanitize processing settings."""
    validated = {}

    # Clip settings
    validated['clip_duration'] = max(5.0, min(120.0, settings.get('clip_duration', 30.0)))
    validated['max_clips'] = max(1, min(50, settings.get('max_clips', 10)))

    # Quality settings
    quality_options = ['480p', '720p', '1080p', '1440p', '2160p']
    validated['video_quality'] = settings.get('video_quality', '720p')
    if validated['video_quality'] not in quality_options:
        validated['video_quality'] = '720p'

    # Compression settings
    compression_options = ['high_quality', 'balanced', 'compressed']
    validated['compression_level'] = settings.get('compression_level', 'balanced')
    if validated['compression_level'] not in compression_options:
        validated['compression_level'] = 'balanced'

    # Caption settings
    caption_options = ['modern_purple', 'tiktok_style', 'youtube_style', 'instagram_story', 'podcast_style']
    validated['caption_style'] = settings.get('caption_style', 'modern_purple')
    if validated['caption_style'] not in caption_options:
        validated['caption_style'] = 'modern_purple'

    # Detection type
    detection_options = ['ai_powered', 'fixed_intervals']
    validated['moment_detection_type'] = settings.get('moment_detection_type', 'ai_powered')
    if validated['moment_detection_type'] not in detection_options:
        validated['moment_detection_type'] = 'ai_powered'

    # Boolean settings
    validated['enable_word_highlighting'] = bool(settings.get('enable_word_highlighting', True))

    return validated

# Keep all your existing functions...

def split_and_burn_subtitles(video_path: str, segments, clip_duration: float = 30.0, output_dir: str = None):
    """Split video into clips, generate per-clip SRTs, and burn subtitles."""
    if output_dir is None:
        output_dir = tempfile.gettempdir()

    print(f"Output directory: {output_dir}")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    clips = []
    moments = detect_moments(video_path, clip_duration)

    print(f"Found {len(moments)} moments to process")

    for idx, moment in enumerate(moments):
        output_path = os.path.join(output_dir, f"clip_{idx:03d}.mp4")
        srt_path = os.path.join(output_dir, f"clip_{idx:03d}.srt")

        print(f"Processing moment {idx + 1}/{len(moments)}: {moment['start']:.1f}s - {moment['end']:.1f}s")

        # Filter only segments that overlap this moment
        clip_segments = []
        for seg in segments:
            # Check if segment overlaps with this moment
            if seg["start"] < moment["end"] and seg["end"] > moment["start"]:
                # Adjust timing relative to clip start
                adjusted_seg = {
                    "start": max(0, seg["start"] - moment["start"]),
                    "end": min(moment["end"] - moment["start"], seg["end"] - moment["start"]),
                    "text": seg["text"]
                }
                # Only add if the segment has positive duration
                if adjusted_seg["end"] > adjusted_seg["start"]:
                    clip_segments.append(adjusted_seg)

        # Write SRT file for this clip if there are subtitles
        subtitles = None
        if clip_segments:
            write_srt(clip_segments, srt_path)
            subtitles = srt_path
            print(f"  Created SRT with {len(clip_segments)} segments")

        # Create video clip with or without subtitles
        try:
            create_clip(video_path, moment["start"], moment["end"], output_path, subtitles_srt=subtitles)
            clips.append(output_path)
            print(f"  ✓ Clip {idx + 1} created successfully")
        except Exception as e:
            print(f"  ✗ Failed to create clip {idx + 1}: {e}")
            continue

        # Cleanup temporary SRT file
        if subtitles and os.path.exists(srt_path):
            try:
                os.remove(srt_path)
            except Exception as e:
                print(f"Warning: Could not remove temp SRT file {srt_path}: {e}")

    print(f"Successfully created {len(clips)} clips out of {len(moments)} moments")
    return clips

def process_youtube_video(url: str, clip_duration: float = 30.0, output_dir: str = None):
    """Complete pipeline to process YouTube video into clips with subtitles."""
    try:
        # Download video
        print("Downloading video...")
        video_path = download_video(url)
        print(f"Downloaded: {video_path}")

        # Check if downloaded video has audio
        if not check_audio(video_path):
            print("Warning: Downloaded video has no audio!")

        # Transcribe audio
        print("Transcribing audio...")
        segments = transcribe_with_whisper(video_path)
        print(f"Found {len(segments)} transcript segments")

        # Split into clips
        print("Creating clips...")
        clips = split_and_burn_subtitles(video_path, segments, clip_duration, output_dir)

        # Cleanup original video
        try:
            os.remove(video_path)
            print(f"Cleaned up original video: {video_path}")
        except Exception as e:
            print(f"Warning: Could not remove original video {video_path}: {e}")

        return clips

    except Exception as e:
        print(f"Error processing video: {e}")
        raise