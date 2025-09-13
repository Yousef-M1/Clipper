from celery import shared_task
from core.models import VideoRequest, Clip
from clipper.utils import download_video, transcribe_with_whisper, create_clip, write_srt, check_audio
import tempfile
import os
from django.core.files.base import ContentFile
from openai import RateLimitError, APIError, BadRequestError
import logging

# Import the new modules we created
from ..ai_moments import detect_ai_moments
from ..caption_styles import CaptionStyleManager, create_styled_subtitles
from ..video_quality import VideoQualityManager, create_quality_controlled_clip

logger = logging.getLogger(__name__)

def write_enhanced_clip_srt(segments, srt_path, style='modern_purple', enable_word_highlighting=True):
    """Enhanced SRT creation with styling and word highlighting."""
    # Clamp negative times and filter out invalid segments
    valid_segments = []
    for seg in segments:
        start = max(0, seg["start"])
        end = max(0, seg["end"])
        if end > start and seg["text"].strip():
            valid_segments.append({
                "start": start,
                "end": end,
                "text": seg["text"].strip()
            })

    if not valid_segments:
        logger.warning(f"No valid segments for SRT file: {srt_path}")
        return None

    if enable_word_highlighting:
        # Create styled subtitles with word highlighting
        style_manager = CaptionStyleManager(style)
        style_manager.create_word_level_srt(valid_segments, srt_path)
    else:
        # Create regular subtitles
        write_srt(valid_segments, srt_path)

    if not os.path.isfile(srt_path):
        raise FileNotFoundError(f"SRT file not found: {srt_path}")
    return srt_path

def detect_moments_enhanced(video_path: str, transcript, settings: dict):
    """Enhanced moment detection with AI or fixed intervals."""
    detection_type = settings.get('moment_detection_type', 'fixed_intervals')
    clip_duration = settings.get('clip_duration', 30.0)
    max_clips = settings.get('max_clips', 10)

    if detection_type == 'ai_powered':
        try:
            logger.info("Using AI-powered moment detection")
            return detect_ai_moments(video_path, transcript, clip_duration, max_clips)
        except Exception as e:
            logger.warning(f"AI moment detection failed, falling back to fixed intervals: {e}")
            return detect_moments_fixed(video_path, clip_duration)
    else:
        logger.info("Using fixed interval moment detection")
        return detect_moments_fixed(video_path, clip_duration)

def detect_moments_fixed(video_path: str, clip_duration: float = 30.0):
    """Original fixed-interval moments detection."""
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
        if end - start >= 5.0:
            moments.append({"start": start, "end": end})
        start = end

    logger.info(f"Detected {len(moments)} fixed moments")
    return moments

