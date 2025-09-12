from celery import shared_task
from core.models import VideoRequest, Clip
from clipper.utils import download_video, transcribe_with_whisper, detect_moments, create_clip
import tempfile
import os
from django.core.files import File
from openai.error import RateLimitError, APIError, ServiceUnavailableError, InvalidRequestError

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
        video_request.original_language = "en"  # you could auto-detect
        video_request.save()

        # 3. Detect moments
        moments = detect_moments(video_path, clip_duration=30)  # 30s clips

        # 4. Create clips
        clips_created = 0
        for moment in moments:
            output_path = os.path.join(tempfile.gettempdir(), f"clip_{clips_created}.mp4")
            create_clip(video_path, moment["start"], moment["end"], output_path)

            # Save clip in Django
            with open(output_path, "rb") as f:
                clip_file = File(f)
                Clip.objects.create(
                    video_request=video_request,
                    start_time=moment["start"],
                    end_time=moment["end"],
                    duration=moment["end"] - moment["start"],
                    file_path=clip_file,
                    status="done",
                )
            clips_created += 1

        video_request.total_clips = clips_created
        video_request.status = "done"
        video_request.save()

    except RateLimitError as e:
        # Temporary: Retry with exponential backoff
        raise self.retry(exc=e, countdown=min(60, 2 ** self.request.retries))

    except (APIError, ServiceUnavailableError) as e:
        # API unstable -> retry
        raise self.retry(exc=e, countdown=30)

    except InvalidRequestError as e:
        # Permanent error (e.g., insufficient_quota, bad request) → don’t retry
        video_request.status = "failed"
        video_request.save()
        raise

    except Exception as e:
        # Catch-all fallback
        try:
            self.retry(exc=e, countdown=10)
        except self.MaxRetriesExceededError:
            video_request.status = "failed"
            video_request.save()
