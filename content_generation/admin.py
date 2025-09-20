from django.contrib import admin
from .models import (
    ContentTemplate, ContentGenerationRequest, GeneratedContent,
    ContentGenerationUsage, PublishingIntegration
)


@admin.register(ContentTemplate)
class ContentTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'platform', 'is_built_in', 'created_at']
    list_filter = ['template_type', 'platform', 'is_built_in']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ContentGenerationRequest)
class ContentGenerationRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'template', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'template__template_type', 'created_at']
    search_fields = ['user__email', 'template__name']
    readonly_fields = ['created_at', 'started_at', 'completed_at']
    raw_id_fields = ['user', 'video_request']


@admin.register(GeneratedContent)
class GeneratedContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'content_request', 'word_count', 'user_rating', 'is_published', 'created_at']
    list_filter = ['format', 'is_published', 'user_rating', 'created_at']
    search_fields = ['title', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'word_count', 'reading_time_minutes']
    raw_id_fields = ['user', 'content_request']


@admin.register(ContentGenerationUsage)
class ContentGenerationUsageAdmin(admin.ModelAdmin):
    list_display = ['user', 'template_type', 'tokens_consumed', 'cost_usd', 'credits_used', 'created_at']
    list_filter = ['template_type', 'plan_type', 'ai_model', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['created_at']


@admin.register(PublishingIntegration)
class PublishingIntegrationAdmin(admin.ModelAdmin):
    list_display = ['generated_content', 'platform', 'status', 'scheduled_for', 'published_at']
    list_filter = ['platform', 'status', 'scheduled_for']
    search_fields = ['generated_content__title', 'user__email']
    readonly_fields = ['created_at', 'published_at']
