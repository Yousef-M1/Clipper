"""
Celery tasks for AI influencer video generation
"""
import os
import logging
import asyncio
import tempfile
from datetime import datetime
from typing import Optional
from celery import shared_task
from django.utils import timezone
from django.core.files import File
from django.core.files.base import ContentFile

from .models import AvatarProject, ProcessingLog
from .tts_service import TTSService

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_avatar_project(self, project_id: int):
    """
    Main task to process an AI influencer video project
    """
    try:
        # Get the project
        project = AvatarProject.objects.get(id=project_id)
        project.status = 'processing'
        project.progress_percentage = 0
        project.save()

        logger.info(f"Starting avatar project processing: {project.title}")

        # Log processing start
        ProcessingLog.objects.create(
            project=project,
            step='project_start',
            status='started',
            message=f"Starting processing for project: {project.title}"
        )

        # Step 1: Generate audio from script
        self.update_state(state='PROGRESS', meta={'current': 1, 'total': 4, 'status': 'Generating speech audio...'})
        project.progress_percentage = 25
        project.save()

        audio_path = _generate_audio_sync(project)

        # Step 2: Prepare avatar image
        self.update_state(state='PROGRESS', meta={'current': 2, 'total': 4, 'status': 'Preparing avatar image...'})
        project.progress_percentage = 50
        project.save()

        avatar_image_path = _prepare_avatar_image(project)

        # Step 3: Generate avatar video
        self.update_state(state='PROGRESS', meta={'current': 3, 'total': 4, 'status': 'Generating avatar video...'})
        project.progress_percentage = 75
        project.save()

        video_path = _generate_avatar_video_sync(project, avatar_image_path, audio_path)

        # Step 4: Finalize and save
        self.update_state(state='PROGRESS', meta={'current': 4, 'total': 4, 'status': 'Finalizing video...'})

        _finalize_project(project, video_path, audio_path)

        project.status = 'completed'
        project.progress_percentage = 100
        project.completed_at = timezone.now()
        project.save()

        # Log completion
        ProcessingLog.objects.create(
            project=project,
            step='project_complete',
            status='completed',
            message=f"Project completed successfully"
        )

        logger.info(f"Avatar project completed: {project.title}")
        return {
            'status': 'completed',
            'project_id': project_id,
            'video_url': project.final_video.url if project.final_video else None
        }

    except Exception as e:
        logger.error(f"Avatar project processing failed: {e}")

        # Update project status
        project = AvatarProject.objects.get(id=project_id)
        project.status = 'failed'
        project.error_message = str(e)
        project.save()

        # Log error
        ProcessingLog.objects.create(
            project=project,
            step='project_error',
            status='failed',
            message=f"Processing failed: {e}"
        )

        raise


def _generate_audio_sync(project: AvatarProject) -> str:
    """
    Generate audio from script (synchronous wrapper for async TTS)
    """
    try:
        start_time = datetime.now()

        ProcessingLog.objects.create(
            project=project,
            step='audio_generation',
            status='started',
            message=f"Generating audio with {project.voice.engine} engine"
        )

        # Run async TTS generation
        audio_path = asyncio.run(_generate_audio_async(project))

        processing_time = (datetime.now() - start_time).total_seconds()

        ProcessingLog.objects.create(
            project=project,
            step='audio_generation',
            status='completed',
            message=f"Audio generated successfully",
            processing_time=processing_time
        )

        return audio_path

    except Exception as e:
        ProcessingLog.objects.create(
            project=project,
            step='audio_generation',
            status='failed',
            message=f"Audio generation failed: {e}"
        )
        raise


async def _generate_audio_async(project: AvatarProject) -> str:
    """
    Generate audio from script using TTS service
    """
    tts_service = TTSService()

    # Create temporary file for audio
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        output_path = tmp.name

    # Generate speech
    audio_path = await tts_service.generate_speech(
        text=project.script,
        voice_id=project.voice.voice_id,
        engine=project.voice.engine,
        speed=project.voice_speed,
        pitch=project.voice_pitch,
        output_path=output_path
    )

    return audio_path


def _prepare_avatar_image(project: AvatarProject) -> str:
    """
    Prepare avatar image file for processing
    """
    try:
        ProcessingLog.objects.create(
            project=project,
            step='image_preparation',
            status='started',
            message="Preparing avatar image"
        )

        # Get avatar image path
        if project.custom_avatar_image:
            avatar_path = project.custom_avatar_image.path
        elif project.character and project.character.avatar_image:
            avatar_path = project.character.avatar_image.path
        else:
            raise ValueError("No avatar image available")

        ProcessingLog.objects.create(
            project=project,
            step='image_preparation',
            status='completed',
            message=f"Avatar image prepared: {avatar_path}"
        )

        return avatar_path

    except Exception as e:
        ProcessingLog.objects.create(
            project=project,
            step='image_preparation',
            status='failed',
            message=f"Image preparation failed: {e}"
        )
        raise


