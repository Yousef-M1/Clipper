from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from core import models

class UserAdmin(BaseUserAdmin):
    """Define the admin pages for users."""
    ordering = ['id']
    list_display = ['email', 'first_name', 'last_name', 'is_staff']
    list_filter = ['is_staff', 'is_active']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (
            _('Permissions'),
              {
                  'fields': (
                      'is_active',
                        'is_staff',
                          'is_superuser')}),
        (_('Important dates'), {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

    readonly_fields = ['last_login']
    search_fields = ['email']
    ordering = ['email']
admin.site.register(models.User, UserAdmin)


# Queue Management Admin
@admin.register(models.ProcessingQueue)
class ProcessingQueueAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'video_request', 'user', 'priority_badge', 'status_badge',
        'queue_position', 'queued_at', 'estimated_wait_time', 'actual_duration'
    ]
    list_filter = ['status', 'priority', 'queued_at']
    search_fields = ['user__email', 'video_request__url']
    readonly_fields = ['queued_at', 'started_at', 'completed_at', 'queue_position', 'estimated_wait_time']
    ordering = ['-priority', 'queued_at']

    def priority_badge(self, obj):
        color = obj.get_priority_display_color()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'

    def status_badge(self, obj):
        colors = {
            'queued': '#orange',
            'processing': '#blue',
            'completed': '#green',
            'failed': '#red',
            'cancelled': '#gray'
        }
        color = colors.get(obj.status, '#gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    actions = ['cancel_selected', 'retry_selected']

    def cancel_selected(self, request, queryset):
        from core.queue_manager import QueueManager
        cancelled = 0
        for queue_entry in queryset:
            if QueueManager.cancel_task(queue_entry):
                cancelled += 1
        self.message_user(request, f'Cancelled {cancelled} tasks.')
    cancel_selected.short_description = 'Cancel selected tasks'

    def retry_selected(self, request, queryset):
        from core.queue_manager import QueueManager
        retried = 0
        for queue_entry in queryset:
            if QueueManager.retry_failed_task(queue_entry):
                retried += 1
        self.message_user(request, f'Retried {retried} tasks.')
    retry_selected.short_description = 'Retry selected failed tasks'


@admin.register(models.QueueStats)
class QueueStatsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_processed', 'total_failed', 'avg_processing_time',
        'max_queue_length', 'free_users_processed', 'pro_users_processed', 'premium_users_processed'
    ]
    list_filter = ['date']
    readonly_fields = ['date', 'created_at', 'updated_at']
    ordering = ['-date']


@admin.register(models.NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'event_type', 'notification_type', 'status', 'recipient', 'created_at']
    list_filter = ['event_type', 'notification_type', 'status', 'created_at']
    search_fields = ['user__email', 'recipient', 'subject']
    readonly_fields = ['created_at', 'sent_at']
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False  # Don't allow manual creation of notifications
