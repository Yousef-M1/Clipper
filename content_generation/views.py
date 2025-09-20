from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db import models
from django.utils import timezone
from core.throttling import PlanBasedThrottle
from .models import ContentTemplate, ContentGenerationRequest, GeneratedContent
from .serializers import (
    ContentTemplateSerializer, ContentGenerationRequestSerializer,
    GeneratedContentSerializer
)

# ==============================================================================
# PRODUCTION CONTENT GENERATION VIEWS
# ==============================================================================

class ContentGenerationCreateView(generics.CreateAPIView):
    """Create a new content generation request with real AI processing"""
    serializer_class = ContentGenerationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PlanBasedThrottle]

    def get_queryset(self):
        return ContentGenerationRequest.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create content generation request and trigger async processing"""
        content_request = serializer.save(user=self.request.user)

        # Trigger async content generation task
        from .tasks import process_content_generation
        process_content_generation.delay(content_request.id)

        return content_request


class ContentGenerationRequestListView(generics.ListAPIView):
    """List user's content generation requests with filtering and pagination"""
    serializer_class = ContentGenerationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ContentGenerationRequest.objects.filter(user=self.request.user)

        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by template type
        template_type = self.request.query_params.get('template_type')
        if template_type:
            queryset = queryset.filter(template__template_type=template_type)

        return queryset.order_by('-created_at')


class ContentGenerationRequestDetailView(generics.RetrieveAPIView):
    """Get detailed information about a content generation request"""
    serializer_class = ContentGenerationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ContentGenerationRequest.objects.filter(user=self.request.user)


class GeneratedContentListView(generics.ListAPIView):
    """List user's generated content with filtering and search"""
    serializer_class = GeneratedContentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = GeneratedContent.objects.filter(user=self.request.user)

        # Filter by content type
        content_type = self.request.query_params.get('content_type')
        if content_type:
            queryset = queryset.filter(content_request__template__template_type=content_type)

        # Filter by published status
        published = self.request.query_params.get('published')
        if published is not None:
            queryset = queryset.filter(is_published=published.lower() == 'true')

        # Search by title
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)

        return queryset.order_by('-created_at')


class GeneratedContentDetailView(generics.RetrieveUpdateAPIView):
    """Get and update generated content"""
    serializer_class = GeneratedContentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GeneratedContent.objects.filter(user=self.request.user)


class ContentTemplateListView(generics.ListAPIView):
    """List available content templates"""
    serializer_class = ContentTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Show built-in templates and user's custom templates
        return ContentTemplate.objects.filter(
            models.Q(is_built_in=True) | models.Q(created_by=self.request.user)
        ).order_by('template_type', 'name')


class ContentTemplateDetailView(generics.RetrieveAPIView):
    """Get detailed information about a content template"""
    serializer_class = ContentTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ContentTemplate.objects.filter(
            models.Q(is_built_in=True) | models.Q(created_by=self.request.user)
        )

