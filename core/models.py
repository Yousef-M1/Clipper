from django.db import models
from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
# Create your models here.

class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and return a new user with an email and password.
        """
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a new superuser with an email and password.
        """

        #  user = self.create_user(email, password)
        # user.is_staff = True
        # user.is_superuser = True
        # user.save(using=self._db)
        # return user
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model that uses email as the unique identifier.
    """
    email = models.EmailField(unique=True ,db_index=True, max_length=255)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

class Plan(models.Model):
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('premium', 'Premium'),
    ]
    name = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    monthly_credits = models.IntegerField(default=75)   # how many credits per month
    credit_per_clip = models.IntegerField(default=1)    # how many credits used per clip

    def __str__(self):
        return self.name

class UserCredits(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    used_credits = models.IntegerField(default=0)
    last_reset = models.DateField(auto_now_add=True)


    @property
    def remaining_credits(self):
        return (self.plan.monthly_credits if self.plan else 0) - self.used_credits

    def use_credits(self, clips_count=1):
        """Deduct credits based on plan's credit_per_clip"""
        cost = clips_count * (self.plan.credit_per_clip if self.plan else 1)
        if self.remaining_credits < cost:
            raise ValueError("Not enough credits!")
        self.used_credits += cost
        self.save()
        return True

    def reset_credits(self):
        """Reset monthly credits"""
        self.used_credits = 0
        self.save()



# Define a Django model named VideoRequest that represents a user's video processing request
class VideoRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    url = models.URLField()
    original_language = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total_clips = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # NEW FIELDS FOR ENHANCED FEATURES
    moment_detection_type = models.CharField(
        max_length=20,
        choices=[('ai_powered', 'AI Powered'), ('fixed_intervals', 'Fixed Intervals')],
        default='ai_powered'
    )
    video_quality = models.CharField(
        max_length=10,
        choices=[('480p', '480p'), ('720p', '720p'), ('1080p', '1080p'), ('1440p', '1440p'), ('2160p', '2160p')],
        default='720p'
    )
    compression_level = models.CharField(
        max_length=15,
        choices=[('high_quality', 'High Quality'), ('balanced', 'Balanced'), ('compressed', 'Compressed')],
        default='balanced'
    )
    caption_style = models.CharField(
        max_length=20,
        choices=[
            ('modern_purple', 'Modern Purple'),
            ('tiktok_style', 'TikTok Style'),
            ('youtube_style', 'YouTube Style'),
            ('instagram_story', 'Instagram Story'),
            ('podcast_style', 'Podcast Style')
        ],
        default='modern_purple'
    )
    enable_word_highlighting = models.BooleanField(default=True)
    clip_duration = models.FloatField(default=30.0)
    max_clips = models.IntegerField(default=10)

    # NEW VIDEO FORMAT FIELDS
    output_format = models.CharField(
        max_length=20,
        choices=[
            ('horizontal', 'Horizontal (16:9)'),
            ('vertical', 'Vertical (9:16)'),
            ('square', 'Square (1:1)'),
            ('custom', 'Custom Aspect Ratio')
        ],
        default='horizontal'
    )
    custom_width = models.IntegerField(null=True, blank=True, help_text="Custom width in pixels")
    custom_height = models.IntegerField(null=True, blank=True, help_text="Custom height in pixels")
    social_platform = models.CharField(
        max_length=20,
        choices=[
            ('youtube', 'YouTube'),
            ('tiktok', 'TikTok'),
            ('instagram_story', 'Instagram Story'),
            ('instagram_post', 'Instagram Post'),
            ('instagram_reel', 'Instagram Reel'),
            ('facebook_post', 'Facebook Post'),
            ('twitter', 'Twitter/X'),
            ('linkedin', 'LinkedIn'),
            ('custom', 'Custom')
        ],
        default='youtube'
    )

    # Metadata fields
    processing_settings = models.JSONField(default=dict, blank=True)  # Store all processing settings
    estimated_processing_time = models.FloatField(null=True, blank=True)  # In minutes

    def __str__(self):
        return f"{self.url} ({self.user.email})"




