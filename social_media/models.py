"""
Social Media Publishing Models
Handles social platform connections, scheduled posts, and analytics
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid

User = get_user_model()


class SocialPlatform(models.Model):
    """Supported social media platforms"""

    PLATFORM_CHOICES = [
        ('tiktok', 'TikTok'),
        ('instagram', 'Instagram'),
        ('youtube', 'YouTube'),
        ('twitter', 'Twitter/X'),
        ('facebook', 'Facebook'),
        ('linkedin', 'LinkedIn'),
    ]

    name = models.CharField(max_length=20, choices=PLATFORM_CHOICES, unique=True)
    display_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    api_version = models.CharField(max_length=10, default='v1')

    # Platform-specific settings
    max_video_duration = models.IntegerField(help_text="Maximum video duration in seconds")
    max_file_size_mb = models.FloatField(help_text="Maximum file size in MB")
    supported_formats = models.JSONField(default=list)  # ['mp4', 'mov', etc.]
    aspect_ratios = models.JSONField(default=list)  # ['9:16', '1:1', etc.]

    # API capabilities
    supports_scheduling = models.BooleanField(default=True)
    supports_analytics = models.BooleanField(default=True)
    supports_captions = models.BooleanField(default=True)
    supports_hashtags = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

    class Meta:
        ordering = ['display_name']


class SocialAccount(models.Model):
    """User's connected social media accounts"""

    STATUS_CHOICES = [
        ('connected', 'Connected'),
        ('expired', 'Token Expired'),
        ('error', 'Connection Error'),
        ('disconnected', 'Disconnected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    platform = models.ForeignKey(SocialPlatform, on_delete=models.CASCADE)

    # Account info
    account_id = models.CharField(max_length=100)  # Platform-specific user ID
    username = models.CharField(max_length=100)
    display_name = models.CharField(max_length=200, blank=True)
    profile_picture = models.URLField(blank=True)

    # Authentication
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    scope = models.TextField(blank=True)  # OAuth scopes

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='connected')
    last_used = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Metadata
    follower_count = models.IntegerField(default=0)
    is_business_account = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.platform.display_name} (@{self.username})"

    def is_token_expired(self):
        """Check if access token is expired"""
        if not self.token_expires_at:
            return False
        return timezone.now() > self.token_expires_at

    def needs_refresh(self):
        """Check if token needs refresh (expires within 1 hour)"""
        if not self.token_expires_at:
            return False
        return timezone.now() > (self.token_expires_at - timedelta(hours=1))

    class Meta:
        unique_together = ['user', 'platform', 'account_id']
        ordering = ['-created_at']


class ScheduledPost(models.Model):
    """Scheduled social media posts"""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('posting', 'Posting'),
        ('posted', 'Posted'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Normal'),
        (3, 'High'),
        (4, 'Urgent'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_posts')
    social_account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE)

    # Content
    video_file = models.FileField(upload_to='social_posts/', null=True, blank=True)
    video_url = models.URLField(blank=True)  # For processed clips
    thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)

    # Post details
    caption = models.TextField(blank=True)
    hashtags = models.JSONField(default=list)  # List of hashtags
    mentions = models.JSONField(default=list)  # List of @mentions

    # Scheduling
    scheduled_time = models.DateTimeField()
    timezone_name = models.CharField(max_length=50, default='UTC')

    # Status & tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)

    # Platform response
    platform_post_id = models.CharField(max_length=100, blank=True)
    platform_url = models.URLField(blank=True)
    platform_response = models.JSONField(default=dict)

    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)

    # Metadata
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.social_account.platform.display_name} - {self.scheduled_time}"

    def can_retry(self):
        """Check if post can be retried"""
        return self.status == 'failed' and self.retry_count < self.max_retries

    def is_due(self):
        """Check if post is due for posting"""
        return (
            self.status == 'scheduled' and
            timezone.now() >= self.scheduled_time
        )

    class Meta:
        ordering = ['scheduled_time']
        indexes = [
            models.Index(fields=['status', 'scheduled_time']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['social_account', 'status']),
        ]


class PostTemplate(models.Model):
    """Reusable post templates"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_templates')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Template settings
    caption_template = models.TextField(blank=True, help_text="Use {variables} for dynamic content")
    hashtags = models.JSONField(default=list)
    default_platforms = models.ManyToManyField(SocialPlatform, blank=True)

    # Scheduling defaults
    default_time_offset = models.IntegerField(default=0, help_text="Minutes from now")
    post_frequency = models.CharField(max_length=20, blank=True)  # daily, weekly, etc.

    # Usage stats
    usage_count = models.IntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.name}"

    class Meta:
        ordering = ['-last_used', 'name']


class PostAnalytics(models.Model):
    """Analytics for posted content"""

    scheduled_post = models.OneToOneField(ScheduledPost, on_delete=models.CASCADE, related_name='analytics')

    # Engagement metrics
    views = models.BigIntegerField(default=0)
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)

    # Reach metrics
    reach = models.BigIntegerField(default=0)
    impressions = models.BigIntegerField(default=0)
    engagement_rate = models.FloatField(default=0.0)

    # Platform-specific metrics
    platform_metrics = models.JSONField(default=dict)

    # Tracking
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_engagement_rate(self):
        """Calculate engagement rate"""
        if self.impressions > 0:
            total_engagement = self.likes + self.comments + self.shares + self.saves
            self.engagement_rate = (total_engagement / self.impressions) * 100
        return self.engagement_rate

    class Meta:
        ordering = ['-created_at']


class ContentCalendar(models.Model):
    """Content calendar for planning posts"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='content_calendars')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Calendar settings
    start_date = models.DateField()
    end_date = models.DateField()
    timezone_name = models.CharField(max_length=50, default='UTC')

    # Posting schedule
    posting_times = models.JSONField(default=list)  # List of time strings
    post_frequency = models.JSONField(default=dict)  # Platform-specific frequencies

    # Content themes
    themes = models.JSONField(default=list)  # Weekly/daily themes

    # Status
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.name}"

    class Meta:
        ordering = ['-created_at']


class WebhookEvent(models.Model):
    """Track webhook events from social platforms"""

    EVENT_TYPES = [
        ('post_published', 'Post Published'),
        ('post_failed', 'Post Failed'),
        ('analytics_update', 'Analytics Update'),
        ('account_deauthorized', 'Account Deauthorized'),
        ('rate_limit_exceeded', 'Rate Limit Exceeded'),
    ]

    social_account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE, related_name='webhook_events')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)

    # Event data
    platform_event_id = models.CharField(max_length=100, blank=True)
    event_data = models.JSONField(default=dict)

    # Processing
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.social_account} - {self.event_type}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['processed', 'created_at']),
            models.Index(fields=['social_account', 'event_type']),
        ]