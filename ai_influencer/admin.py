"""
Admin configuration for AI influencer models
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import AvatarCharacter, VoiceProfile, AvatarProject, ProcessingLog


@admin.register(AvatarCharacter)
class AvatarCharacterAdmin(admin.ModelAdmin):
    """Admin for avatar characters"""
    list_display = ['name', 'gender', 'voice_style', 'is_active', 'created_at']
    list_filter = ['gender', 'voice_style', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


@admin.register(VoiceProfile)
class VoiceProfileAdmin(admin.ModelAdmin):
    """Admin for voice profiles"""
    list_display = ['name', 'language', 'gender', 'engine', 'is_premium', 'is_active']
    list_filter = ['engine', 'language', 'gender', 'is_premium', 'is_active']
    search_fields = ['name', 'voice_id']

    def get_queryset(self, request):
        return super().get_queryset(request)


class ProcessingLogInline(admin.TabularInline):
    """Inline for processing logs"""
    model = ProcessingLog
    readonly_fields = ['step', 'status', 'message', 'processing_time', 'created_at']
    extra = 0


@admin.register(AvatarProject)
class AvatarProjectAdmin(admin.ModelAdmin):
    """Admin for avatar projects"""
    list_display = [
        'title', 'user_email', 'status', 'progress_percentage',
        'video_quality', 'lip_sync_model', 'created_at'
    ]
    list_filter = [
        'status', 'video_quality', 'aspect_ratio', 'lip_sync_model',
        'enable_emotions', 'created_at'
    ]
    search_fields = ['title', 'user__email', 'script']
    readonly_fields = [
        'status', 'progress_percentage', 'error_message', 'video_duration',
        'file_size_mb', 'processing_time', 'created_at', 'updated_at',
        'completed_at', 'estimated_credits_cost'
    ]
    inlines = [ProcessingLogInline]

    fieldsets = (
        ('Project Info', {
            'fields': ('title', 'user', 'script', 'status', 'progress_percentage', 'error_message')
        }),
        ('Avatar Configuration', {
            'fields': ('character', 'custom_avatar_image')
        }),
        ('Voice Configuration', {
            'fields': ('voice', 'voice_speed', 'voice_pitch')
        }),
        ('Video Configuration', {
            'fields': ('aspect_ratio', 'video_quality', 'background_color', 'background_image')
        }),
        ('Processing Settings', {
            'fields': ('lip_sync_model', 'enable_emotions', 'head_movement_intensity')
        }),
        ('Generated Content', {
            'fields': ('generated_audio', 'final_video', 'thumbnail')
        }),
        ('Metadata', {
            'fields': (
                'video_duration', 'file_size_mb', 'processing_time',
                'estimated_credits_cost', 'created_at', 'updated_at', 'completed_at'
            )
        }),
    )

    def user_email(self, obj):
        """Display user email"""
        return obj.user.email
    user_email.short_description = 'User Email'

    def estimated_credits_cost(self, obj):
        """Display estimated credits cost"""
        return obj.estimated_credits_cost
    estimated_credits_cost.short_description = 'Credits Cost'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'character', 'voice')


@admin.register(ProcessingLog)
class ProcessingLogAdmin(admin.ModelAdmin):
    """Admin for processing logs"""
    list_display = ['project_title', 'step', 'status', 'processing_time', 'created_at']
    list_filter = ['status', 'step', 'created_at']
    search_fields = ['project__title', 'step', 'message']
    readonly_fields = ['project', 'step', 'status', 'message', 'processing_time', 'created_at']

    def project_title(self, obj):
        """Display project title"""
        return obj.project.title
    project_title.short_description = 'Project'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project')
