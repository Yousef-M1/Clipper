import os
import tempfile
import subprocess
import yt_dlp
from moviepy.editor import VideoFileClip
from openai import OpenAI, RateLimitError, APIError, BadRequestError
import whisper

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
                file=f
            )
        # Whisper API returns text only, fallback for timestamps
        segments = [{"start": 0.0, "end": 3.0, "text": transcript.text}]
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

def create_clip(video_path: str, start: float, end: float, output_path: str, subtitles_srt: str = None):
    """
    Trim a video (with audio) and optionally burn subtitles into it using ffmpeg.
    """
    # Make sure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Check if original video has audio
    check_audio(video_path)

    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",                    # overwrite output
        "-ss", str(start),       # start time
        "-i", video_path,        # input video
        "-t", str(end - start),  # duration (not end time)
        "-c:v", "libx264",       # video codec
        "-c:a", "aac",           # audio codec
        "-b:a", "128k",          # audio bitrate
        "-ar", "44100",          # audio sample rate
        "-ac", "2",              # stereo audio
        "-preset", "fast",       # encoding speed
        "-crf", "23"             # video quality (lower = better)
    ]

    # Burn subtitles if provided
    if subtitles_srt and os.path.exists(subtitles_srt):
        # Escape the subtitle path for ffmpeg
        escaped_srt = subtitles_srt.replace("\\", "\\\\").replace(":", "\\:")
        cmd.extend(["-vf", f"subtitles={escaped_srt}"])

    # Add output file
    cmd.append(output_path)

    # Run command with error handling
    try:
        print(f"Creating clip: {start}s to {end}s -> {output_path}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ Successfully created clip: {output_path}")

        # Verify the output has audio
        check_audio(output_path)

    except subprocess.CalledProcessError as e:
        print(f"✗ FFmpeg error: {e.stderr}")
        raise Exception(f"Failed to create clip: {e.stderr}")

    return output_path

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

# Example usage:
# clips = process_youtube_video("https://www.youtube.com/watch?v=YOUR_VIDEO_ID")
# print(clips)