from django.db import models
from django.conf import settings
from django.utils import timezone

class ContentTemplate(models.Model):
    """Templates for different types of content generation"""

    TEMPLATE_TYPES = [
        ('blog_post', 'Blog Post'),
        ('show_notes', 'Show Notes'),
        ('social_media', 'Social Media Post'),
        ('video_description', 'Video Description'),
        ('email_newsletter', 'Email Newsletter'),
        ('transcript', 'Transcript'),
        ('summary', 'Summary'),
        ('key_takeaways', 'Key Takeaways'),
        ('seo_article', 'SEO Article'),
        ('course_outline', 'Course Outline'),
    ]

    PLATFORM_CHOICES = [
        ('general', 'General'),
        ('youtube', 'YouTube'),
        ('tiktok', 'TikTok'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter/X'),
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
        ('wordpress', 'WordPress'),
        ('medium', 'Medium'),
        ('substack', 'Substack'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='general')

    # Template content structure
    prompt_template = models.TextField(help_text="AI prompt template with placeholders")
    output_structure = models.JSONField(default=dict, help_text="Expected output structure")

    # Configuration
    max_words = models.IntegerField(default=1000, help_text="Maximum word count")
    min_words = models.IntegerField(default=100, help_text="Minimum word count")
    tone = models.CharField(max_length=50, default='professional')
    style = models.CharField(max_length=50, default='informative')

    # SEO settings (for blog posts and articles)
    include_seo_meta = models.BooleanField(default=False)
    target_keywords = models.JSONField(default=list, blank=True)
    include_headings = models.BooleanField(default=True)
    include_bullet_points = models.BooleanField(default=True)

    # System fields
    is_built_in = models.BooleanField(default=True, help_text="Built-in system template")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_type', 'name']
        unique_together = ['name', 'template_type', 'platform']

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class ContentGenerationRequest(models.Model):
    """Track content generation requests from videos"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Normal'),
        (3, 'High'),
        (4, 'Urgent'),
    ]

    # Basic info
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    video_request = models.ForeignKey('core.VideoRequest', on_delete=models.CASCADE, related_name='content_requests')

    # Template and configuration
    template = models.ForeignKey(ContentTemplate, on_delete=models.CASCADE)
    custom_instructions = models.TextField(blank=True, help_text="Additional user instructions")

    # Content targeting
    target_audience = models.CharField(max_length=200, blank=True)
    brand_voice = models.CharField(max_length=100, blank=True)
    custom_keywords = models.JSONField(default=list, blank=True)

    # Processing info
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processing_time_seconds = models.FloatField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)

    # Metadata
    ai_model_used = models.CharField(max_length=50, blank=True)
    tokens_used = models.IntegerField(default=0)
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'priority', 'created_at']),
        ]

    def __str__(self):
        return f"Content Generation: {self.template.name} for {self.video_request.url}"

    @property
    def estimated_completion_time(self):
        """Estimate completion time based on queue position and complexity"""
        if self.status == 'completed':
            return None

        # Simple estimation logic
        base_time = 2  # 2 minutes base
        if self.template.max_words > 1500:
            base_time += 3
        if self.template.include_seo_meta:
            base_time += 2

        return base_time


class GeneratedContent(models.Model):
    """Store generated content results"""

    CONTENT_FORMATS = [
        ('markdown', 'Markdown'),
        ('html', 'HTML'),
        ('plain_text', 'Plain Text'),
        ('json', 'JSON'),
    ]

    # Relationships
    content_request = models.OneToOneField(ContentGenerationRequest, on_delete=models.CASCADE, related_name='generated_content')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Content data
    title = models.CharField(max_length=500, blank=True)
    content = models.TextField()
    format = models.CharField(max_length=20, choices=CONTENT_FORMATS, default='markdown')

    # SEO metadata (for SEO content types)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    headings = models.JSONField(default=list, blank=True)

    # Social media specific fields
    hashtags = models.JSONField(default=list, blank=True)
    mentions = models.JSONField(default=list, blank=True)
    call_to_action = models.CharField(max_length=200, blank=True)

    # Analytics and metrics
    word_count = models.IntegerField(default=0)
    reading_time_minutes = models.FloatField(default=0.0)
    readability_score = models.FloatField(null=True, blank=True)

    # Quality metrics
    ai_confidence_score = models.FloatField(default=0.0, help_text="AI confidence in content quality (0-1)")
    user_rating = models.IntegerField(null=True, blank=True, help_text="User rating 1-5")

    # Versioning
    version = models.IntegerField(default=1)
    is_latest = models.BooleanField(default=True)

    # Publishing info
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_url = models.URLField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_published']),
            models.Index(fields=['content_request', 'version']),
        ]

    def __str__(self):
        return f"{self.title or 'Generated Content'} (v{self.version})"

    def save(self, *args, **kwargs):
        # Calculate word count
        if self.content:
            self.word_count = len(self.content.split())
            self.reading_time_minutes = max(1, self.word_count / 200)  # Average reading speed

        super().save(*args, **kwargs)

    @property
    def estimated_reading_time(self):
        """Human-readable reading time"""
        if self.reading_time_minutes < 1:
            return "Less than 1 minute"
        elif self.reading_time_minutes < 60:
            return f"{int(self.reading_time_minutes)} minute{'s' if self.reading_time_minutes > 1 else ''}"
        else:
            hours = int(self.reading_time_minutes // 60)
            minutes = int(self.reading_time_minutes % 60)
            return f"{hours}h {minutes}m"


class ContentGenerationUsage(models.Model):
    """Track content generation usage for billing and analytics"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content_request = models.ForeignKey(ContentGenerationRequest, on_delete=models.CASCADE)

    # Usage metrics
    tokens_consumed = models.IntegerField(default=0)
    processing_time_seconds = models.FloatField(default=0.0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)

    # Plan and billing info
    plan_type = models.CharField(max_length=20, default='free')
    credits_used = models.IntegerField(default=1)

    # Metadata
    ai_model = models.CharField(max_length=50, default='gpt-3.5-turbo')
    template_type = models.CharField(max_length=20)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['plan_type', 'created_at']),
        ]

    def __str__(self):
        return f"Usage: {self.user.email} - {self.template_type} ({self.credits_used} credits)"


class PublishingIntegration(models.Model):
    """Track publishing to external platforms"""

    PLATFORM_CHOICES = [
        ('wordpress', 'WordPress'),
        ('medium', 'Medium'),
        ('substack', 'Substack'),
        ('linkedin', 'LinkedIn'),
        ('twitter', 'Twitter/X'),
        ('facebook', 'Facebook'),
        ('custom_webhook', 'Custom Webhook'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('publishing', 'Publishing'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    generated_content = models.ForeignKey(GeneratedContent, on_delete=models.CASCADE, related_name='publications')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    # Publishing details
    scheduled_for = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_url = models.URLField(blank=True)
    platform_post_id = models.CharField(max_length=100, blank=True)

    # Platform-specific settings
    platform_settings = models.JSONField(default=dict, blank=True)

    # Results
    error_message = models.TextField(blank=True)
    analytics_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'platform', 'status']),
            models.Index(fields=['scheduled_for']),
        ]

    def __str__(self):
        return f"Publishing: {self.generated_content.title} to {self.get_platform_display()}"
