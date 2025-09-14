from rest_framework import generics, authentication, permissions, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from django.http import HttpResponse, Http404
from django.db.models import Count, Q
from core.models import VideoRequest, CaptionSettings, Clip, UserCredits
from core.throttling import PlanBasedThrottle, VideoProcessingThrottle, BurstProtectionThrottle
from clipper.serializers import VideoRequestSerializer, CaptionSettingsSerializer, ClipSerializer
from .tasks.tasks import process_video_request, process_video_with_custom_settings
from .video_quality import get_available_quality_presets, get_available_compression_levels
from .caption_styles import get_available_caption_styles
from .video_formats import get_available_video_formats, get_available_platforms
import os
import mimetypes

class VideoRequestCreateView(generics.CreateAPIView):
    """Enhanced video request creation with processing settings"""
    serializer_class = VideoRequestSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [VideoProcessingThrottle, BurstProtectionThrottle]

    def perform_create(self, serializer):
        from core.queue_manager import QueueManager

        video_request = serializer.save(user=self.request.user)

        # Get processing settings from request data
        processing_settings = self.request.data.get('processing_settings', {})

        # Default settings if not provided
        default_settings = {
            'moment_detection_type': 'enhanced_ai',  # Now defaults to enhanced detection
            'clip_duration': 30.0,
            'max_clips': 10,
            'video_quality': '720p',
            'compression_level': 'balanced',
            'caption_style': 'modern_purple',
            'enable_word_highlighting': True,
            'enable_scene_detection': True,  # NEW: Enable visual scene detection
            'enable_composition_analysis': True,  # NEW: Enable composition scoring
        }

        # Merge with defaults
        final_settings = {**default_settings, **processing_settings}

        # Add to queue instead of direct processing
        queue_entry = QueueManager.add_to_queue(video_request, final_settings)

        # Log queue position for user feedback
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Video request {video_request.id} queued at position #{queue_entry.queue_position}")

        return video_request

class EnhancedVideoRequestCreateView(generics.CreateAPIView):
    """Video request creation with full control over processing settings"""
    serializer_class = VideoRequestSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [VideoProcessingThrottle, BurstProtectionThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create video request
        video_request = serializer.save(user=request.user)

        # Extract processing settings
        processing_settings = request.data.get('processing_settings', {})

        # Validate processing settings
        validated_settings = self.validate_processing_settings(processing_settings)

        # Add to queue instead of direct processing
        from core.queue_manager import QueueManager
        queue_entry = QueueManager.add_to_queue(video_request, validated_settings)

        return Response({
            'id': video_request.id,
            'url': video_request.url,
            'status': video_request.status,
            'processing_settings': validated_settings,
            'queue_position': queue_entry.queue_position,
            'estimated_wait_time': queue_entry.estimated_wait_time
        }, status=status.HTTP_201_CREATED)

    def validate_processing_settings(self, settings):
        """Validate and set defaults for processing settings"""
        validated = {}

        # Moment detection type
        moment_types = ['ai_powered', 'fixed_intervals']
        validated['moment_detection_type'] = settings.get('moment_detection_type', 'ai_powered')
        if validated['moment_detection_type'] not in moment_types:
            validated['moment_detection_type'] = 'ai_powered'

        # Clip settings
        validated['clip_duration'] = max(5.0, min(120.0, float(settings.get('clip_duration', 30.0))))
        validated['max_clips'] = max(1, min(50, int(settings.get('max_clips', 10))))

        # Video quality
        quality_presets = get_available_quality_presets()
        validated['video_quality'] = settings.get('video_quality', '720p')
        if validated['video_quality'] not in quality_presets:
            validated['video_quality'] = '720p'

        # Compression level
        compression_levels = get_available_compression_levels()
        validated['compression_level'] = settings.get('compression_level', 'balanced')
        if validated['compression_level'] not in compression_levels:
            validated['compression_level'] = 'balanced'

        # Caption style
        caption_styles = get_available_caption_styles()
        validated['caption_style'] = settings.get('caption_style', 'modern_purple')
        if validated['caption_style'] not in caption_styles:
            validated['caption_style'] = 'modern_purple'

        # Word highlighting
        validated['enable_word_highlighting'] = bool(settings.get('enable_word_highlighting', True))

        # Video format options
        format_types = ['horizontal', 'vertical', 'square', 'custom']
        validated['output_format'] = settings.get('output_format', 'horizontal')
        if validated['output_format'] not in format_types:
            validated['output_format'] = 'horizontal'

        # Social platform
        platform_presets = get_available_platforms()
        validated['social_platform'] = settings.get('social_platform', 'youtube')
        if validated['social_platform'] not in platform_presets:
            validated['social_platform'] = 'youtube'

        # Custom dimensions
        if validated['output_format'] == 'custom':
            from .video_formats import validate_custom_dimensions
            custom_width = settings.get('custom_width')
            custom_height = settings.get('custom_height')

            if custom_width and custom_height:
                is_valid, message = validate_custom_dimensions(int(custom_width), int(custom_height))
                if is_valid:
                    validated['custom_width'] = int(custom_width)
                    validated['custom_height'] = int(custom_height)
                else:
                    # Fallback to default format if custom dimensions are invalid
                    validated['output_format'] = 'horizontal'
                    validated.pop('custom_width', None)
                    validated.pop('custom_height', None)

        return validated

class VideoRequestListView(generics.ListAPIView):
    serializer_class = VideoRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PlanBasedThrottle]

    def get_queryset(self):
        return VideoRequest.objects.filter(user=self.request.user).order_by('-created_at')

