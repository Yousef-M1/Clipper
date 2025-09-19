"""
API views for AI influencer video generation
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import AvatarProject, AvatarCharacter, VoiceProfile
from .serializers import (
    AvatarProjectSerializer,
    AvatarCharacterSerializer,
    VoiceProfileSerializer,
    CreateAvatarProjectSerializer
)
from .tasks import process_tts_only
from .tts_service import TTSService


class AvatarCharacterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for available avatar characters
    """
    queryset = AvatarCharacter.objects.filter(is_active=True)
    serializer_class = AvatarCharacterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        gender = self.request.query_params.get('gender')
        if gender:
            queryset = queryset.filter(gender=gender)
        return queryset


class VoiceProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for available voice profiles
    """
    queryset = VoiceProfile.objects.filter(is_active=True)
    serializer_class = VoiceProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by engine
        engine = self.request.query_params.get('engine')
        if engine:
            queryset = queryset.filter(engine=engine)

        # Filter by language
        language = self.request.query_params.get('language')
        if language:
            queryset = queryset.filter(language=language)

        # Filter by gender
        gender = self.request.query_params.get('gender')
        if gender:
            queryset = queryset.filter(gender=gender)

        # Filter by premium status
        user = self.request.user
        if not hasattr(user, 'plan') or user.plan.name == 'free':
            queryset = queryset.filter(is_premium=False)

        return queryset

    @action(detail=False, methods=['get'])
    def engines(self, request):
        """Get available TTS engines"""
        engines = VoiceProfile.objects.values_list('engine', flat=True).distinct()
        return Response({'engines': list(engines)})

    @action(detail=False, methods=['get'])
    def languages(self, request):
        """Get available languages"""
        languages = VoiceProfile.objects.values_list('language', flat=True).distinct()
        return Response({'languages': list(languages)})


class AvatarProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AI influencer avatar projects
    """
    serializer_class = AvatarProjectSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return AvatarProject.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateAvatarProjectSerializer
        return AvatarProjectSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create new avatar project and start processing"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Check user credits
        user = request.user
        estimated_cost = serializer.validated_data.get('estimated_credits_cost', 5)

        if hasattr(user, 'credits') and user.credits.credits_remaining < estimated_cost:
            return Response(
                {'error': f'Insufficient credits. Need {estimated_cost}, have {user.credits.credits_remaining}'},
                status=status.HTTP_402_PAYMENT_REQUIRED
            )

        # Create project
        project = serializer.save(user=user)

        # Deduct credits
        if hasattr(user, 'credits'):
            user.credits.credits_remaining -= estimated_cost
            user.credits.save()

        # Start TTS processing
        process_tts_only.delay(project.id)

        response_serializer = AvatarProjectSerializer(project)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry failed project processing"""
        project = self.get_object()

        if project.status != 'failed':
            return Response(
                {'error': 'Can only retry failed projects'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reset project status
        project.status = 'pending'
        project.progress_percentage = 0
        project.error_message = None
        project.save()

        # Start TTS processing
        process_tts_only.delay(project.id)

        serializer = self.get_serializer(project)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get project processing status"""
        project = self.get_object()

        return Response({
            'id': project.id,
            'status': project.status,
            'progress_percentage': project.progress_percentage,
            'error_message': project.error_message,
            'created_at': project.created_at,
            'completed_at': project.completed_at,
            'video_url': project.final_video.url if project.final_video else None,
            'thumbnail_url': project.thumbnail.url if project.thumbnail else None,
        })

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """Get project processing logs"""
        project = self.get_object()
        logs = project.processing_logs.all()

        return Response({
            'logs': [
                {
                    'step': log.step,
                    'status': log.status,
                    'message': log.message,
                    'processing_time': log.processing_time,
                    'created_at': log.created_at,
                }
                for log in logs
            ]
        })

    @action(detail=False, methods=['post'])
    def estimate_cost(self, request):
        """Estimate credits cost for a project"""
        script = request.data.get('script', '')
        video_quality = request.data.get('video_quality', '1080p')

        if not script:
            return Response(
                {'error': 'Script is required for cost estimation'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate estimated cost
        base_cost = 5
        script_length_multiplier = len(script) / 100
        quality_multiplier = 1.5 if video_quality == '1080p' else 1.0

        estimated_cost = max(1, int(base_cost + script_length_multiplier * quality_multiplier))

        return Response({
            'estimated_cost': estimated_cost,
            'script_length': len(script),
            'base_cost': base_cost,
            'quality_multiplier': quality_multiplier,
        })

    @action(detail=False, methods=['get'])
    def settings(self, request):
        """Get available settings for avatar projects"""
        tts_service = TTSService()

        return Response({
            'aspect_ratios': [
                {'value': '16:9', 'label': 'Landscape (16:9)'},
                {'value': '9:16', 'label': 'Portrait/TikTok (9:16)'},
                {'value': '1:1', 'label': 'Square (1:1)'},
            ],
            'video_qualities': [
                {'value': '720p', 'label': '720p HD'},
                {'value': '1080p', 'label': '1080p Full HD'},
            ],
            'lip_sync_models': [
                {'value': 'wav2lip', 'label': 'Wav2Lip'},
                {'value': 'wav2lipv2', 'label': 'Wav2Lip v2 (Recommended)'},
                {'value': 'sadtalker', 'label': 'SadTalker'},
            ],
            'supported_engines': tts_service.supported_engines,
        })
