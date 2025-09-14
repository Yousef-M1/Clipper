"""
Django REST Framework serializers for social media publishing
"""

from rest_framework import serializers
from .models import (
    SocialPlatform, SocialAccount, ScheduledPost,
    PostTemplate, PostAnalytics, ContentCalendar
)


class SocialPlatformSerializer(serializers.ModelSerializer):
    """Serializer for social media platforms"""

    class Meta:
        model = SocialPlatform
        fields = [
            'id', 'name', 'display_name', 'max_video_duration',
            'max_file_size_mb', 'supported_formats', 'aspect_ratios',
            'supports_scheduling', 'supports_analytics', 'supports_captions',
            'supports_hashtags'
        ]


class SocialAccountSerializer(serializers.ModelSerializer):
    """Serializer for connected social media accounts"""

    platform = SocialPlatformSerializer(read_only=True)
    is_token_expired = serializers.BooleanField(read_only=True)
    needs_refresh = serializers.BooleanField(read_only=True)

    class Meta:
        model = SocialAccount
        fields = [
            'id', 'platform', 'account_id', 'username', 'display_name',
            'profile_picture', 'status', 'last_used', 'follower_count',
            'is_business_account', 'is_verified', 'is_token_expired',
            'needs_refresh', 'created_at', 'updated_at'
        ]


class ScheduledPostSerializer(serializers.ModelSerializer):
    """Serializer for scheduled posts"""

    platform = serializers.CharField(source='social_account.platform.display_name', read_only=True)
    account_username = serializers.CharField(source='social_account.username', read_only=True)
    can_retry = serializers.BooleanField(read_only=True)
    is_due = serializers.BooleanField(read_only=True)
    has_analytics = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledPost
        fields = [
            'id', 'platform', 'account_username', 'video_url', 'caption',
            'hashtags', 'mentions', 'scheduled_time', 'status', 'priority',
            'platform_post_id', 'platform_url', 'error_message', 'retry_count',
            'max_retries', 'posted_at', 'can_retry', 'is_due', 'has_analytics',
            'created_at', 'updated_at'
        ]

    def get_has_analytics(self, obj):
        """Check if post has analytics data"""
        return hasattr(obj, 'analytics')


class PostAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for post analytics"""

    platform = serializers.CharField(source='scheduled_post.social_account.platform.display_name', read_only=True)
    post_caption = serializers.CharField(source='scheduled_post.caption', read_only=True)
    posted_at = serializers.DateTimeField(source='scheduled_post.posted_at', read_only=True)

    class Meta:
        model = PostAnalytics
        fields = [
            'platform', 'post_caption', 'posted_at', 'views', 'likes',
            'comments', 'shares', 'saves', 'reach', 'impressions',
            'engagement_rate', 'platform_metrics', 'last_updated', 'created_at'
        ]


class PostTemplateSerializer(serializers.ModelSerializer):
    """Serializer for post templates"""

    class Meta:
        model = PostTemplate
        fields = [
            'id', 'name', 'description', 'caption_template', 'hashtags',
            'default_time_offset', 'post_frequency', 'usage_count',
            'last_used', 'created_at', 'updated_at'
        ]


class ContentCalendarSerializer(serializers.ModelSerializer):
    """Serializer for content calendars"""

    class Meta:
        model = ContentCalendar
        fields = [
            'id', 'name', 'description', 'start_date', 'end_date',
            'timezone_name', 'posting_times', 'post_frequency', 'themes',
            'is_active', 'created_at', 'updated_at'
        ]


class SchedulePostRequestSerializer(serializers.Serializer):
    """Serializer for schedule post requests"""

    social_account_id = serializers.IntegerField()
    scheduled_time = serializers.DateTimeField()
    video_url = serializers.URLField()
    caption = serializers.CharField(max_length=2200, allow_blank=True)
    hashtags = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        allow_empty=True
    )
    mentions = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        allow_empty=True
    )
    priority = serializers.IntegerField(min_value=1, max_value=4, required=False, default=2)

    def validate_scheduled_time(self, value):
        """Validate that scheduled time is in the future"""
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future")
        return value


class ConnectAccountRequestSerializer(serializers.Serializer):
    """Serializer for connecting social media accounts"""

    platform = serializers.CharField(max_length=20)
    auth_code = serializers.CharField(max_length=500)
    redirect_uri = serializers.URLField(required=False)

    def validate_platform(self, value):
        """Validate that platform is supported"""
        supported_platforms = ['tiktok', 'instagram', 'youtube', 'twitter', 'facebook', 'linkedin']
        if value not in supported_platforms:
            raise serializers.ValidationError(f"Platform must be one of: {', '.join(supported_platforms)}")
        return value


class BulkScheduleSerializer(serializers.Serializer):
    """Serializer for bulk scheduling posts"""

    posts = serializers.ListField(
        child=SchedulePostRequestSerializer(),
        min_length=1,
        max_length=50  # Limit bulk operations
    )
    template_id = serializers.IntegerField(required=False)

    def validate_posts(self, value):
        """Validate that all posts have different scheduled times"""
        scheduled_times = [post['scheduled_time'] for post in value]
        if len(scheduled_times) != len(set(scheduled_times)):
            raise serializers.ValidationError("All posts must have unique scheduled times")
        return value


class ContentSuggestionSerializer(serializers.Serializer):
    """Serializer for content suggestions"""

    type = serializers.CharField()
    title = serializers.CharField()
    data = serializers.JSONField()
    confidence = serializers.FloatField(min_value=0.0, max_value=1.0, default=0.8)
    action = serializers.CharField(required=False)


class DashboardSummarySerializer(serializers.Serializer):
    """Serializer for dashboard summary data"""

    connected_accounts = serializers.IntegerField()
    accounts_by_platform = serializers.DictField()
    total_posts = serializers.IntegerField()
    posts_by_status = serializers.DictField()
    top_performing_posts = ScheduledPostSerializer(many=True, required=False)
    upcoming_posts = ScheduledPostSerializer(many=True, required=False)
    suggestions = ContentSuggestionSerializer(many=True, required=False)