class Clip(models.Model):
    video_request = models.ForeignKey(VideoRequest, on_delete=models.CASCADE, related_name='clips')
    start_time = models.FloatField()
    end_time = models.FloatField()
    duration = models.FloatField()
    caption_style = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default='pending')
    file_path = models.FileField(upload_to='clips/', blank=True, null=True)
    format = models.CharField(max_length=10, default='mp4')

    # NEW FIELDS FOR ENHANCED FEATURES
    detection_method = models.CharField(
        max_length=20,
        choices=[('ai_detected', 'AI Detected'), ('audio_detected', 'Audio Detected'), ('fixed_interval', 'Fixed Interval')],
        default='fixed_interval'
    )
    engagement_score = models.FloatField(default=5.0)  # AI-determined engagement score (1-10)
    moment_reason = models.TextField(blank=True)  # Why this moment was selected
    moment_tags = models.JSONField(default=list, blank=True)  # Tags like ['educational', 'surprising']

    # Quality and file information
    video_quality = models.CharField(max_length=10, default='720p')
    file_size_mb = models.FloatField(null=True, blank=True)
    compression_level = models.CharField(max_length=15, default='balanced')

    # Caption styling information
    used_caption_style = models.CharField(max_length=20, default='modern_purple')
    has_word_highlighting = models.BooleanField(default=False)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"Clip {self.start_time}s-{self.end_time}s from {self.video_request.id}"

# Define a Django model named CaptionSettings for caption customization options
class CaptionSettings(models.Model):
    # One-to-one relationship with VideoRequest; if video request is deleted, delete these settings too
    video_request = models.OneToOneField(VideoRequest, on_delete=models.CASCADE)

    # Style of the captions, defaults to 'default'
    style = models.CharField(max_length=50, default='default')

    # Optional introductory title text for the captions
    intro_title = models.CharField(max_length=100, blank=True)

    # Font size for captions, defaults to 24
    font_size = models.IntegerField(default=24)

    # Color of the caption text, defaults to 'white'
    font_color = models.CharField(max_length=20, default='white')

    # Optional animation style for the captions
    animation_style = models.CharField(max_length=50, blank=True)

    # Optional target for the animation (e.g., which words/elements to animate)
    animation_target = models.CharField(max_length=50, blank=True)

    # Boolean flag to determine if captions should be displayed per word (True) or per phrase (False)
    per_word = models.BooleanField(default=False)

    # Boolean flag to hide punctuation in the captions when True
    hide_punctuation = models.BooleanField(default=False)

    # Boolean flag to enable AI-based keyword highlighting when True
    ai_highlight_keywords = models.BooleanField(default=False)

    # Boolean flag to enable caption rotation/position changes when True
    rotate_captions = models.BooleanField(default=False)

    def __str__(self):
        return f"Captions for {self.video_request.id}"


# ==============================================================================
# PAYMENT AND BILLING MODELS
# ==============================================================================

class StripeCustomer(models.Model):
    """Store Stripe customer information"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stripe_customer')
    stripe_customer_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stripe Customer {self.stripe_customer_id} for {self.user.email}"


class Subscription(models.Model):
    """Track user subscriptions"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('incomplete', 'Incomplete'),
        ('incomplete_expired', 'Incomplete Expired'),
        ('past_due', 'Past Due'),
        ('unpaid', 'Unpaid'),
        ('trialing', 'Trialing'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='incomplete')
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"

    @property
    def is_active(self):
        return self.status in ['active', 'trialing']


