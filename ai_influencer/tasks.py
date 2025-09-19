"""
Simplified Celery tasks for TTS only
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
def process_tts_only(self, project_id: int):
    """
    Simple task to only generate TTS audio
    """
    try:
        # Get the project
        project = AvatarProject.objects.get(id=project_id)
        project.status = 'processing'
        project.progress_percentage = 0
        project.save()

        logger.info(f"Starting TTS generation: {project.title}")

        # Log processing start
        ProcessingLog.objects.create(
            project=project,
            step='tts_start',
            status='started',
            message=f"Starting TTS generation for: {project.title}"
        )

        # Generate audio from script
        self.update_state(state='PROGRESS', meta={'current': 1, 'total': 1, 'status': 'Generating speech audio...'})
        project.progress_percentage = 50
        project.save()

        audio_path = _generate_audio_sync(project)

        # Save audio file to project
        project.progress_percentage = 100
        project.save()

        # Save the audio file
        with open(audio_path, 'rb') as audio_file:
            project.final_video.save(
                f"{project.id}_audio.mp3",
                File(audio_file),
                save=True
            )

        project.status = 'completed'
        project.completed_at = timezone.now()
        project.save()

        # Log completion
        ProcessingLog.objects.create(
            project=project,
            step='tts_complete',
            status='completed',
            message=f"TTS generation completed successfully"
        )

        logger.info(f"TTS generation completed: {project.title}")
        return {
            'status': 'completed',
            'project_id': project_id,
            'audio_url': project.final_video.url if project.final_video else None
        }

    except Exception as e:
        logger.error(f"TTS generation failed: {e}")

        # Update project status
        project = AvatarProject.objects.get(id=project_id)
        project.status = 'failed'
        project.error_message = str(e)
        project.save()

        # Log error
        ProcessingLog.objects.create(
            project=project,
            step='tts_error',
            status='failed',
            message=f"TTS generation failed: {e}"
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
    Generate audio using TTS service
    """
    tts_service = TTSService()

    # Create temporary file for audio
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
        audio_path = tmp_file.name

    # Generate TTS audio
    result_path = await tts_service.generate_speech(
        text=project.script,
        voice_id=project.voice.voice_id,
        engine=project.voice.engine,
        output_path=audio_path
    )

    return result_path