def _generate_avatar_video_sync(project: AvatarProject, avatar_image_path: str, audio_path: str) -> str:
    """
    Generate avatar video (synchronous wrapper for async avatar generation)
    """
    try:
        start_time = datetime.now()

        ProcessingLog.objects.create(
            project=project,
            step='video_generation',
            status='started',
            message=f"Generating video with {project.lip_sync_model} model"
        )

        # Run async avatar generation
        video_path = asyncio.run(_generate_avatar_video_async(
            project, avatar_image_path, audio_path
        ))

        processing_time = (datetime.now() - start_time).total_seconds()

        ProcessingLog.objects.create(
            project=project,
            step='video_generation',
            status='completed',
            message="Avatar video generated successfully",
            processing_time=processing_time
        )

        return video_path

    except Exception as e:
        ProcessingLog.objects.create(
            project=project,
            step='video_generation',
            status='failed',
            message=f"Video generation failed: {e}"
        )
        raise


async def _generate_avatar_video_async(
    project: AvatarProject,
    avatar_image_path: str,
    audio_path: str
) -> str:
    """
    Generate avatar video using avatar service
    """
    avatar_service = AvatarGenerationService()

    # Validate inputs
    is_valid, message = avatar_service.validate_inputs(
        avatar_image_path, audio_path, project.lip_sync_model
    )
    if not is_valid:
        raise ValueError(f"Input validation failed: {message}")

    # Create temporary file for video
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
        output_path = tmp.name

    # Generate avatar video
    video_path = await avatar_service.generate_avatar_video(
        avatar_image_path=avatar_image_path,
        audio_path=audio_path,
        model=project.lip_sync_model,
        quality=project.video_quality,
        aspect_ratio=project.aspect_ratio,
        background_color=project.background_color,
        background_image_path=project.background_image.path if project.background_image else None,
        head_movement_intensity=project.head_movement_intensity,
        enable_emotions=project.enable_emotions,
        output_path=output_path
    )

    return video_path


def _finalize_project(project: AvatarProject, video_path: str, audio_path: str):
    """
    Finalize project by saving files and metadata
    """
    try:
        ProcessingLog.objects.create(
            project=project,
            step='finalization',
            status='started',
            message="Finalizing project files"
        )

        # Save generated audio file
        with open(audio_path, 'rb') as audio_file:
            project.generated_audio.save(
                f"{project.id}_audio.wav",
                File(audio_file),
                save=False
            )

        # Save final video file
        with open(video_path, 'rb') as video_file:
            project.final_video.save(
                f"{project.id}_video.mp4",
                File(video_file),
                save=False
            )

        # Calculate metadata
        video_size = os.path.getsize(video_path)
        project.file_size_mb = video_size / (1024 * 1024)

        # Get video duration using ffprobe
        try:
            import subprocess
            duration_cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(duration_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                project.video_duration = float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Could not get video duration: {e}")

        # Generate thumbnail
        _generate_thumbnail(project, video_path)

        project.save()

        # Clean up temporary files
        try:
            os.unlink(audio_path)
            os.unlink(video_path)
        except Exception as e:
            logger.warning(f"Could not clean up temp files: {e}")

        ProcessingLog.objects.create(
            project=project,
            step='finalization',
            status='completed',
            message="Project finalized successfully"
        )

    except Exception as e:
        ProcessingLog.objects.create(
            project=project,
            step='finalization',
            status='failed',
            message=f"Finalization failed: {e}"
        )
        raise


def _generate_thumbnail(project: AvatarProject, video_path: str):
    """
    Generate thumbnail from video
    """
    try:
        import subprocess

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            thumbnail_path = tmp.name

        # Extract frame at 1 second
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', '1',
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            thumbnail_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as thumb_file:
                project.thumbnail.save(
                    f"{project.id}_thumb.jpg",
                    File(thumb_file),
                    save=False
                )

            os.unlink(thumbnail_path)

    except Exception as e:
        logger.warning(f"Thumbnail generation failed: {e}")


@shared_task
def cleanup_failed_projects():
    """
    Cleanup task to remove temporary files from failed projects
    """
    try:
        failed_projects = AvatarProject.objects.filter(status='failed')
        cleaned_count = 0

        for project in failed_projects:
            # Remove temporary files if they exist
            if project.generated_audio:
                try:
                    project.generated_audio.delete()
                except:
                    pass

            if project.final_video:
                try:
                    project.final_video.delete()
                except:
                    pass

            if project.thumbnail:
                try:
                    project.thumbnail.delete()
                except:
                    pass

            cleaned_count += 1

        logger.info(f"Cleaned up {cleaned_count} failed projects")
        return {'cleaned_projects': cleaned_count}

    except Exception as e:
        logger.error(f"Failed project cleanup error: {e}")
        raise