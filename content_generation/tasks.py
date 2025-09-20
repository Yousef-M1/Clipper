from celery import shared_task
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging
import asyncio

from .models import ContentGenerationRequest, GeneratedContent, ContentTemplate
from .ai_content_service import AIContentGenerationService
from .complete_workflow import CompleteContentWorkflow

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_content_generation(self, content_request_id):
    """
    Process content generation request asynchronously

    This task handles the complete AI content generation pipeline:
    1. Fetch video content or transcript
    2. Generate content using AI
    3. Save results to database
    4. Update request status
    """
    try:
        content_request = ContentGenerationRequest.objects.get(id=content_request_id)

        # Update status to processing
        content_request.status = 'processing'
        content_request.started_at = timezone.now()
        content_request.save()

        logger.info(f"Starting content generation for request {content_request_id}")

        # Run sync content generation (we're already in a worker thread)
        result = _process_content_sync(content_request)

        if result['success']:
            # Update request with success
            content_request.status = 'completed'
            content_request.completed_at = timezone.now()
            content_request.processing_time_seconds = result.get('processing_time', 0)
            content_request.tokens_used = result.get('tokens_used', 0)
            content_request.cost_estimate = result.get('cost_estimate', 0.0)
            content_request.ai_model_used = 'gpt-4'
            content_request.save()

            logger.info(f"Content generation completed for request {content_request_id}")
        else:
            # Handle failure
            content_request.status = 'failed'
            content_request.error_message = result.get('error', 'Unknown error')
            content_request.save()

            logger.error(f"Content generation failed for request {content_request_id}: {result.get('error')}")

    except ContentGenerationRequest.DoesNotExist:
        logger.error(f"Content generation request {content_request_id} not found")

    except Exception as exc:
        logger.error(f"Content generation task failed: {str(exc)}")

        # Update request status
        try:
            content_request = ContentGenerationRequest.objects.get(id=content_request_id)
            content_request.status = 'failed'
            content_request.error_message = str(exc)
            content_request.save()
        except:
            pass

        # Retry the task
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying content generation task in {self.default_retry_delay} seconds")
            raise self.retry(countdown=self.default_retry_delay, exc=exc)
        else:
            logger.error(f"Content generation task failed after {self.max_retries} retries")


