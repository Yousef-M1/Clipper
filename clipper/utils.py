import yt_dlp
import os
import tempfile
from openai import OpenAI, RateLimitError, APIError, BadRequestError
import subprocess
from moviepy.editor import VideoFileClip
import whisper

# ---------------------------
# Video Download
# ---------------------------
def download_video(url: str) -> str:
    """Download video using yt-dlp and return the file path."""
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, '%(id)s.%(ext)s')

    ydl_opts = {
        'format': 'mp4',
        'outtmpl': output_path,
        'noplaylist': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    return filename

# ---------------------------
# OpenAI Client
# ---------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------
# Transcription
# ---------------------------
def transcribe_with_whisper(video_path: str):
    """
    Transcribe video and return a list of segments with text + timestamps.
    Each segment: {"start": float, "end": float, "text": str}
    """
    try:
        with open(video_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        # OpenAI Whisper returns only text
        segments = [{"start": 0.0, "end": 3.0, "text": transcript.text}]
        return segments

    except (RateLimitError, APIError, BadRequestError) as e:
        print(f"OpenAI API error ({e}), using local Whisper fallback.")
        model = whisper.load_model("base")
        result = model.transcribe(video_path)
        segments = result.get("segments", [])
        return segments

# ---------------------------
# Clip detection
# ---------------------------
def detect_moments(video_path: str, clip_duration: float = 30.0):
    """Detect moments in a video and return start/end times for each clip."""
    moments = []
    with VideoFileClip(video_path) as video:
        total_duration = video.duration
    start = 0.0
    while start < total_duration:
        end = min(start + clip_duration, total_duration)
        moments.append({"start": start, "end": end})
        start = end
    return moments

# ---------------------------
# SRT Writer
# ---------------------------
def write_srt(segments, srt_path: str):
    """Generate SRT file from Whisper segments."""
    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            start_time = format_time(seg["start"])
            end_time = format_time(seg["end"])
            text = seg["text"].strip()
            f.write(f"{i+1}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")

    if not os.path.isfile(srt_path):
        raise FileNotFoundError(f"SRT file not created: {srt_path}")
    return srt_path

# ---------------------------
# Create Video Clip
# ---------------------------
def create_clip(video_path: str, start: float, end: float, output_path: str, subtitles_srt: str = None):
    """
    Trim video using ffmpeg, burn subtitles if provided, keeping audio in sync.
    """
    if subtitles_srt and not os.path.exists(subtitles_srt):
        raise FileNotFoundError(f"SRT file not found: {subtitles_srt}")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-ss", str(start),
        "-to", str(end),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart"
    ]

    # Burn subtitles if provided
    if subtitles_srt:
        cmd.extend([
            "-filter_complex",
            f"subtitles={subtitles_srt}:force_style='FontName=DejaVuSans,FontSize=24'"
        ])

    cmd.append(output_path)

    # Run ffmpeg and capture errors
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg error:", result.stderr)
        raise RuntimeError(f"FFmpeg failed for clip {output_path}")

    return output_path
