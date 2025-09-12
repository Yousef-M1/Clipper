# clipper/serializers.py
from rest_framework import serializers
from core.models import VideoRequest, CaptionSettings ,  Clip


class ClipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clip
        fields = ['id' , 'video_request', 'start_time', 'end_time', 'duration', 'caption_style', 'status', 'file_path' , 'format']


class CaptionSettingsSerializer(serializers.ModelSerializer):

    class Meta:
        model = CaptionSettings
        fields = [
            'id', 'video_request', 'style', 'intro_title',
            'font_size', 'font_color', 'animation_style',
            'animation_target', 'per_word', 'hide_punctuation',
            'ai_highlight_keywords', 'rotate_captions'
        ]
class VideoRequestSerializer(serializers.ModelSerializer):
    captions = CaptionSettingsSerializer(required=False)  # nested serializer

    class Meta:
        model = VideoRequest
        fields = ['id', 'url', 'original_language', 'created_at', 'total_clips', 'status' , 'captions']
        read_only_fields = ['created_at', 'total_clips', 'status' ,'captions']
    def create(self, validated_data):
        captions_data = validated_data.pop('captions', None)
        video_request = VideoRequest.objects.create(**validated_data)
        if captions_data:
            CaptionSettings.objects.create(video_request=video_request, **captions_data)
        return video_request