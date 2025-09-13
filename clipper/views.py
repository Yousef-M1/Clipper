from rest_framework import generics, authentication, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from core.models import VideoRequest, CaptionSettings, Clip
from clipper.serializers import VideoRequestSerializer, CaptionSettingsSerializer, ClipSerializer
from .tasks.tasks import process_video_request, process_video_with_custom_settings
from .video_quality import get_available_quality_presets, get_available_compression_levels
from .caption_styles import get_available_caption_styles

class VideoRequestCreateView(generics.CreateAPIView):
    """Enhanced video request creation with processing settings"""
    serializer_class = VideoRequestSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        video_request = serializer.save(user=self.request.user)

        # Get processing settings from request data
        processing_settings = self.request.data.get('processing_settings', {})

        # Default settings if not provided
        default_settings = {
            'moment_detection_type': 'ai_powered',
            'clip_duration': 30.0,
            'max_clips': 10,
            'video_quality': '720p',
            'compression_level': 'balanced',
            'caption_style': 'modern_purple',
            'enable_word_highlighting': True,
        }

        # Merge with defaults
        final_settings = {**default_settings, **processing_settings}

        # Start processing with custom settings
        if processing_settings:
            process_video_with_custom_settings.delay(video_request.id, **final_settings)
        else:
            # Use default processing
            process_video_request.delay(video_request.id)

class EnhancedVideoRequestCreateView(generics.CreateAPIView):
    """Video request creation with full control over processing settings"""
    serializer_class = VideoRequestSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create video request
        video_request = serializer.save(user=request.user)

        # Extract processing settings
        processing_settings = request.data.get('processing_settings', {})

        # Validate processing settings
        validated_settings = self.validate_processing_settings(processing_settings)

        # Start processing task
        process_video_with_custom_settings.delay(video_request.id, **validated_settings)

        return Response({
            'id': video_request.id,
            'url': video_request.url,
            'status': video_request.status,
            'processing_settings': validated_settings
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

        return validated

class VideoRequestListView(generics.ListAPIView):
    serializer_class = VideoRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

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
        'defaults': {
            'moment_detection_type': 'ai_powered',
            'clip_duration': 30.0,
            'max_clips': 10,
            'video_quality': '720p',
            'compression_level': 'balanced',
            'caption_style': 'modern_purple',
            'enable_word_highlighting': True
        }
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
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