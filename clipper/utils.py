import yt_dlp
import os
import tempfile
from openai import OpenAI
import subprocess
from moviepy.editor import VideoFileClip

def download_video(url: str) -> str:
    """"Download video using yt-dlp and return the file path."""

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



# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # get key from env variable

def transcribe_with_whisper(video_path: str):
    with open(video_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    return transcript.text



def detect_moments(video_path: str, clip_duration: float = 30.0):
    """
    Detect moments in a video and return start/end times for each clip.

    Args:
        video_path (str): Path to the video file.
        clip_duration (float): Duration of each clip in seconds (default 30s).

    Returns:
        List[dict]: List of {"start": float, "end": float} for each clip.
    """
    moments = []

    # Load video to get total duration
    with VideoFileClip(video_path) as video:
        total_duration = video.duration  # in seconds

    start = 0.0
    while start < total_duration:
        end = min(start + clip_duration, total_duration)
        moments.append({"start": start, "end": end})
        start = end

    return moments


def create_clip(video_path: str, start: float, end: float, output_path: str):
    """Trim video with ffmpeg"""
    cmd = [
        "ffmpeg",
        "-y",  # overwrite
        "-i", video_path,
        "-ss", str(start),
        "-to", str(end),
        "-c:v", "libx264",
        "-c:a", "aac",
        output_path
    ]
    subprocess.run(cmd, check=True)
    return output_path


