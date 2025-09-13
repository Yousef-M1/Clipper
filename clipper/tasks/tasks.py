from celery import shared_task
from core.models import VideoRequest, Clip
from clipper.utils import download_video, transcribe_with_whisper, detect_moments, create_clip, write_srt
import tempfile
import os
from django.core.files.base import ContentFile
from openai import RateLimitError, APIError, BadRequestError
import logging

logger = logging.getLogger(__name__)

def write_clip_srt(segments, srt_path):
    """Write SRT and ensure the file exists."""
    write_srt(segments, srt_path)
    if not os.path.isfile(srt_path):
        raise FileNotFoundError(f"SRT file not found: {srt_path}")
    return srt_path

@shared_task(bind=True, max_retries=3)
def process_video_request(self, video_request_id):
    video_request = VideoRequest.objects.get(id=video_request_id)
    video_request.status = "processing"
    video_request.save()

    try:
        # 1. Download video
        video_path = download_video(video_request.url)

        # 2. Transcribe video
        transcript = transcribe_with_whisper(video_path)
        video_request.original_language = "en"  # or auto-detect
        video_request.save()

        # 3. Detect moments
        moments = detect_moments(video_path, clip_duration=30)  # 30s clips

        # 4. Create clips
        clips_created = 0
        for moment in moments:
            output_path = os.path.join(tempfile.gettempdir(), f"clip_{clips_created}.mp4")
            srt_path = os.path.join(tempfile.gettempdir(), f"clip_{clips_created}.srt")

            # Filter segments for this clip time range
            clip_segments = [
                seg for seg in transcript
                if seg["start"] < moment["end"] and seg["end"] > moment["start"]
            ]
            # Adjust segment times relative to clip start
            for seg in clip_segments:
                seg["start"] = max(0, seg["start"] - moment["start"])
                seg["end"] = seg["end"] - moment["start"]

            # Write and check SRT
            write_clip_srt(clip_segments, srt_path)

            # Trim video & include audio/subtitles
            create_clip(video_path, moment["start"], moment["end"], output_path, subtitles_srt=srt_path)

            # Save clip in Django storage
            with open(output_path, "rb") as f:
                clip_content = ContentFile(f.read())
                clip_instance = Clip.objects.create(
                    video_request=video_request,
                    start_time=moment["start"],
                    end_time=moment["end"],
                    duration=moment["end"] - moment["start"],
                    status="done",
                )
                clip_instance.file_path.save(f"clip_{clips_created}.mp4", clip_content)

            logger.info(f"Created clip {clips_created} for video_request {video_request_id}")
            os.remove(output_path)
            os.remove(srt_path)
            clips_created += 1

        video_request.total_clips = clips_created
        video_request.status = "done"
        video_request.save()

    except RateLimitError as e:
        raise self.retry(exc=e, countdown=min(60, 2 ** self.request.retries))

    except APIError as e:
        raise self.retry(exc=e, countdown=30)

    except BadRequestError as e:
        video_request.status = "failed"
        video_request.save()
        raise

    except Exception as e:
        try:
            self.retry(exc=e, countdown=10)
        except self.MaxRetriesExceededError:
            video_request.status = "failed"
            video_request.save()
