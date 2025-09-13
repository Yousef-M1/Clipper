# clipper/serializers.py
from rest_framework import serializers
from core.models import VideoRequest, CaptionSettings, Clip


class ClipSerializer(serializers.ModelSerializer):
    """Enhanced Clip serializer with new fields"""

    class Meta:
        model = Clip
        fields = [
            'id', 'video_request', 'start_time', 'end_time', 'duration',
            'caption_style', 'status', 'file_path', 'format',
            # New enhanced fields
            'detection_method', 'engagement_score', 'moment_reason', 'moment_tags',
            'video_quality', 'file_size_mb', 'compression_level',
            'used_caption_style', 'has_word_highlighting'
        ]
        read_only_fields = [
            'id', 'detection_method', 'engagement_score', 'moment_reason',
            'moment_tags', 'file_size_mb'
        ]


class CaptionSettingsSerializer(serializers.ModelSerializer):
    """Keep your existing CaptionSettings serializer"""

    class Meta:
        model = CaptionSettings
        fields = [
            'id', 'video_request', 'style', 'intro_title',
            'font_size', 'font_color', 'animation_style',
            'animation_target', 'per_word', 'hide_punctuation',
            'ai_highlight_keywords', 'rotate_captions'
        ]


class VideoRequestSerializer(serializers.ModelSerializer):
    """Enhanced VideoRequest serializer with processing settings"""
    captions = CaptionSettingsSerializer(required=False)
    clips = ClipSerializer(many=True, read_only=True)

    # Processing settings fields
    processing_settings = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = VideoRequest
        fields = [
            'id', 'url', 'original_language', 'created_at', 'total_clips', 'status',
            # New enhanced fields
            'moment_detection_type', 'video_quality', 'compression_level',
            'caption_style', 'enable_word_highlighting', 'clip_duration', 'max_clips',
            'processing_settings', 'estimated_processing_time',
            # Related fields
            'captions', 'clips'
        ]
        read_only_fields = [
            'created_at', 'total_clips', 'status', 'estimated_processing_time', 'clips'
        ]

    def create(self, validated_data):
        """Enhanced create method to handle processing settings"""
        captions_data = validated_data.pop('captions', None)

        # Extract processing settings and store them
        processing_settings = {
            'moment_detection_type': validated_data.get('moment_detection_type', 'ai_powered'),
            'video_quality': validated_data.get('video_quality', '720p'),
            'compression_level': validated_data.get('compression_level', 'balanced'),
            'caption_style': validated_data.get('caption_style', 'modern_purple'),
            'enable_word_highlighting': validated_data.get('enable_word_highlighting', True),
            'clip_duration': validated_data.get('clip_duration', 30.0),
            'max_clips': validated_data.get('max_clips', 10),
        }
        validated_data['processing_settings'] = processing_settings

        video_request = VideoRequest.objects.create(**validated_data)

        if captions_data:
            CaptionSettings.objects.create(video_request=video_request, **captions_data)

        return video_request

    def update(self, instance, validated_data):
        """Enhanced update method"""
        captions_data = validated_data.pop('captions', None)

        # Update processing settings
        if any(field in validated_data for field in [
            'moment_detection_type', 'video_quality', 'compression_level',
            'caption_style', 'enable_word_highlighting', 'clip_duration', 'max_clips'
        ]):
            processing_settings = instance.processing_settings or {}
            processing_settings.update({
                'moment_detection_type': validated_data.get('moment_detection_type', processing_settings.get('moment_detection_type')),
                'video_quality': validated_data.get('video_quality', processing_settings.get('video_quality')),
                'compression_level': validated_data.get('compression_level', processing_settings.get('compression_level')),
                'caption_style': validated_data.get('caption_style', processing_settings.get('caption_style')),
                'enable_word_highlighting': validated_data.get('enable_word_highlighting', processing_settings.get('enable_word_highlighting')),
                'clip_duration': validated_data.get('clip_duration', processing_settings.get('clip_duration')),
                'max_clips': validated_data.get('max_clips', processing_settings.get('max_clips')),
            })
            validated_data['processing_settings'] = processing_settings

        # Update the instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update captions if provided
        if captions_data:
            captions, created = CaptionSettings.objects.get_or_create(
                video_request=instance,
                defaults=captions_data
            )
            if not created:
                for attr, value in captions_data.items():
                    setattr(captions, attr, value)
                captions.save()

        return instance


class ProcessingSettingsSerializer(serializers.Serializer):
    """Dedicated serializer for processing settings validation"""
    moment_detection_type = serializers.ChoiceField(
        choices=[('ai_powered', 'AI Powered'), ('fixed_intervals', 'Fixed Intervals')],
        default='ai_powered'
    )
    video_quality = serializers.ChoiceField(
        choices=[('480p', '480p'), ('720p', '720p'), ('1080p', '1080p'), ('1440p', '1440p'), ('2160p', '2160p')],
        default='720p'
    )
    compression_level = serializers.ChoiceField(
        choices=[('high_quality', 'High Quality'), ('balanced', 'Balanced'), ('compressed', 'Compressed')],
        default='balanced'
    )
    caption_style = serializers.ChoiceField(
        choices=[
            ('modern_purple', 'Modern Purple'),
            ('tiktok_style', 'TikTok Style'),
            ('youtube_style', 'YouTube Style'),
            ('instagram_story', 'Instagram Story'),
            ('podcast_style', 'Podcast Style')
        ],
        default='modern_purple'
    )
    enable_word_highlighting = serializers.BooleanField(default=True)
    clip_duration = serializers.FloatField(min_value=5.0, max_value=120.0, default=30.0)
    max_clips = serializers.IntegerField(min_value=1, max_value=50, default=10)


class EnhancedVideoRequestSerializer(serializers.ModelSerializer):
    """Specialized serializer for the enhanced create endpoint"""
    processing_settings = ProcessingSettingsSerializer(required=False)

    class Meta:
        model = VideoRequest
        fields = ['id', 'url', 'processing_settings']

    def create(self, validated_data):
        """Create video request with validated processing settings"""
        processing_settings = validated_data.pop('processing_settings', {})

        # Set individual fields from processing settings
        for field, value in processing_settings.items():
            validated_data[field] = value

        # Store the complete processing settings
        validated_data['processing_settings'] = processing_settings

        return VideoRequest.objects.create(**validated_data)


class ClipDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual clip information"""
    video_request_url = serializers.CharField(source='video_request.url', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Clip
        fields = [
            'id', 'start_time', 'end_time', 'duration', 'status', 'format',
            'detection_method', 'engagement_score', 'moment_reason', 'moment_tags',
            'video_quality', 'file_size_mb', 'compression_level',
            'used_caption_style', 'has_word_highlighting',
            'video_request_url', 'download_url'
        ]

    def get_download_url(self, obj):
        """Get the download URL for the clip file"""
        if obj.file_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_path.url)
            return obj.file_path.url
        return None