class CaptionSettingsUpdateView(generics.RetrieveUpdateAPIView):
    queryset = CaptionSettings.objects.all()
    serializer_class = CaptionSettingsSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(video_request__user=self.request.user)

class ClipListView(generics.ListAPIView):
    serializer_class = ClipSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        video_request_id = self.kwargs['video_request_id']
        return Clip.objects.filter(
            video_request__id=video_request_id,
            video_request__user=self.request.user
        ).order_by('start_time')

# API Views for getting available options

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_quality_presets(request):
    """Get available video quality presets"""
    presets = get_available_quality_presets()
    return Response({
        'presets': presets,
        'default': '720p'
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_compression_levels(request):
    """Get available compression levels"""
    levels = get_available_compression_levels()
    return Response({
        'levels': levels,
        'default': 'balanced'
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_caption_styles(request):
    """Get available caption styles"""
    styles = get_available_caption_styles()
    return Response({
        'styles': styles,
        'default': 'modern_purple'
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_video_formats(request):
    """Get available video formats and aspect ratios"""
    formats = get_available_video_formats()
    return Response({
        'formats': formats,
        'default_format': 'horizontal'
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_platform_presets(request):
    """Get social media platform presets"""
    platforms = get_available_platforms()
    return Response({
        'platforms': platforms,
        'default_platform': 'youtube'
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_processing_options(request):
    """Get all available processing options"""
    return Response({
        'moment_detection_types': {
            'ai_powered': {
                'name': 'AI-Powered Detection',
                'description': 'Uses AI to identify engaging and viral moments'
            },
            'fixed_intervals': {
                'name': 'Fixed Intervals',
                'description': 'Creates clips at fixed time intervals'
            }
        },
        'quality_presets': get_available_quality_presets(),
        'compression_levels': get_available_compression_levels(),
        'caption_styles': get_available_caption_styles(),
        'video_formats': get_available_video_formats(),
        'platform_presets': get_available_platforms(),
        'defaults': {
            'moment_detection_type': 'ai_powered',
            'clip_duration': 30.0,
            'max_clips': 10,
            'video_quality': '720p',
            'compression_level': 'balanced',
            'caption_style': 'modern_purple',
            'enable_word_highlighting': True,
            'output_format': 'horizontal',
            'social_platform': 'youtube'
        }
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([VideoProcessingThrottle, BurstProtectionThrottle])
def reprocess_video(request, video_request_id):
    """Reprocess an existing video with new settings"""
    try:
        video_request = VideoRequest.objects.get(id=video_request_id, user=request.user)
    except VideoRequest.DoesNotExist:
        return Response({'error': 'Video request not found'}, status=status.HTTP_404_NOT_FOUND)

    # Get new processing settings
    processing_settings = request.data.get('processing_settings', {})

    # Validate settings
    view = EnhancedVideoRequestCreateView()
    validated_settings = view.validate_processing_settings(processing_settings)

    # Delete existing clips
    video_request.clips.all().delete()

    # Update status and start reprocessing
    video_request.status = 'pending'
    video_request.save()

    process_video_with_custom_settings.delay(video_request_id, **validated_settings)

    return Response({
        'message': 'Video reprocessing started',
        'video_request_id': video_request_id,
        'new_settings': validated_settings
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def estimate_processing_cost(request):
    """Estimate processing time and resources based on settings"""
    duration = float(request.GET.get('duration', 300))  # 5 minutes default
    settings = {
        'moment_detection_type': request.GET.get('moment_detection_type', 'ai_powered'),
        'video_quality': request.GET.get('video_quality', '720p'),
        'max_clips': int(request.GET.get('max_clips', 10)),
        'enable_word_highlighting': request.GET.get('enable_word_highlighting', 'true').lower() == 'true'
    }

    # Rough estimates
    base_time = duration * 0.1  # 10% of video duration for basic processing

    if settings['moment_detection_type'] == 'ai_powered':
        base_time *= 2  # AI detection takes longer

    quality_multiplier = {
        '480p': 0.7,
        '720p': 1.0,
        '1080p': 1.5,
        '1440p': 2.2,
        '2160p': 4.0
    }.get(settings['video_quality'], 1.0)

    base_time *= quality_multiplier

    if settings['enable_word_highlighting']:
        base_time *= 1.2  # Word highlighting adds some processing time

    estimated_time = base_time * settings['max_clips'] / 10  # Scale by number of clips

    return Response({
        'estimated_processing_time_minutes': round(estimated_time / 60, 1),
        'settings_impact': {
            'ai_detection': settings['moment_detection_type'] == 'ai_powered',
            'quality_multiplier': quality_multiplier,
            'word_highlighting': settings['enable_word_highlighting'],
            'clip_count': settings['max_clips']
        }
    })

# DASHBOARD VIEWS

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    """Get user's dashboard summary with stats and recent activity"""
    user = request.user

    # Get user's video statistics
    video_stats = VideoRequest.objects.filter(user=user).aggregate(
        total_videos=Count('id'),
        completed_videos=Count('id', filter=Q(status='done')),
        processing_videos=Count('id', filter=Q(status='processing')),
        failed_videos=Count('id', filter=Q(status='failed')),
        total_clips=Count('clips')
    )

    # Get user credits info
    try:
        user_credits = UserCredits.objects.get(user=user)
        credits_info = {
            'plan': user_credits.plan.name if user_credits.plan else 'No Plan',
            'monthly_credits': user_credits.plan.monthly_credits if user_credits.plan else 0,
            'used_credits': user_credits.used_credits,
            'remaining_credits': user_credits.remaining_credits,
            'credit_per_clip': user_credits.plan.credit_per_clip if user_credits.plan else 1
        }
    except UserCredits.DoesNotExist:
        credits_info = {
            'plan': 'No Plan',
            'monthly_credits': 0,
            'used_credits': 0,
            'remaining_credits': 0,
            'credit_per_clip': 1
        }

    # Get recent videos (last 10)
    recent_videos = VideoRequest.objects.filter(user=user).order_by('-created_at')[:10]
    recent_videos_data = VideoRequestSerializer(recent_videos, many=True).data

    return Response({
        'user': {
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.created_at
        },
        'stats': video_stats,
        'credits': credits_info,
        'recent_videos': recent_videos_data,
        'quick_actions': [
            {'label': 'Create New Video', 'endpoint': '/api/clipper/video-requests/create-enhanced/'},
            {'label': 'View All Videos', 'endpoint': '/api/clipper/video-requests/'},
            {'label': 'Account Settings', 'endpoint': '/api/user/manage/'}
        ]
    })

class VideoRequestDetailView(generics.RetrieveAPIView):
    """Get detailed information about a video request including all clips"""
    serializer_class = VideoRequestSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VideoRequest.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Get all clips for this video
        clips = Clip.objects.filter(video_request=instance).order_by('start_time')
        clips_data = ClipSerializer(clips, many=True).data

        # Add download URLs to clips
        for i, clip_data in enumerate(clips_data):
            clip_data['download_url'] = f"/api/clipper/clips/{clips[i].id}/download/"

        return Response({
            'video': serializer.data,
            'clips': clips_data,
            'clips_count': len(clips_data),
            'total_duration': sum(clip.duration for clip in clips),
            'processing_settings': instance.processing_settings if hasattr(instance, 'processing_settings') else {}
        })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_clip(request, clip_id):
    """Download a specific clip file"""
    try:
        clip = Clip.objects.get(
            id=clip_id,
            video_request__user=request.user
        )
    except Clip.DoesNotExist:
        raise Http404("Clip not found or you don't have permission to access it")

    # Check if file exists
    if not clip.file_path or not clip.file_path.name:
        return Response({'error': 'Clip file not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        file_path = clip.file_path.path
        if not os.path.exists(file_path):
            return Response({'error': 'Clip file not found on disk'}, status=status.HTTP_404_NOT_FOUND)

        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'video/mp4'

        # Create response
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="clip_{clip_id}_{clip.start_time}-{clip.end_time}s.mp4"'
            return response

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_video_request(request, video_request_id):
    """Delete a video request and all its clips"""
    try:
        video_request = VideoRequest.objects.get(
            id=video_request_id,
            user=request.user
        )
    except VideoRequest.DoesNotExist:
        raise Http404("Video request not found")

    # Delete associated files
    clips = video_request.clips.all()
    deleted_files = 0

    for clip in clips:
        if clip.file_path and clip.file_path.name:
            try:
                if os.path.exists(clip.file_path.path):
                    os.remove(clip.file_path.path)
                    deleted_files += 1
            except Exception as e:
                pass  # Continue even if file deletion fails

    # Delete the video request (this will cascade delete clips)
    video_request.delete()

    return Response({
        'message': 'Video request deleted successfully',
        'deleted_clips': len(clips),
        'deleted_files': deleted_files
    })

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_clip(request, clip_id):
    """Delete a specific clip"""
    try:
        clip = Clip.objects.get(
            id=clip_id,
            video_request__user=request.user
        )
    except Clip.DoesNotExist:
        raise Http404("Clip not found")

    # Delete associated file
    if clip.file_path and clip.file_path.name:
        try:
            if os.path.exists(clip.file_path.path):
                os.remove(clip.file_path.path)
        except Exception as e:
            pass  # Continue even if file deletion fails

    clip.delete()

    return Response({'message': 'Clip deleted successfully'})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_download_clips(request):
    """Get download URLs for multiple clips"""
    clip_ids = request.data.get('clip_ids', [])

    if not clip_ids:
        return Response({'error': 'No clip IDs provided'}, status=status.HTTP_400_BAD_REQUEST)

    clips = Clip.objects.filter(
        id__in=clip_ids,
        video_request__user=request.user
    ).select_related('video_request')

    if len(clips) != len(clip_ids):
        return Response({'error': 'Some clips not found or unauthorized'}, status=status.HTTP_404_NOT_FOUND)

    download_info = []
    for clip in clips:
        download_info.append({
            'clip_id': clip.id,
            'filename': f"clip_{clip.id}_{clip.start_time}-{clip.end_time}s.mp4",
            'download_url': f"/api/clipper/clips/{clip.id}/download/",
            'duration': clip.duration,
            'size_mb': clip.file_size_mb
        })

    return Response({
        'clips': download_info,
        'total_clips': len(download_info),
        'estimated_total_size_mb': sum(clip.file_size_mb or 10 for clip in clips)  # Default 10MB if size unknown
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([PlanBasedThrottle])
def get_rate_limit_status(request):
    """Get current user's rate limit status and usage"""
    try:
        from core.models import UserCredits

        # Get user's plan
        try:
            user_credits = UserCredits.objects.get(user=request.user)
            plan_name = user_credits.plan.name if user_credits.plan else 'free'
        except UserCredits.DoesNotExist:
            plan_name = 'free'

        # Define limits for different operations
        plan_limits = {
            'free': {
                'general': 50,
                'video_processing': 2,
                'burst': 10
            },
            'pro': {
                'general': 200,
                'video_processing': 20,
                'burst': 10
            },
            'premium': {
                'general': 500,
                'video_processing': 50,
                'burst': 10
            }
        }

        limits = plan_limits.get(plan_name, plan_limits['free'])

        return Response({
            'plan': plan_name,
            'limits': {
                'general_requests_per_hour': limits['general'],
                'video_processing_per_hour': limits['video_processing'],
                'burst_requests_per_minute': limits['burst']
            },
            'features': {
                'priority_processing': plan_name in ['pro', 'premium'],
                'advanced_settings': plan_name in ['pro', 'premium'],
                'unlimited_downloads': plan_name == 'premium'
            }
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# QUEUE MANAGEMENT ENDPOINTS

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([PlanBasedThrottle])
def get_queue_status(request):
    """Get user's queue status and system queue info"""
    from core.queue_manager import QueueManager

    user_queue_status = QueueManager.get_queue_status(request.user)

    return Response({
        'user_queue': user_queue_status['user_queue'],
        'system_status': {
            'total_queued': user_queue_status['queue_length'],
            'currently_processing': user_queue_status['processing_count']
        },
        'user_priority': QueueManager.get_user_priority(request.user),
        'priority_description': {
            1: 'Free - Lower priority',
            2: 'Pro - Normal priority',
            3: 'Premium - High priority'
        }.get(QueueManager.get_user_priority(request.user), 'Unknown')
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_processing_history(request):
    """Get user's processing history"""
    from core.models import ProcessingQueue

    limit = int(request.GET.get('limit', 10))

    history = ProcessingQueue.objects.filter(
        user=request.user
    ).order_by('-completed_at')[:limit]

    history_data = []
    for entry in history:
        history_data.append({
            'id': entry.id,
            'video_url': entry.video_request.url,
            'status': entry.status,
            'priority': entry.priority,
            'queued_at': entry.queued_at,
            'started_at': entry.started_at,
            'completed_at': entry.completed_at,
            'actual_duration': entry.actual_duration,
            'clips_generated': entry.video_request.clips.count(),
            'error_message': entry.error_message if entry.status == 'failed' else None
        })

    return Response({
        'history': history_data,
        'total_processed': ProcessingQueue.objects.filter(
            user=request.user,
            status__in=['completed', 'failed']
        ).count()
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_processing(request, queue_id):
    """Cancel a queued processing task"""
    from core.models import ProcessingQueue
    from core.queue_manager import QueueManager

    try:
        queue_entry = ProcessingQueue.objects.get(
            id=queue_id,
            user=request.user
        )

        success = QueueManager.cancel_task(queue_entry)

        if success:
            return Response({
                'message': 'Processing task cancelled successfully',
                'status': queue_entry.status
            })
        else:
            return Response({
                'error': 'Cannot cancel task - it may already be processing or completed'
            }, status=status.HTTP_400_BAD_REQUEST)

    except ProcessingQueue.DoesNotExist:
        return Response({'error': 'Queue entry not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def retry_processing(request, queue_id):
    """Retry a failed processing task"""
    from core.models import ProcessingQueue
    from core.queue_manager import QueueManager

    try:
        queue_entry = ProcessingQueue.objects.get(
            id=queue_id,
            user=request.user
        )

        success = QueueManager.retry_failed_task(queue_entry)

        if success:
            return Response({
                'message': 'Processing task queued for retry',
                'status': queue_entry.status,
                'retry_count': queue_entry.retry_count,
                'queue_position': queue_entry.queue_position
            })
        else:
            return Response({
                'error': 'Cannot retry task - maximum retries exceeded or task is not failed'
            }, status=status.HTTP_400_BAD_REQUEST)

    except ProcessingQueue.DoesNotExist:
        return Response({'error': 'Queue entry not found'}, status=status.HTTP_404_NOT_FOUND)


# ENHANCED SCENE DETECTION ENDPOINTS - CutMagic-like functionality

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([PlanBasedThrottle])
def analyze_video_composition(request):
    """
    Analyze video composition and provide insights
    Similar to Quaso's comprehensive video analysis
    """
    from clipper.scene_detection import analyze_video_composition as analyze_composition

    try:
        video_request_id = request.data.get('video_request_id')
        if not video_request_id:
            return Response({'error': 'video_request_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get video request
        video_request = VideoRequest.objects.get(
            id=video_request_id,
            user=request.user
        )

        # Check if file exists
        if not video_request.video_file or not os.path.exists(video_request.video_file.path):
            return Response({'error': 'Video file not found'}, status=status.HTTP_404_NOT_FOUND)

        # Analyze composition
        analysis = analyze_composition(video_request.video_file.path)

        return Response({
            'video_id': video_request_id,
            'analysis': analysis,
            'message': 'Video composition analysis completed'
        })

    except VideoRequest.DoesNotExist:
        return Response({'error': 'Video request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([PlanBasedThrottle])
def detect_enhanced_moments(request):
    """
    Enhanced moment detection with visual scene analysis
    Combines AI transcript analysis with visual scene detection
    """
    from clipper.ai_moments import detect_ai_moments_with_composition

    try:
        video_request_id = request.data.get('video_request_id')
        clip_duration = float(request.data.get('clip_duration', 30.0))
        max_clips = int(request.data.get('max_clips', 10))
        enable_scene_detection = request.data.get('enable_scene_detection', True)

        if not video_request_id:
            return Response({'error': 'video_request_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get video request
        video_request = VideoRequest.objects.get(
            id=video_request_id,
            user=request.user
        )

        # Check if file exists
        if not video_request.video_file or not os.path.exists(video_request.video_file.path):
            return Response({'error': 'Video file not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get transcript (simplified for now)
        transcript = []  # You can integrate with your existing transcript generation

        # Run enhanced detection
        results = detect_ai_moments_with_composition(
            video_request.video_file.path,
            transcript,
            clip_duration,
            max_clips,
            enable_scene_detection
        )

        return Response({
            'video_id': video_request_id,
            'moments': results['moments'],
            'video_analysis': results['video_analysis'],
            'recommendations': results['recommendations'],
            'quality_score': results['quality_score'],
            'total_moments_found': len(results['moments']),
            'message': 'Enhanced moment detection completed'
        })

    except VideoRequest.DoesNotExist:
        return Response({'error': 'Video request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([PlanBasedThrottle])
def detect_scene_transitions(request):
    """
    Detect scene transitions and cuts
    Similar to Quaso's CutMagic automatic scene detection
    """
    from clipper.scene_detection import detect_enhanced_scenes

    try:
        video_request_id = request.data.get('video_request_id')
        max_scenes = int(request.data.get('max_scenes', 20))

        if not video_request_id:
            return Response({'error': 'video_request_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get video request
        video_request = VideoRequest.objects.get(
            id=video_request_id,
            user=request.user
        )

        # Check if file exists
        if not video_request.video_file or not os.path.exists(video_request.video_file.path):
            return Response({'error': 'Video file not found'}, status=status.HTTP_404_NOT_FOUND)

        # Detect scenes
        scenes = detect_enhanced_scenes(video_request.video_file.path, max_scenes)

        # Format for API response
        formatted_scenes = []
        for scene in scenes:
            formatted_scenes.append({
                'start_time': scene['start'],
                'end_time': scene['end'],
                'duration': scene['end'] - scene['start'],
                'shot_type': scene.get('visual_features', {}).get('shot_type', 'unknown'),
                'composition_score': scene['score'],
                'faces_detected': scene.get('visual_features', {}).get('face_count', 0),
                'motion_intensity': scene.get('visual_features', {}).get('motion_intensity', 0.5),
                'text_detected': scene.get('visual_features', {}).get('text_detected', False),
                'reason': scene.get('reason', 'Visual scene detected'),
                'tags': scene.get('tags', [])
            })

        return Response({
            'video_id': video_request_id,
            'scenes': formatted_scenes,
            'total_scenes': len(formatted_scenes),
            'message': f'Detected {len(formatted_scenes)} scene transitions'
        })

    except VideoRequest.DoesNotExist:
        return Response({'error': 'Video request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_scene_detection_capabilities(request):
    """
    Get available scene detection capabilities and settings
    """
    return Response({
        'features': {
            'visual_scene_detection': True,
            'shot_type_classification': True,
            'face_detection': True,
            'motion_analysis': True,
            'text_detection': True,
            'composition_scoring': True,
            'color_analysis': True
        },
        'shot_types': [
            'close_up',
            'medium_shot',
            'wide_shot',
            'extreme_close_up',
            'talking_head',
            'action_shot',
            'transition'
        ],
        'analysis_features': [
            'scene_boundaries',
            'composition_quality',
            'face_count_per_scene',
            'motion_intensity',
            'dominant_colors',
            'text_regions',
            'virality_scoring'
        ],
        'supported_formats': ['mp4', 'avi', 'mov', 'mkv'],
        'max_duration_minutes': 180,  # 3 hours
        'message': 'Enhanced scene detection powered by computer vision'
    })