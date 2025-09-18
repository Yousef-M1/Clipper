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
from ..advanced_captions import AdvancedCaptionStyleManager, create_advanced_subtitles
from ..simple_captions import create_simple_visible_subtitles, write_per_word_full_line_srt
from ..video_quality import VideoQualityManager, create_quality_controlled_clip

logger = logging.getLogger(__name__)

def write_enhanced_clip_srt(segments, srt_path, style='modern_purple', enable_word_highlighting=True,
                           advanced_mode=False, max_words_per_screen=2, output_format='horizontal'):
    """Enhanced SRT creation with advanced styling and organized word display."""
    # Clamp negative times and filter out invalid segments
    valid_segments = []
    for seg in segments:
        start = max(0, seg["start"])
        end = max(0, seg["end"])
        if end > start and seg["text"].strip():
            # Copy word-level data if available
            segment_data = {
                "start": start,
                "end": end,
                "text": seg["text"].strip()
            }
            if "words" in seg:
                segment_data["words"] = seg["words"]
            valid_segments.append(segment_data)

    if not valid_segments:
        logger.warning(f"No valid segments for SRT file: {srt_path}")
        return None

    try:
        # Check if this is an advanced style that should use the advanced caption system
        advanced_styles = ['elevate_style', 'slide_in_modern', 'word_pop', 'two_word_flow', 'impactful_highlight']

        if advanced_mode and style in advanced_styles:
            logger.info(f"Creating advanced subtitles with {style}")
            return create_advanced_subtitles(
                valid_segments,
                srt_path,
                style_name=style,
                max_words=max_words_per_screen,
                enable_effects=True
            )
        # Use per-word highlighting for styles with word highlighting enabled
        elif enable_word_highlighting and style in ['modern_purple', 'tiktok_style']:
            if style == 'modern_purple':
                logger.info(f"Creating per-word SRT subtitles with purple highlighting")
                active_color = "#8B5CF6"  # purple
            elif style == 'tiktok_style':
                logger.info(f"Creating per-word SRT subtitles with red/pink highlighting")
                active_color = "#FF6B6B"  # red/pink for TikTok

            return write_per_word_full_line_srt(
                valid_segments,
                srt_path,
                active_color=active_color,
                inactive_color="#FFFFFF"  # white
            )
        else:
            # Use simple, reliable captions for other styles
            logger.info(f"Creating simple, visible subtitles with max words: {max_words_per_screen}")
            return create_simple_visible_subtitles(
                valid_segments,
                srt_path,
                max_words=max_words_per_screen,
                style=style,
                output_format=output_format
            )

    except Exception as e:
        logger.error(f"Simple subtitles failed ({e}), using basic fallback")
        # Fallback to basic SRT
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
            return detect_moments_fixed(video_path, clip_duration, max_clips)
    else:
        logger.info("Using fixed interval moment detection")
        return detect_moments_fixed(video_path, clip_duration, max_clips)

def detect_moments_fixed(video_path: str, clip_duration: float = 30.0, max_clips: int = 10):
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
    while start < total_duration and len(moments) < max_clips:
        end = min(start + clip_duration, total_duration)
        if end - start >= 5.0:
            moments.append({"start": start, "end": end})
        start = end

    logger.info(f"Detected {len(moments)} fixed moments (limited to {max_clips})")
    return moments

