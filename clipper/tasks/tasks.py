from celery import shared_task
from core.models import VideoRequest, Clip
from clipper.utils import download_video, transcribe_with_whisper, create_clip, write_srt, check_audio
import tempfile
import os
from django.core.files.base import ContentFile
from openai import RateLimitError, APIError, BadRequestError
import logging

logger = logging.getLogger(__name__)

def write_clip_srt(segments, srt_path):
    """Write SRT and ensure the file exists."""
    # Clamp negative times and filter out invalid segments
    valid_segments = []
    for seg in segments:
        start = max(0, seg["start"])
        end = max(0, seg["end"])
        # Only include segments with positive duration and text
        if end > start and seg["text"].strip():
            valid_segments.append({
                "start": start,
                "end": end,
                "text": seg["text"].strip()
            })

    if not valid_segments:
        logger.warning(f"No valid segments for SRT file: {srt_path}")
        return None

    write_srt(valid_segments, srt_path)
    if not os.path.isfile(srt_path):
        raise FileNotFoundError(f"SRT file not found: {srt_path}")
    return srt_path

def detect_moments(video_path: str, clip_duration: float = 30.0):
    """Simple fixed-interval moments detection."""
    from moviepy.editor import VideoFileClip
    try:
        with VideoFileClip(video_path) as video:
            total_duration = video.duration
        logger.info(f"Video duration: {total_duration:.2f} seconds")
    except Exception as e:
        logger.error(f"Error reading video duration: {e}")
        raise

    moments = []
    start = 0.0
    while start < total_duration:
        end = min(start + clip_duration, total_duration)
        # Only add moments with reasonable duration (at least 5 seconds)
        if end - start >= 5.0:
            moments.append({"start": start, "end": end})
        start = end

    logger.info(f"Detected {len(moments)} moments")
    return moments

@shared_task(bind=True, max_retries=3)
def process_video_request(self, video_request_id):
    video_request = VideoRequest.objects.get(id=video_request_id)
    video_request.status = "processing"
    video_request.save()

    video_path = None
    try:
        logger.info(f"Starting processing video request {video_request_id}")

        # 1. Download video
        video_path = download_video(video_request.url)
        logger.info(f"Downloaded video to {video_path}")

        # Check if downloaded video has audio
        if not check_audio(video_path):
            logger.warning(f"Downloaded video has no audio: {video_path}")
            # Continue processing but log the issue

        # 2. Transcribe video
        logger.info(f"Starting transcription for {video_request_id}")
        transcript = transcribe_with_whisper(video_path)
        video_request.original_language = "en"  # Update if auto-detection is implemented
        video_request.save()
        logger.info(f"Transcription completed for {video_request_id}. Found {len(transcript)} segments")

        # 3. Detect moments
        moments = detect_moments(video_path, clip_duration=30)
        clips_created = 0
        total_moments = len(moments)

        if not moments:
            raise ValueError("No valid moments detected in video")

        # 4. Create clips
        for idx, moment in enumerate(moments):
            logger.info(f"Processing clip {idx + 1}/{total_moments} ({moment['start']:.1f}s - {moment['end']:.1f}s)")

            # Create unique filenames to avoid conflicts
            clip_filename = f"clip_{video_request_id}_{idx:03d}.mp4"
            srt_filename = f"clip_{video_request_id}_{idx:03d}.srt"

            output_path = os.path.join(tempfile.gettempdir(), clip_filename)
            srt_path = os.path.join(tempfile.gettempdir(), srt_filename)

            try:
                # Filter segments for this clip
                clip_segments = []
                for seg in transcript:
                    # Check if segment overlaps with this moment
                    if seg["start"] < moment["end"] and seg["end"] > moment["start"]:
                        # Adjust timing relative to clip start
                        adjusted_start = max(0, seg["start"] - moment["start"])
                        adjusted_end = min(moment["end"] - moment["start"], seg["end"] - moment["start"])

                        # Only add if the segment has positive duration
                        if adjusted_end > adjusted_start:
                            clip_segments.append({
                                "start": adjusted_start,
                                "end": adjusted_end,
                                "text": seg["text"]
                            })

                logger.info(f"Found {len(clip_segments)} subtitle segments for clip {idx + 1}")

                # Write SRT (only if there are segments)
                srt_file_path = None
                if clip_segments:
                    srt_file_path = write_clip_srt(clip_segments, srt_path)
                    if srt_file_path:
                        logger.info(f"Created SRT file: {srt_file_path}")

                # Create video clip with proper error handling
                logger.info(f"Creating video clip: {output_path}")
                create_clip(video_path, moment["start"], moment["end"], output_path, subtitles_srt=srt_file_path)

                # Verify the clip was created and has audio
                if not os.path.exists(output_path):
                    raise FileNotFoundError(f"Output clip not created: {output_path}")

                # Check if the created clip has audio
                if not check_audio(output_path):
                    logger.warning(f"Created clip has no audio: {output_path}")

                # Save clip in Django storage
                with open(output_path, "rb") as f:
                    clip_instance = Clip.objects.create(
                        video_request=video_request,
                        start_time=moment["start"],
                        end_time=moment["end"],
                        duration=moment["end"] - moment["start"],
                        status="done",
                    )
                    clip_instance.file_path.save(clip_filename, ContentFile(f.read()))

                logger.info(f"✓ Successfully created and saved clip {idx + 1}/{total_moments}")
                clips_created += 1

            except Exception as clip_error:
                logger.error(f"Failed to create clip {idx + 1}: {clip_error}")
                # Continue with next clip instead of failing completely
                continue

            finally:
                # Cleanup temporary files
                for temp_file in [output_path, srt_path]:
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except Exception as cleanup_error:
                            logger.warning(f"Could not remove temp file {temp_file}: {cleanup_error}")

        # Update video request status
        video_request.total_clips = clips_created
        if clips_created > 0:
            video_request.status = "done"
            logger.info(f"✓ Successfully processed video request {video_request_id}. Created {clips_created}/{total_moments} clips")
        else:
            video_request.status = "failed"
            logger.error(f"✗ Failed to create any clips for video request {video_request_id}")
        video_request.save()

    except (RateLimitError, APIError) as e:
        logger.warning(f"API error for video request {video_request_id}: {str(e)}. Retrying...")
        video_request.status = "pending"
        video_request.save()
        raise self.retry(exc=e, countdown=min(60, 2 ** self.request.retries))

    except BadRequestError as e:
        logger.error(f"Bad request error for video request {video_request_id}: {str(e)}")
        video_request.status = "failed"
        video_request.save()
        raise

    except Exception as e:
        logger.exception(f"Unexpected error for video request {video_request_id}: {str(e)}")
        video_request.status = "failed"
        video_request.save()
        try:
            raise self.retry(exc=e, countdown=10)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for video request {video_request_id}")
            video_request.status = "failed"
            video_request.save()

    finally:
        # Always cleanup the original video file
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
                logger.info(f"Cleaned up original video: {video_path}")
            except Exception as cleanup_error:
                logger.warning(f"Could not remove original video {video_path}: {cleanup_error}")