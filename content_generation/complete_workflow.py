"""
Complete YouTube → AI Content Generation Workflow
Demonstrates the full pipeline from video URL to generated content
"""

import asyncio
import logging
from typing import Dict, Optional
from django.utils import timezone

from core.models import VideoRequest, User
from content_generation.models import ContentTemplate, ContentGenerationRequest, GeneratedContent
from content_generation.ai_content_service import AIContentGenerationService
from clipper.utils import download_video, transcribe_with_whisper

logger = logging.getLogger(__name__)


class CompleteContentWorkflow:
    """
    Complete workflow from YouTube URL to generated content
    """

    def __init__(self):
        self.ai_service = AIContentGenerationService()

    async def process_youtube_to_content(
        self,
        youtube_url: str,
        user: User,
        content_type: str = 'blog_post',
        target_keywords: list = None,
        target_audience: str = '',
        brand_voice: str = 'professional',
        custom_instructions: str = ''
    ) -> Dict:
        """
        Complete workflow: YouTube URL → AI Generated Content

        Args:
            youtube_url: YouTube video URL
            user: Django user instance
            content_type: Type of content to generate
            target_keywords: SEO keywords
            target_audience: Target audience description
            brand_voice: Brand voice style
            custom_instructions: Additional user instructions

        Returns:
            Dict with generated content and metadata
        """

        try:
            # Step 1: Create video request
            video_request = await self._create_video_request(youtube_url, user)

            # Step 2: Download and process video
            video_data = await self._process_video(video_request)

            # Step 3: Get transcript
            transcript = await self._get_transcript(video_data)

            # Step 4: Get content template
            template = await self._get_content_template(content_type)

            # Step 5: Generate content using AI
            generated_content = await self._generate_content(
                transcript=transcript,
                template=template,
                video_request=video_request,
                user=user,
                target_keywords=target_keywords or [],
                target_audience=target_audience,
                brand_voice=brand_voice,
                custom_instructions=custom_instructions
            )

            return {
                'success': True,
                'workflow_id': f"workflow_{video_request.id}_{generated_content.id}",
                'video_request': {
                    'id': video_request.id,
                    'url': youtube_url,
                    'status': video_request.status,
                    'title': video_data.get('title', ''),
                    'duration': video_data.get('duration', 0)
                },
                'generated_content': {
                    'id': generated_content.id,
                    'title': generated_content.title,
                    'content_type': content_type,
                    'word_count': generated_content.word_count,
                    'reading_time': generated_content.estimated_reading_time,
                    'ai_confidence': generated_content.ai_confidence_score,
                    'content_preview': generated_content.content[:200] + '...',
                    'full_content': generated_content.content,
                    'meta_data': {
                        'meta_title': generated_content.meta_title,
                        'meta_description': generated_content.meta_description,
                        'keywords': generated_content.keywords,
                        'hashtags': generated_content.hashtags
                    }
                },
                'processing_time': {
                    'video_processing': video_data.get('processing_time', 0),
                    'content_generation': generated_content.content_request.processing_time_seconds
                },
                'usage': {
                    'tokens_used': generated_content.content_request.tokens_used,
                    'estimated_cost': float(generated_content.content_request.cost_estimate)
                }
            }

        except Exception as e:
            logger.error(f"Complete workflow failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'step_failed': self._determine_failure_step(e)
            }

    async def _create_video_request(self, youtube_url: str, user: User) -> VideoRequest:
        """Create video request from YouTube URL"""
        video_request = VideoRequest.objects.create(
            user=user,
            url=youtube_url,
            status='pending',
            moment_detection_type='ai_powered',
            video_quality='720p',
            max_clips=5  # We mainly need transcript, not clips
        )
        logger.info(f"Created video request {video_request.id} for {youtube_url}")
        return video_request

    async def _process_video(self, video_request: VideoRequest) -> Dict:
        """Download and process video"""
        start_time = timezone.now()

        try:
            # Download video (using existing clipper utils)
            video_path = await asyncio.to_thread(download_video, video_request.url)

            # Get video metadata
            video_info = {
                'title': 'Sample Video Title',  # Would extract from video metadata
                'duration': 300,  # Would get actual duration
                'file_path': video_path
            }

            # Update video request
            video_request.status = 'processing'
            video_request.save()

            processing_time = (timezone.now() - start_time).total_seconds()
            video_info['processing_time'] = processing_time

            logger.info(f"Video processed in {processing_time}s")
            return video_info

        except Exception as e:
            video_request.status = 'failed'
            video_request.save()
            raise Exception(f"Video processing failed: {str(e)}")

    async def _get_transcript(self, video_data: Dict) -> str:
        """Get video transcript using existing transcription"""
        try:
            # Use existing transcription service
            transcript = await asyncio.to_thread(
                transcribe_with_whisper,
                video_data['file_path']
            )

            logger.info(f"Transcript generated: {len(transcript)} characters")
            return transcript

        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")

    async def _get_content_template(self, content_type: str) -> ContentTemplate:
        """Get content template by type"""
        template_mapping = {
            'blog_post': 'SEO Blog Post',
            'show_notes': 'Podcast Show Notes',
            'social_media': 'Twitter Thread',
            'linkedin': 'LinkedIn Post',
            'youtube_description': 'YouTube Description',
            'email_newsletter': 'Email Newsletter',
            'key_takeaways': 'Key Takeaways',
            'summary': 'Video Summary'
        }

        template_name = template_mapping.get(content_type, 'SEO Blog Post')

        try:
            template = ContentTemplate.objects.get(
                name=template_name,
                is_built_in=True
            )
            return template
        except ContentTemplate.DoesNotExist:
            raise Exception(f"Template '{template_name}' not found")

    async def _generate_content(
        self,
        transcript: str,
        template: ContentTemplate,
        video_request: VideoRequest,
        user: User,
        target_keywords: list,
        target_audience: str,
        brand_voice: str,
        custom_instructions: str
    ) -> GeneratedContent:
        """Generate content using AI service"""

        # Create content generation request
        content_request = ContentGenerationRequest.objects.create(
            user=user,
            video_request=video_request,
            template=template,
            custom_instructions=custom_instructions,
            target_audience=target_audience,
            brand_voice=brand_voice,
            custom_keywords=target_keywords,
            status='processing'
        )

        start_time = timezone.now()

        try:
            # Generate content based on template type
            if template.template_type == 'blog_post':
                result = await self.ai_service.generate_blog_post(
                    transcript=transcript,
                    video_title=video_request.url,  # Would use actual title
                    target_keywords=target_keywords,
                    target_audience=target_audience,
                    brand_voice=brand_voice,
                    custom_instructions=custom_instructions,
                    word_count=template.max_words
                )

            elif template.template_type == 'show_notes':
                result = await self.ai_service.generate_show_notes(
                    transcript=transcript,
                    video_title=video_request.url,
                    custom_instructions=custom_instructions
                )

            elif template.template_type == 'social_media':
                result = await self.ai_service.generate_social_media_posts(
                    transcript=transcript,
                    video_title=video_request.url,
                    platform='twitter',
                    brand_voice=brand_voice,
                    custom_instructions=custom_instructions
                )

            else:
                # Fallback to blog post
                result = await self.ai_service.generate_blog_post(
                    transcript=transcript,
                    video_title=video_request.url,
                    target_keywords=target_keywords,
                    target_audience=target_audience,
                    brand_voice=brand_voice,
                    custom_instructions=custom_instructions
                )

            if not result.get('success'):
                raise Exception(result.get('error', 'AI generation failed'))

            # Calculate processing time
            processing_time = (timezone.now() - start_time).total_seconds()

            # Update content request
            content_request.status = 'completed'
            content_request.completed_at = timezone.now()
            content_request.processing_time_seconds = processing_time
            content_request.tokens_used = result.get('tokens_used', 0)
            content_request.cost_estimate = self.ai_service.calculate_cost(
                result.get('tokens_used', 0)
            )
            content_request.ai_model_used = 'gpt-4'
            content_request.save()

            # Create generated content
            generated_content = GeneratedContent.objects.create(
                content_request=content_request,
                user=user,
                title=result.get('title', 'Generated Content'),
                content=result.get('content', ''),
                format='markdown',
                meta_title=result.get('meta_title', ''),
                meta_description=result.get('meta_description', ''),
                keywords=result.get('keywords', []),
                headings=result.get('headings', []),
                hashtags=result.get('hashtags', []),
                ai_confidence_score=result.get('ai_confidence', 0.0)
            )

            logger.info(f"Content generated successfully: {generated_content.id}")
            return generated_content

        except Exception as e:
            content_request.status = 'failed'
            content_request.error_message = str(e)
            content_request.save()
            raise Exception(f"Content generation failed: {str(e)}")

    def _determine_failure_step(self, error: Exception) -> str:
        """Determine which step failed based on error message"""
        error_str = str(error).lower()

        if 'video processing' in error_str or 'download' in error_str:
            return 'video_processing'
        elif 'transcription' in error_str:
            return 'transcription'
        elif 'template' in error_str:
            return 'template_selection'
        elif 'content generation' in error_str or 'ai' in error_str:
            return 'content_generation'
        else:
            return 'unknown'

    # Utility methods for testing
    def get_supported_content_types(self) -> Dict:
        """Get all supported content types"""
        return {
            'blog_post': {
                'name': 'SEO Blog Post',
                'description': 'Full blog article with SEO optimization',
                'word_count': '800-1500 words',
                'features': ['SEO meta data', 'Headings', 'Keywords']
            },
            'show_notes': {
                'name': 'Show Notes',
                'description': 'Podcast episode summary with timestamps',
                'word_count': '300-1000 words',
                'features': ['Timestamps', 'Key takeaways', 'Resources']
            },
            'social_media': {
                'name': 'Social Media Posts',
                'description': 'Platform-optimized social content',
                'word_count': '50-500 words',
                'features': ['Hashtags', 'Platform optimization', 'CTAs']
            },
            'linkedin': {
                'name': 'LinkedIn Post',
                'description': 'Professional LinkedIn content',
                'word_count': '100-500 words',
                'features': ['Professional tone', 'Insights', 'Engagement']
            },
            'key_takeaways': {
                'name': 'Key Takeaways',
                'description': 'Actionable insights from video',
                'word_count': '150-400 words',
                'features': ['Bullet points', 'Actionable', 'Prioritized']
            }
        }

    async def test_complete_workflow(self, user: User) -> Dict:
        """Test the complete workflow with sample data"""
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        return await self.process_youtube_to_content(
            youtube_url=test_url,
            user=user,
            content_type='blog_post',
            target_keywords=['AI', 'automation', 'productivity'],
            target_audience='Content creators and marketers',
            brand_voice='professional',
            custom_instructions='Focus on practical tips and actionable insights'
        )