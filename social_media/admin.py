"""
Django admin interface for social media publishing
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    SocialPlatform, SocialAccount, ScheduledPost,
    PostTemplate, PostAnalytics, ContentCalendar, WebhookEvent
)


@admin.register(SocialPlatform)
class SocialPlatformAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'name', 'is_active', 'max_video_duration',
        'max_file_size_mb', 'supports_scheduling', 'supports_analytics'
    ]
    list_filter = ['is_active', 'supports_scheduling', 'supports_analytics']
    search_fields = ['name', 'display_name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'display_name', 'is_active', 'api_version')
        }),
        ('Capabilities', {
            'fields': (
                'max_video_duration', 'max_file_size_mb', 'supported_formats',
                'aspect_ratios', 'supports_scheduling', 'supports_analytics',
                'supports_captions', 'supports_hashtags'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = [
        'user_email', 'platform', 'username', 'status_badge',
        'follower_count', 'is_business_account', 'last_used', 'created_at'
    ]
    list_filter = [
        'platform', 'status', 'is_business_account', 'is_verified', 'created_at'
    ]
    search_fields = ['user__email', 'username', 'display_name']
    readonly_fields = [
        'account_id', 'token_expires_at', 'last_used',
        'created_at', 'updated_at', 'token_status'
    ]

    fieldsets = (
        ('User & Platform', {
            'fields': ('user', 'platform', 'account_id')
        }),
        ('Account Info', {
            'fields': (
                'username', 'display_name', 'profile_picture',
                'follower_count', 'is_business_account', 'is_verified'
            )
        }),
        ('Authentication', {
            'fields': ('status', 'token_status', 'token_expires_at', 'scope'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('last_used', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'

    def status_badge(self, obj):
        colors = {
            'connected': '#green',
            'expired': '#orange',
            'error': '#red',
            'disconnected': '#gray'
        }
        color = colors.get(obj.status, '#gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def token_status(self, obj):
        if obj.is_token_expired():
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.needs_refresh():
            return format_html('<span style="color: orange;">Needs Refresh</span>')
        else:
            return format_html('<span style="color: green;">Valid</span>')
    token_status.short_description = 'Token Status'

    actions = ['refresh_tokens', 'disconnect_accounts']

    def refresh_tokens(self, request, queryset):
        """Admin action to refresh tokens"""
        from .services import SocialMediaPublishingService

        refreshed = 0
        for account in queryset.filter(status='connected'):
            try:
                SocialMediaPublishingService.refresh_account_token(account)
                refreshed += 1
            except Exception:
                pass

        self.message_user(request, f'Refreshed {refreshed} tokens')
    refresh_tokens.short_description = 'Refresh access tokens'

    def disconnect_accounts(self, request, queryset):
        """Admin action to disconnect accounts"""
        count = queryset.update(status='disconnected')
        self.message_user(request, f'Disconnected {count} accounts')
    disconnect_accounts.short_description = 'Disconnect selected accounts'


@admin.register(ScheduledPost)
class ScheduledPostAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_email', 'platform', 'status_badge', 'scheduled_time',
        'priority', 'posted_at', 'retry_count', 'has_analytics'
    ]
    list_filter = [
        'status', 'priority', 'social_account__platform',
        'scheduled_time', 'posted_at', 'created_at'
    ]
    search_fields = [
        'user__email', 'caption', 'social_account__username',
        'platform_post_id'
    ]
    readonly_fields = [
        'id', 'platform_post_id', 'platform_url', 'platform_response',
        'posted_at', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'social_account', 'status', 'priority')
        }),
        ('Content', {
            'fields': (
                'video_file', 'video_url', 'thumbnail', 'caption',
                'hashtags', 'mentions'
            )
        }),
        ('Scheduling', {
            'fields': ('scheduled_time', 'timezone_name')
        }),
        ('Publishing Results', {
            'fields': (
                'platform_post_id', 'platform_url', 'platform_response',
                'posted_at'
            ),
            'classes': ('collapse',)
        }),
        ('Error Handling', {
            'fields': ('error_message', 'retry_count', 'max_retries'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'

    def platform(self, obj):
        return obj.social_account.platform.display_name
    platform.short_description = 'Platform'

    def status_badge(self, obj):
        colors = {
            'draft': '#gray',
            'scheduled': '#blue',
            'posting': '#orange',
            'posted': '#green',
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

    def has_analytics(self, obj):
        return hasattr(obj, 'analytics')
    has_analytics.boolean = True
    has_analytics.short_description = 'Analytics'

    actions = ['publish_now', 'cancel_posts', 'retry_failed']

    def publish_now(self, request, queryset):
        """Admin action to publish posts immediately"""
        from .tasks import publish_single_post

        published = 0
        for post in queryset.filter(status__in=['draft', 'scheduled']):
            publish_single_post.apply_async(args=[post.id])
            published += 1

        self.message_user(request, f'Queued {published} posts for immediate publishing')
    publish_now.short_description = 'Publish selected posts now'

    def cancel_posts(self, request, queryset):
        """Admin action to cancel posts"""
        count = queryset.filter(status__in=['draft', 'scheduled']).update(status='cancelled')
        self.message_user(request, f'Cancelled {count} posts')
    cancel_posts.short_description = 'Cancel selected posts'

    def retry_failed(self, request, queryset):
        """Admin action to retry failed posts"""
        from .tasks import publish_single_post

        retried = 0
        for post in queryset.filter(status='failed'):
            if post.can_retry():
                post.status = 'scheduled'
                post.save()
                publish_single_post.apply_async(args=[post.id], countdown=60)
                retried += 1

        self.message_user(request, f'Queued {retried} failed posts for retry')
    retry_failed.short_description = 'Retry failed posts'


@admin.register(PostAnalytics)
class PostAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'post_id', 'platform', 'views', 'likes', 'comments',
        'engagement_rate', 'last_updated'
    ]
    list_filter = ['scheduled_post__social_account__platform', 'last_updated']
    search_fields = [
        'scheduled_post__user__email',
        'scheduled_post__caption',
        'scheduled_post__platform_post_id'
    ]
    readonly_fields = ['scheduled_post', 'created_at', 'last_updated']

    def post_id(self, obj):
        return str(obj.scheduled_post.id)[:8] + '...'
    post_id.short_description = 'Post ID'

    def platform(self, obj):
        return obj.scheduled_post.social_account.platform.display_name
    platform.short_description = 'Platform'


@admin.register(PostTemplate)
class PostTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user_email', 'usage_count', 'last_used', 'created_at'
    ]
    list_filter = ['post_frequency', 'last_used', 'created_at']
    search_fields = ['name', 'user__email', 'description']
    readonly_fields = ['usage_count', 'last_used', 'created_at', 'updated_at']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'


@admin.register(ContentCalendar)
class ContentCalendarAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user_email', 'start_date', 'end_date',
        'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'start_date', 'created_at']
    search_fields = ['name', 'user__email', 'description']
    readonly_fields = ['created_at', 'updated_at']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = [
        'social_account', 'event_type', 'processed', 'created_at'
    ]
    list_filter = [
        'event_type', 'processed', 'social_account__platform', 'created_at'
    ]
    search_fields = [
        'social_account__user__email',
        'platform_event_id'
    ]
    readonly_fields = ['created_at', 'processed_at']

    actions = ['mark_processed', 'reprocess_events']

    def mark_processed(self, request, queryset):
        """Mark events as processed"""
        count = queryset.update(processed=True)
        self.message_user(request, f'Marked {count} events as processed')
    mark_processed.short_description = 'Mark as processed'

    def reprocess_events(self, request, queryset):
        """Reprocess webhook events"""
        from .tasks import process_webhook_events

        queryset.update(processed=False, error_message='', processed_at=None)
        process_webhook_events.apply_async(countdown=30)

        self.message_user(request, f'Queued {queryset.count()} events for reprocessing')
    reprocess_events.short_description = 'Reprocess selected events'