def _process_content_sync(content_request):
    """
    Synchronous content generation processing
    """
    try:
        start_time = timezone.now()

        # Initialize AI service
        ai_service = AIContentGenerationService()

        # Get transcript/content source
        transcript = ""
        video_title = ""
        video_duration = 0

        if content_request.video_request:
            # Extract REAL transcript from video processing subtitle files
            from .transcript_extractor import extract_real_transcript

            video_request = content_request.video_request

            # Get real transcript from subtitle files
            transcript_data = extract_real_transcript(video_request)

            transcript = transcript_data['transcript']
            video_title = transcript_data['title']
            video_duration = transcript_data['duration']

            logger.info(f"Extracted real transcript for video {video_request.id}: "
                       f"{transcript_data['clips_processed']} clips processed, "
                       f"source: {transcript_data['source']}")

        elif content_request.custom_text_input:
            # Use custom text input
            transcript = content_request.custom_text_input
            video_title = "Custom Content"

        else:
            return {
                'success': False,
                'error': 'No content source provided (video_request or custom_text_input)'
            }

        if not transcript:
            return {
                'success': False,
                'error': 'No transcript or content available for processing'
            }

        # Generate content based on template type
        template = content_request.template
        content_result = None

        if template.template_type == 'blog_post':
            content_result = asyncio.run(ai_service.generate_blog_post(
                transcript=transcript,
                video_title=video_title,
                target_keywords=content_request.custom_keywords or [],
                target_audience=content_request.target_audience,
                brand_voice=content_request.brand_voice,
                custom_instructions=content_request.custom_instructions,
                template=template
            ))

        elif template.template_type == 'show_notes':
            content_result = asyncio.run(ai_service.generate_show_notes(
                transcript=transcript,
                video_title=video_title,
                video_duration=video_duration,
                target_audience=content_request.target_audience,
                brand_voice=content_request.brand_voice,
                custom_instructions=content_request.custom_instructions,
                template=template
            ))

        elif template.template_type == 'social_media':
            content_result = asyncio.run(ai_service.generate_social_media_posts(
                transcript=transcript,
                video_title=video_title,
                target_keywords=content_request.custom_keywords or [],
                target_audience=content_request.target_audience,
                brand_voice=content_request.brand_voice,
                custom_instructions=content_request.custom_instructions,
                template=template
            ))

        elif template.template_type == 'email_newsletter':
            content_result = asyncio.run(ai_service.generate_email_newsletter(
                transcript=transcript,
                video_title=video_title,
                target_keywords=content_request.custom_keywords or [],
                target_audience=content_request.target_audience,
                brand_voice=content_request.brand_voice,
                custom_instructions=content_request.custom_instructions,
                template=template
            ))

        elif template.template_type == 'video_summary':
            content_result = asyncio.run(ai_service.generate_video_summary(
                transcript=transcript,
                video_title=video_title,
                video_duration=video_duration,
                target_audience=content_request.target_audience,
                brand_voice=content_request.brand_voice,
                custom_instructions=content_request.custom_instructions,
                template=template
            ))

        else:
            # Generic content generation using template
            content_result = asyncio.run(ai_service.generate_custom_content(
                transcript=transcript,
                video_title=video_title,
                template=template,
                custom_variables={
                    'target_keywords': content_request.custom_keywords or [],
                    'target_audience': content_request.target_audience,
                    'brand_voice': content_request.brand_voice,
                    'custom_instructions': content_request.custom_instructions,
                    'video_duration': video_duration
                }
            ))

        if not content_result or not content_result.get('success'):
            return {
                'success': False,
                'error': content_result.get('error', 'Content generation failed') if content_result else 'No content generated'
            }

        # Save generated content to database
        with transaction.atomic():
            generated_content = GeneratedContent.objects.create(
                content_request=content_request,
                user=content_request.user,
                title=content_result.get('title', video_title),
                content=content_result.get('content', ''),
                format=content_result.get('format', 'markdown'),
                meta_title=content_result.get('meta_title', ''),
                meta_description=content_result.get('meta_description', ''),
                keywords=content_result.get('keywords', []),
                hashtags=content_result.get('hashtags', []),
                ai_confidence_score=content_result.get('confidence_score', 0.0)
            )

        # Calculate processing time
        end_time = timezone.now()
        processing_time = (end_time - start_time).total_seconds()

        return {
            'success': True,
            'generated_content_id': generated_content.id,
            'processing_time': processing_time,
            'tokens_used': content_result.get('tokens_used', 0),
            'cost_estimate': content_result.get('cost_estimate', 0.0),
            'word_count': generated_content.word_count,
            'content_preview': content_result.get('content', '')[:200] + '...' if content_result.get('content', '') else ''
        }

    except Exception as e:
        logger.error(f"Async content generation failed: {str(e)}")
        return {
            'success': False,
            'error': f"Content generation error: {str(e)}"
        }


@shared_task
def cleanup_old_content_requests():
    """
    Cleanup old content generation requests and failed processing
    Run this task periodically (e.g., daily)
    """
    try:
        from datetime import timedelta

        # Delete failed requests older than 7 days
        old_failed = ContentGenerationRequest.objects.filter(
            status='failed',
            created_at__lt=timezone.now() - timedelta(days=7)
        )
        failed_count = old_failed.count()
        old_failed.delete()

        # Reset stuck processing requests older than 1 hour
        stuck_processing = ContentGenerationRequest.objects.filter(
            status='processing',
            processing_started_at__lt=timezone.now() - timedelta(hours=1)
        )
        stuck_count = stuck_processing.count()
        stuck_processing.update(
            status='failed',
            error_message='Processing timeout - request was stuck'
        )

        logger.info(f"Cleanup completed: {failed_count} failed requests deleted, {stuck_count} stuck requests reset")

        return {
            'success': True,
            'failed_deleted': failed_count,
            'stuck_reset': stuck_count
        }

    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def batch_content_generation(content_request_ids):
    """
    Process multiple content generation requests in batch
    Useful for bulk operations
    """
    results = []

    for request_id in content_request_ids:
        try:
            # Process each request
            result = process_content_generation.delay(request_id)
            results.append({
                'request_id': request_id,
                'task_id': result.id,
                'status': 'queued'
            })
        except Exception as e:
            results.append({
                'request_id': request_id,
                'task_id': None,
                'status': 'failed',
                'error': str(e)
            })

    return {
        'success': True,
        'batch_size': len(content_request_ids),
        'results': results
    }