@shared_task(bind=True, max_retries=3)
def process_video_request(self, video_request_id, processing_settings=None):
    """Enhanced video processing with AI moments, styled captions, and quality control."""

    video_request = VideoRequest.objects.get(id=video_request_id)

    # Get processing settings from video request, or use defaults
    if processing_settings is None and video_request.processing_settings:
        processing_settings = video_request.processing_settings
    elif processing_settings is None:
        processing_settings = {
            'moment_detection_type': 'ai_powered',  # 'ai_powered' or 'fixed_intervals'
            'clip_duration': 30.0,
            'max_clips': 10,
            'video_quality': '720p',  # '480p', '720p', '1080p', '1440p', '2160p'
            'compression_level': 'balanced',  # 'high_quality', 'balanced', 'compressed'
            'caption_style': 'modern_purple',  # 'modern_purple', 'tiktok_style', 'youtube_style', etc.
            'enable_word_highlighting': True,
            # NEW FORMAT OPTIONS
            'output_format': 'horizontal',  # 'horizontal', 'vertical', 'square', 'custom'
            'social_platform': 'youtube',  # 'youtube', 'tiktok', 'instagram_story', etc.
            'custom_width': None,
            'custom_height': None,
        }
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
                logger.info(f"DEBUG: Filtering transcript for clip {moment['start']:.1f}-{moment['end']:.1f}s")

                for seg in transcript:
                    logger.info(f"  Checking segment {seg['start']:.1f}-{seg['end']:.1f}s: '{seg['text'][:50]}...'")
                    if seg["start"] < moment["end"] and seg["end"] > moment["start"]:
                        adjusted_start = max(0, seg["start"] - moment["start"])
                        adjusted_end = min(moment["end"] - moment["start"], seg["end"] - moment["start"])

                        if adjusted_end > adjusted_start:
                            clip_segment = {
                                "start": adjusted_start,
                                "end": adjusted_end,
                                "text": seg["text"]
                            }
                            # CRITICAL: Copy and adjust word-level timestamps for clip timing
                            if "words" in seg:
                                adjusted_words = []
                                for word in seg["words"]:
                                    # Adjust word timestamps relative to clip start
                                    word_start = max(0, word["start"] - moment["start"])
                                    word_end = max(0, word["end"] - moment["start"])

                                    # Only include words that fall within the clip duration
                                    if word_start < (moment["end"] - moment["start"]):
                                        adjusted_words.append({
                                            "start": word_start,
                                            "end": word_end,
                                            "word": word["word"]
                                        })
                                clip_segment["words"] = adjusted_words
                            clip_segments.append(clip_segment)

                logger.info(f"Found {len(clip_segments)} subtitle segments for clip {idx + 1}")

                # Create enhanced SRT with styling
                srt_file_path = None
                if clip_segments:
                    srt_file_path = write_enhanced_clip_srt(
                        clip_segments,
                        srt_path,
                        style=processing_settings['caption_style'],
                        enable_word_highlighting=processing_settings['enable_word_highlighting'],
                        advanced_mode=processing_settings.get('advanced_captions', True),
                        max_words_per_screen=processing_settings.get('max_words_per_screen', 2),
                        output_format=processing_settings.get('output_format', 'horizontal')
                    )
                    if srt_file_path:
                        logger.info(f"Created styled SRT file: {srt_file_path}")

                # Create video clip with quality control and format options
                logger.info(f"Creating quality-controlled video clip: {output_path}")

                create_quality_controlled_clip(
                    video_path,
                    moment["start"],
                    moment["end"],
                    output_path,
                    quality=processing_settings['video_quality'],
                    compression=processing_settings['compression_level'],
                    subtitles_srt=srt_file_path,
                    output_format=processing_settings.get('output_format', 'horizontal'),
                    custom_width=processing_settings.get('custom_width'),
                    custom_height=processing_settings.get('custom_height')
                )

                # Verify clip creation
                if not os.path.exists(output_path):
                    raise FileNotFoundError(f"Output clip not created: {output_path}")

                # Check audio in created clip
                if not check_audio(output_path):
                    logger.warning(f"Created clip has no audio: {output_path}")

                # BACKGROUND MUSIC MIXING
                if video_request.background_music:
                    try:
                        from ..audio_mixing import AudioMixer

                        logger.info(f"Adding background music: {video_request.background_music.name}")

                        # Create temporary output path for mixed audio
                        mixed_output_path = output_path.replace('.mp4', '_mixed.mp4')

                        mixer = AudioMixer()
                        mixer.mix_background_music(
                            video_path=output_path,
                            output_path=mixed_output_path,
                            background_music=video_request.background_music,
                            music_volume=video_request.music_volume,
                            original_volume=video_request.original_audio_volume,
                            enable_ducking=video_request.enable_audio_ducking,
                            fade_in=video_request.music_fade_in,
                            fade_out=video_request.music_fade_out
                        )

                        # Replace original clip with mixed version
                        if os.path.exists(mixed_output_path):
                            os.replace(mixed_output_path, output_path)
                            logger.info(f"Successfully mixed background music into clip")

                    except Exception as music_error:
                        logger.error(f"Background music mixing failed: {music_error}")
                        # Continue processing without background music

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
                        video_quality=processing_settings['video_quality'],
                        compression_level=processing_settings['compression_level'],
                        used_caption_style=processing_settings['caption_style'],
                        has_word_highlighting=processing_settings['enable_word_highlighting'],
                        caption_style=processing_settings,
                        file_size_mb=estimated_size_mb,
                        detection_method="fixed_interval" if processing_settings['moment_detection_type'] == 'fixed_intervals' else "ai_powered",
                        engagement_score=5.0,
                        format="mp4"
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

            # SOCIAL MEDIA AUTO-POSTING INTEGRATION
            try:
                from core.social_integration import trigger_social_posting_for_video_request

                if video_request.auto_post_to_social:
                    logger.info(f"🚀 Starting social media auto-posting for video request {video_request_id}")
                    social_result = trigger_social_posting_for_video_request(video_request_id)

                    if social_result.get('success'):
                        logger.info(
                            f"✓ Social media posting completed: "
                            f"{social_result.get('clips_processed')} clips processed, "
                            f"{social_result.get('total_posts_created')} posts created ({social_result.get('schedule_type')})"
                        )
                    else:
                        logger.warning(f"⚠️ Social media posting failed: {social_result.get('reason')}")
                else:
                    logger.info("📱 Social media auto-posting disabled for this video request")

            except Exception as social_error:
                logger.error(f"❌ Error in social media integration: {social_error}")
                # Don't fail the entire job if social posting fails
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
        # NEW FORMAT OPTIONS
        'output_format': kwargs.get('output_format', 'horizontal'),
        'social_platform': kwargs.get('social_platform', 'youtube'),
        'custom_width': kwargs.get('custom_width'),
        'custom_height': kwargs.get('custom_height'),
    }

    return process_video_request(video_request_id, settings)