@shared_task(bind=True, max_retries=3)
def process_video_request(self, video_request_id, processing_settings=None):
    """Enhanced video processing with AI moments, styled captions, and quality control."""

    # Default processing settings
    if processing_settings is None:
        processing_settings = {
            'moment_detection_type': 'ai_powered',  # 'ai_powered' or 'fixed_intervals'
            'clip_duration': 30.0,
            'max_clips': 10,
            'video_quality': '720p',  # '480p', '720p', '1080p', '1440p', '2160p'
            'compression_level': 'balanced',  # 'high_quality', 'balanced', 'compressed'
            'caption_style': 'modern_purple',  # 'modern_purple', 'tiktok_style', 'youtube_style', etc.
            'enable_word_highlighting': True,
        }

    video_request = VideoRequest.objects.get(id=video_request_id)
    video_request.status = "processing"
    video_request.save()

    video_path = None
    try:
        logger.info(f"Starting enhanced processing for video request {video_request_id}")
        logger.info(f"Settings: {processing_settings}")

        # 1. Download video
        video_path = download_video(video_request.url)
        logger.info(f"Downloaded video to {video_path}")

        # Check if downloaded video has audio
        if not check_audio(video_path):
            logger.warning(f"Downloaded video has no audio: {video_path}")

        # 2. Transcribe video with Whisper
        logger.info(f"Starting transcription for {video_request_id}")
        transcript = transcribe_with_whisper(video_path)
        video_request.original_language = "en"
        video_request.save()
        logger.info(f"Transcription completed. Found {len(transcript)} segments")

        # 3. Enhanced moment detection
        moments = detect_moments_enhanced(video_path, transcript, processing_settings)
        clips_created = 0
        total_moments = len(moments)

        if not moments:
            raise ValueError("No valid moments detected in video")

        # Initialize quality manager
        quality_manager = VideoQualityManager(
            processing_settings['video_quality'],
            processing_settings['compression_level']
        )

        logger.info(f"Quality settings: {quality_manager.get_quality_info()}")

        # 4. Create enhanced clips
        for idx, moment in enumerate(moments):
            logger.info(f"Processing clip {idx + 1}/{total_moments} ({moment['start']:.1f}s - {moment['end']:.1f}s)")

            # Create unique filenames
            clip_filename = f"clip_{video_request_id}_{idx:03d}.mp4"
            srt_filename = f"clip_{video_request_id}_{idx:03d}.srt"

            output_path = os.path.join(tempfile.gettempdir(), clip_filename)
            srt_path = os.path.join(tempfile.gettempdir(), srt_filename)

            try:
                # Filter segments for this clip
                clip_segments = []
                for seg in transcript:
                    if seg["start"] < moment["end"] and seg["end"] > moment["start"]:
                        adjusted_start = max(0, seg["start"] - moment["start"])
                        adjusted_end = min(moment["end"] - moment["start"], seg["end"] - moment["start"])

                        if adjusted_end > adjusted_start:
                            clip_segments.append({
                                "start": adjusted_start,
                                "end": adjusted_end,
                                "text": seg["text"]
                            })

                logger.info(f"Found {len(clip_segments)} subtitle segments for clip {idx + 1}")

                # Create enhanced SRT with styling
                srt_file_path = None
                if clip_segments:
                    srt_file_path = write_enhanced_clip_srt(
                        clip_segments,
                        srt_path,
                        style=processing_settings['caption_style'],
                        enable_word_highlighting=processing_settings['enable_word_highlighting']
                    )
                    if srt_file_path:
                        logger.info(f"Created styled SRT file: {srt_file_path}")

                # Create video clip with quality control
                logger.info(f"Creating quality-controlled video clip: {output_path}")

                create_quality_controlled_clip(
                    video_path,
                    moment["start"],
                    moment["end"],
                    output_path,
                    quality=processing_settings['video_quality'],
                    compression=processing_settings['compression_level'],
                    subtitles_srt=srt_file_path
                )

                # Verify clip creation
                if not os.path.exists(output_path):
                    raise FileNotFoundError(f"Output clip not created: {output_path}")

                # Check audio in created clip
                if not check_audio(output_path):
                    logger.warning(f"Created clip has no audio: {output_path}")

                # Estimate file size
                duration = moment["end"] - moment["start"]
                estimated_size_mb, size_str = quality_manager.estimate_file_size(duration)

                # Save clip in Django storage
                with open(output_path, "rb") as f:
                    clip_instance = Clip.objects.create(
                        video_request=video_request,
                        start_time=moment["start"],
                        end_time=moment["end"],
                        duration=duration,
                        status="done",
                        # Add metadata fields if available in your model
                        # quality_preset=processing_settings['video_quality'],
                        # caption_style=processing_settings['caption_style'],
                        # file_size_mb=estimated_size_mb
                    )
                    clip_instance.file_path.save(clip_filename, ContentFile(f.read()))

                logger.info(f"✓ Successfully created clip {idx + 1}/{total_moments} ({size_str})")
                clips_created += 1

            except Exception as clip_error:
                logger.error(f"Failed to create clip {idx + 1}: {clip_error}")
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
            logger.info(f"✓ Enhanced processing completed for {video_request_id}. Created {clips_created}/{total_moments} clips")
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

# Helper task for testing different settings
@shared_task
def process_video_with_custom_settings(video_request_id, **kwargs):
    """Process video with custom settings"""
    settings = {
        'moment_detection_type': kwargs.get('moment_detection_type', 'ai_powered'),
        'clip_duration': kwargs.get('clip_duration', 30.0),
        'max_clips': kwargs.get('max_clips', 10),
        'video_quality': kwargs.get('video_quality', '720p'),
        'compression_level': kwargs.get('compression_level', 'balanced'),
        'caption_style': kwargs.get('caption_style', 'modern_purple'),
        'enable_word_highlighting': kwargs.get('enable_word_highlighting', True),
    }

    return process_video_request(video_request_id, settings)