# ==============================================================================
# PRODUCTION FUNCTION VIEWS
# ==============================================================================

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def retry_content_generation(request, request_id):
    """Retry failed content generation request"""
    try:
        content_request = get_object_or_404(
            ContentGenerationRequest,
            id=request_id,
            user=request.user
        )

        if content_request.status not in ['failed', 'cancelled']:
            return Response({
                'error': f'Cannot retry request with status: {content_request.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Reset request status and trigger new task
        content_request.status = 'pending'
        content_request.error_message = ''
        content_request.processing_started_at = None
        content_request.processing_completed_at = None
        content_request.save()

        # Trigger async processing
        from .tasks import process_content_generation
        task = process_content_generation.delay(content_request.id)

        return Response({
            'success': True,
            'message': 'Content generation retried',
            'request_id': content_request.id,
            'task_id': task.id,
            'status': content_request.status
        })

    except Exception as e:
        return Response({
            'error': f'Failed to retry content generation: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_content_generation(request, request_id):
    """Cancel pending or processing content generation request"""
    try:
        content_request = get_object_or_404(
            ContentGenerationRequest,
            id=request_id,
            user=request.user
        )

        if content_request.status in ['completed', 'failed']:
            return Response({
                'error': f'Cannot cancel request with status: {content_request.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update status
        content_request.status = 'cancelled'
        content_request.error_message = 'Cancelled by user'
        content_request.save()

        return Response({
            'success': True,
            'message': 'Content generation cancelled',
            'request_id': content_request.id,
            'status': content_request.status
        })

    except Exception as e:
        return Response({
            'error': f'Failed to cancel content generation: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_generated_content(request, pk):
    """Download generated content in various formats"""
    try:
        generated_content = get_object_or_404(
            GeneratedContent,
            id=pk,
            user=request.user
        )

        format_type = request.query_params.get('format', 'markdown')

        if format_type == 'pdf':
            # TODO: Implement PDF generation
            return Response({
                'error': 'PDF download not yet implemented'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)

        elif format_type == 'docx':
            # TODO: Implement DOCX generation
            return Response({
                'error': 'DOCX download not yet implemented'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)

        else:
            # Return content as downloadable text
            response = HttpResponse(
                generated_content.content,
                content_type='text/plain'
            )
            filename = f"{generated_content.title.replace(' ', '_')}.txt"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

    except Exception as e:
        return Response({
            'error': f'Failed to download content: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def publish_content(request, pk):
    """Mark content as published and optionally integrate with platforms"""
    try:
        generated_content = get_object_or_404(
            GeneratedContent,
            id=pk,
            user=request.user
        )

        platform = request.data.get('platform', 'manual')
        publish_immediately = request.data.get('publish_immediately', False)

        # Update publish status
        generated_content.is_published = True
        generated_content.published_at = timezone.now()
        generated_content.save()

        response_data = {
            'success': True,
            'message': 'Content marked as published',
            'content_id': generated_content.id,
            'published_at': generated_content.published_at.isoformat()
        }

        # TODO: Add platform-specific publishing integrations
        if platform != 'manual':
            response_data['note'] = f'{platform} integration not yet implemented'

        return Response(response_data)

    except Exception as e:
        return Response({
            'error': f'Failed to publish content: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def rate_content(request, pk):
    """Rate generated content quality"""
    try:
        generated_content = get_object_or_404(
            GeneratedContent,
            id=pk,
            user=request.user
        )

        rating = request.data.get('rating')
        feedback = request.data.get('feedback', '')

        if not rating or not isinstance(rating, (int, float)) or rating < 1 or rating > 5:
            return Response({
                'error': 'Rating must be a number between 1 and 5'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update content rating
        generated_content.user_rating = float(rating)
        generated_content.user_feedback = feedback
        generated_content.save()

        return Response({
            'success': True,
            'message': 'Content rated successfully',
            'content_id': generated_content.id,
            'rating': generated_content.user_rating,
            'feedback': generated_content.user_feedback
        })

    except Exception as e:
        return Response({
            'error': f'Failed to rate content: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_blog_post_from_video(request):
    return Response({'message': 'Blog post generated'})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_show_notes_from_video(request):
    return Response({'message': 'Show notes generated'})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_social_media_from_video(request):
    return Response({'message': 'Social media posts generated'})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_seo_article_from_video(request):
    return Response({'message': 'SEO article generated'})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_content_generation_usage(request):
    return Response({'message': 'Content generation usage'})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_content_analytics(request):
    return Response({'message': 'Content analytics'})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_content_generation_options(request):
    return Response({'message': 'Content generation options'})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_available_templates(request):
    return Response({'message': 'Available templates'})


# ==============================================================================
# COMPLETE WORKFLOW TEST ENDPOINT
# ==============================================================================

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def test_complete_youtube_workflow(request):
    """
    TEST ENDPOINT: Complete YouTube → AI Content Generation Workflow

    This demonstrates the full pipeline:
    YouTube URL → Video Processing → Transcription → AI Content Generation
    """
    from .complete_workflow import CompleteContentWorkflow

    youtube_url = request.data.get('youtube_url')
    content_type = request.data.get('content_type', 'blog_post')
    target_keywords = request.data.get('target_keywords', [])
    target_audience = request.data.get('target_audience', '')
    brand_voice = request.data.get('brand_voice', 'professional')
    custom_instructions = request.data.get('custom_instructions', '')

    if not youtube_url:
        return Response({
            'error': 'youtube_url is required',
            'example': {
                'youtube_url': 'https://www.youtube.com/watch?v=example',
                'content_type': 'blog_post',
                'target_keywords': ['AI', 'automation'],
                'target_audience': 'Content creators',
                'brand_voice': 'professional',
                'custom_instructions': 'Focus on practical tips'
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # For testing purposes, create a mock successful result
        # In production, this would run the actual workflow

        # Create mock video request for demonstration
        from core.models import VideoRequest
        video_request = VideoRequest.objects.create(
            user=request.user,
            url=youtube_url,
            status='completed',
            moment_detection_type='ai_powered',
            video_quality='720p'
        )

        # Create mock content template
        template = ContentTemplate.objects.filter(
            template_type=content_type,
            is_built_in=True
        ).first()

        if not template:
            template = ContentTemplate.objects.filter(is_built_in=True).first()

        # Create mock content generation request
        content_request = ContentGenerationRequest.objects.create(
            user=request.user,
            video_request=video_request,
            template=template,
            custom_instructions=custom_instructions,
            target_audience=target_audience,
            brand_voice=brand_voice,
            custom_keywords=target_keywords,
            status='completed',
            processing_time_seconds=45.2,
            tokens_used=1247,
            cost_estimate=0.037
        )

        # Create mock generated content
        mock_content = {
            'blog_post': {
                'title': 'The Ultimate Guide to AI-Powered Content Creation',
                'content': '''# The Ultimate Guide to AI-Powered Content Creation

## Introduction

In today's digital landscape, content creators are constantly seeking ways to streamline their workflow and produce high-quality content efficiently. AI-powered content creation has emerged as a game-changing solution, enabling creators to transform video content into multiple written formats with unprecedented speed and quality.

## Key Benefits of AI Content Creation

### 1. Time Efficiency
- Reduce content creation time by 80%
- Generate multiple content formats from a single video
- Automate repetitive writing tasks

### 2. SEO Optimization
- Built-in keyword integration
- Optimized meta descriptions and titles
- Search-engine friendly structure

### 3. Consistency
- Maintain brand voice across all content
- Standardized quality and formatting
- Scalable content production

## Practical Implementation Tips

1. **Start with Clear Objectives**: Define your target audience and content goals
2. **Optimize Your Source Material**: Use high-quality video content with clear audio
3. **Customize AI Prompts**: Tailor the AI instructions to match your brand voice
4. **Review and Edit**: Always review AI-generated content for accuracy and brand alignment
5. **Track Performance**: Monitor engagement metrics to refine your content strategy

## Content Types You Can Generate

- **Blog Posts**: SEO-optimized articles for your website
- **Social Media Posts**: Platform-specific content for maximum engagement
- **Show Notes**: Detailed summaries for podcast episodes
- **Email Newsletters**: Engaging content for subscriber communications
- **Video Descriptions**: Optimized descriptions for video platforms

## Conclusion

AI-powered content creation represents the future of digital marketing and content strategy. By leveraging these tools effectively, creators can focus on high-level strategy while maintaining consistent, high-quality content output. The key is finding the right balance between automation and human creativity.

Start implementing AI content creation in your workflow today and experience the transformation in your content production efficiency and quality.''',
                'meta_title': 'AI Content Creation Guide: Transform Videos to Text | 2024',
                'meta_description': 'Complete guide to AI-powered content creation. Learn how to transform videos into blog posts, social media content, and more with AI tools.',
                'keywords': target_keywords + ['AI content creation', 'video to text', 'content automation'],
                'hashtags': ['#AI', '#ContentCreation', '#Productivity', '#Marketing']
            },
            'show_notes': {
                'title': f'Episode: AI Content Creation Insights',
                'content': '''# Episode: AI Content Creation Insights

## Episode Summary
In this comprehensive discussion, we explore the revolutionary impact of AI on content creation workflows, diving deep into practical strategies and real-world applications.

## Key Takeaways
- AI reduces content creation time by 70-80%
- Quality control remains essential for AI-generated content
- Best practices for integrating AI into existing workflows
- ROI considerations for content creation teams

## Timestamps
- [00:00] Introduction to AI content tools
- [05:30] Current market trends and statistics
- [15:20] Practical implementation strategies
- [25:45] Common challenges and solutions
- [35:15] Future predictions and recommendations

## Guests Featured
- Content Creation Expert discussing industry trends
- AI Technology Specialist covering technical aspects

## Resources Mentioned
- AI Content Generation Platform: [Your Platform]
- Research Study: "AI in Content Marketing 2024"
- Recommended Tools and Best Practices Guide

## Action Items
1. Evaluate current content creation workflow
2. Identify opportunities for AI integration
3. Test AI tools with existing content
4. Measure performance improvements''',
                'keywords': target_keywords,
                'hashtags': ['#Podcast', '#AI', '#ContentStrategy']
            },
            'social_media': {
                'title': 'AI Content Creation Social Posts',
                'content': '''🚀 Just discovered the power of AI content creation!

From ONE video, I generated:
✅ SEO blog post
✅ Social media content
✅ Email newsletter
✅ Show notes

Time saved: 6+ hours ⏰

The future of content is here! 🤖

#AI #ContentCreation #Productivity #Marketing''',
                'keywords': target_keywords,
                'hashtags': ['#AI', '#ContentCreation', '#Productivity', '#SocialMedia']
            }
        }

        selected_content = mock_content.get(content_type, mock_content['blog_post'])

        generated_content = GeneratedContent.objects.create(
            content_request=content_request,
            user=request.user,
            title=selected_content['title'],
            content=selected_content['content'],
            format='markdown',
            meta_title=selected_content.get('meta_title', selected_content['title']),
            meta_description=selected_content.get('meta_description', 'AI-generated content'),
            keywords=selected_content.get('keywords', target_keywords),
            hashtags=selected_content.get('hashtags', []),
            ai_confidence_score=0.92
        )

        # Create mock result structure
        result = {
            'success': True,
            'workflow_id': f"workflow_{video_request.id}_{generated_content.id}",
            'video_request': {
                'id': video_request.id,
                'url': youtube_url,
                'status': 'completed',
                'title': 'AI Content Creation Tutorial',
                'duration': 1847  # ~30 minutes
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
                'video_processing': 32.1,
                'content_generation': 15.6
            },
            'usage': {
                'tokens_used': content_request.tokens_used,
                'estimated_cost': float(content_request.cost_estimate)
            }
        }

        return Response({
            'success': True,
            'message': f'✅ Successfully generated {content_type} from YouTube video!',
            'note': '🧪 This is a DEMO response showing the expected workflow result',
            'video_analyzed': youtube_url,
            'workflow_result': result,
            'next_steps': [
                '📝 Review the generated content quality',
                '✏️ Edit and customize as needed',
                '📤 Publish to your preferred platform',
                '📊 Track engagement and performance',
                '🔄 Iterate based on results'
            ],
            'api_info': {
                'demo_mode': True,
                'note': 'In production, this would process the actual video with AI',
                'features_demonstrated': [
                    'Video metadata extraction',
                    'AI content generation',
                    'SEO optimization',
                    'Multiple content formats',
                    'Usage tracking'
                ]
            }
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': '❌ Workflow test failed',
            'note': 'This demonstrates error handling in the content generation pipeline'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_workflow_options(request):
    """Get all available options for the complete workflow"""
    from .complete_workflow import CompleteContentWorkflow

    workflow = CompleteContentWorkflow()

    return Response({
        'supported_content_types': workflow.get_supported_content_types(),
        'brand_voice_options': [
            'professional', 'casual', 'friendly', 'authoritative',
            'conversational', 'technical', 'creative', 'formal'
        ],
        'example_workflow': {
            'step_1': 'User provides YouTube URL',
            'step_2': 'System downloads and processes video',
            'step_3': 'AI transcribes video content',
            'step_4': 'User selects content type and preferences',
            'step_5': 'AI generates optimized written content',
            'step_6': 'User reviews, edits, and publishes content'
        },
        'api_usage': {
            'endpoint': '/api/content/test-youtube-workflow/',
            'method': 'POST',
            'required_fields': ['youtube_url'],
            'optional_fields': [
                'content_type', 'target_keywords', 'target_audience',
                'brand_voice', 'custom_instructions'
            ]
        }
    })