class PaymentHistory(models.Model):
    """Track all payment transactions"""
    PAYMENT_TYPE_CHOICES = [
        ('subscription', 'Subscription'),
        ('credit_purchase', 'Credit Purchase'),
        ('refund', 'Refund'),
    ]

    STATUS_CHOICES = [
        ('succeeded', 'Succeeded'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_history')
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_invoice_id = models.CharField(max_length=255, null=True, blank=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # In dollars
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True)
    credits_added = models.IntegerField(default=0)  # Credits added from this payment
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - ${self.amount} ({self.status})"


class CreditPurchase(models.Model):
    """Track one-time credit purchases"""
    CREDIT_PACKAGES = [
        (50, '50 Credits - $9.99'),
        (100, '100 Credits - $19.99'),
        (250, '250 Credits - $39.99'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='credit_purchases')
    payment_history = models.OneToOneField(PaymentHistory, on_delete=models.CASCADE, related_name='credit_purchase')
    credits_purchased = models.IntegerField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.credits_purchased} credits for ${self.amount_paid}"


# ==============================================================================
# QUEUE MANAGEMENT MODELS
# ==============================================================================

class ProcessingQueue(models.Model):
    """Queue for video processing tasks with priority management"""

    PRIORITY_CHOICES = [
        (1, 'Low Priority (Free Users)'),
        (2, 'Normal Priority (Pro Users)'),
        (3, 'High Priority (Premium Users)'),
        (4, 'Critical Priority (Admin/Support)'),
    ]

    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    video_request = models.OneToOneField(VideoRequest, on_delete=models.CASCADE, related_name='queue_entry')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')

    # Timing information
    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Processing details
    estimated_duration = models.FloatField(null=True, blank=True, help_text="Estimated processing time in minutes")
    actual_duration = models.FloatField(null=True, blank=True, help_text="Actual processing time in minutes")
    worker_id = models.CharField(max_length=100, blank=True, help_text="ID of the worker processing this task")

    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)

    # Metadata
    processing_settings = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-priority', 'queued_at']  # Higher priority first, then FIFO
        indexes = [
            models.Index(fields=['status', 'priority', 'queued_at']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"Queue #{self.id} - {self.user.email} ({self.get_status_display()})"

    @property
    def queue_position(self):
        """Get position in queue for queued tasks"""
        if self.status != 'queued':
            return None

        return ProcessingQueue.objects.filter(
            status='queued',
            priority__gt=self.priority
        ).count() + ProcessingQueue.objects.filter(
            status='queued',
            priority=self.priority,
            queued_at__lt=self.queued_at
        ).count() + 1

    @property
    def estimated_wait_time(self):
        """Estimate wait time based on queue position and processing times"""
        position = self.queue_position
        if not position:
            return None

        # Average processing time (in minutes) - can be improved with actual data
        avg_processing_time = 5.0  # 5 minutes average

        # Count currently processing tasks
        processing_count = ProcessingQueue.objects.filter(status='processing').count()

        # Estimate based on position and current processing
        estimated_minutes = (position - 1) * avg_processing_time
        if processing_count > 0:
            estimated_minutes += avg_processing_time  # Add time for current processing

        return max(1, estimated_minutes)  # Minimum 1 minute

    def get_priority_display_color(self):
        """Get color for priority display"""
        colors = {
            1: '#gray',      # Low
            2: '#blue',      # Normal
            3: '#orange',    # High
            4: '#red',       # Critical
        }
        return colors.get(self.priority, '#gray')


class QueueStats(models.Model):
    """Daily statistics for queue performance"""
    date = models.DateField(unique=True)

    # Task counts
    total_queued = models.IntegerField(default=0)
    total_processed = models.IntegerField(default=0)
    total_failed = models.IntegerField(default=0)

    # Timing stats
    avg_wait_time = models.FloatField(default=0.0, help_text="Average wait time in minutes")
    avg_processing_time = models.FloatField(default=0.0, help_text="Average processing time in minutes")
    max_queue_length = models.IntegerField(default=0)

    # User tier breakdown
    free_users_processed = models.IntegerField(default=0)
    pro_users_processed = models.IntegerField(default=0)
    premium_users_processed = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Queue Stats for {self.date}"


class NotificationEvent(models.Model):
    """Track notification events for processing completion"""

    EVENT_TYPES = [
        ('processing_started', 'Processing Started'),
        ('processing_completed', 'Processing Completed'),
        ('processing_failed', 'Processing Failed'),
        ('queue_delayed', 'Queue Delayed'),
    ]

    NOTIFICATION_TYPES = [
        ('email', 'Email'),
        ('webhook', 'Webhook'),
        ('sms', 'SMS'),  # For future
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    queue_entry = models.ForeignKey(ProcessingQueue, on_delete=models.CASCADE, related_name='notifications')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES, default='email')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    # Content
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)

    # Delivery info
    recipient = models.CharField(max_length=255)  # email address, phone, webhook URL
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} notification to {self.recipient} ({self.status})"


