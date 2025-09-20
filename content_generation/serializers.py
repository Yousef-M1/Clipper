from rest_framework import serializers
from .models import (
    ContentTemplate, ContentGenerationRequest, GeneratedContent,
    ContentGenerationUsage, PublishingIntegration
)

class ContentTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentTemplate
        fields = [
            'id', 'name', 'description', 'template_type', 'platform',
            'max_words', 'min_words', 'tone', 'style',
            'include_seo_meta', 'target_keywords', 'include_headings',
            'include_bullet_points', 'is_built_in', 'created_at'
        ]
        read_only_fields = ['id', 'is_built_in', 'created_at']

class ContentGenerationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentGenerationRequest
        fields = [
            'id', 'user', 'video_request', 'template', 'custom_instructions',
            'target_audience', 'brand_voice', 'custom_keywords',
            'status', 'priority', 'created_at', 'completed_at',
            'processing_time_seconds', 'error_message', 'ai_model_used',
            'tokens_used', 'cost_estimate'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'created_at', 'completed_at',
            'processing_time_seconds', 'error_message', 'ai_model_used',
            'tokens_used', 'cost_estimate'
        ]

class GeneratedContentSerializer(serializers.ModelSerializer):
    estimated_reading_time = serializers.ReadOnlyField()

    class Meta:
        model = GeneratedContent
        fields = [
            'id', 'content_request', 'user', 'title', 'content', 'format',
            'meta_title', 'meta_description', 'keywords', 'headings',
            'hashtags', 'mentions', 'call_to_action',
            'word_count', 'reading_time_minutes', 'estimated_reading_time',
            'readability_score', 'ai_confidence_score', 'user_rating',
            'version', 'is_latest', 'is_published', 'published_at',
            'published_url', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'word_count', 'reading_time_minutes',
            'estimated_reading_time', 'ai_confidence_score',
            'version', 'created_at', 'updated_at'
        ]

class ContentGenerationUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentGenerationUsage
        fields = [
            'id', 'user', 'content_request', 'tokens_consumed',
            'processing_time_seconds', 'cost_usd', 'plan_type',
            'credits_used', 'ai_model', 'template_type', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class PublishingIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishingIntegration
        fields = [
            'id', 'generated_content', 'user', 'platform', 'status',
            'scheduled_for', 'published_at', 'published_url',
            'platform_post_id', 'platform_settings', 'error_message',
            'analytics_data', 'created_at'
        ]
        read_only_fields = [
            'id', 'user', 'published_at', 'platform_post_id',
            'error_message', 'analytics_data', 'created_at'
        ]