"""
AI Influencer Models for talking avatar video generation
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import User


class AvatarCharacter(models.Model):
    """
    Predefined AI avatar characters/personas
    """
    name = models.CharField(max_length=100, help_text="Character name (e.g., 'Sarah', 'Tech Guru Mike')")
    description = models.TextField(help_text="Character description and personality")
    avatar_image = models.ImageField(
        upload_to='avatars/characters/',
        help_text="Base image for this character"
    )
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('neutral', 'Neutral')],
        default='neutral'
    )
    voice_style = models.CharField(
        max_length=50,
        choices=[
            ('natural', 'Natural'),
            ('professional', 'Professional'),
            ('casual', 'Casual'),
            ('energetic', 'Energetic'),
            ('calm', 'Calm'),
        ],
        default='natural',
        help_text="Default voice style for this character"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class VoiceProfile(models.Model):
    """
    Available TTS voices and configurations
    """
    name = models.CharField(max_length=100, help_text="Voice name (e.g., 'Emma - English Female')")
    voice_id = models.CharField(
        max_length=100,
        help_text="Voice identifier for TTS engine (e.g., 'en-US-EmmaNeural')"
    )
    language = models.CharField(max_length=10, default='en-US')
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female')],
    )
    engine = models.CharField(
        max_length=20,
        choices=[
            ('edge_tts', 'Edge TTS'),
            ('elevenlabs', 'ElevenLabs'),
            ('chatterbox', 'Chatterbox'),
            ('paddle_tts', 'Paddle TTS'),
            ('openai', 'OpenAI TTS'),
        ],
        default='edge_tts'
    )
    sample_rate = models.IntegerField(default=22050)
    is_premium = models.BooleanField(default=False, help_text="Requires premium subscription")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['language', 'gender', 'name']
        unique_together = ['voice_id', 'engine']

    def __str__(self):
        return f"{self.name} ({self.language})"


class BackgroundVideo(models.Model):
    """
    Background video templates for AI influencer videos
    """
    CATEGORY_CHOICES = [
        ('tech', 'Technology'),
        ('nature', 'Nature'),
        ('city', 'City/Urban'),
        ('abstract', 'Abstract'),
        ('business', 'Business'),
        ('gaming', 'Gaming'),
        ('fitness', 'Fitness'),
        ('food', 'Food'),
        ('travel', 'Travel'),
        ('education', 'Education'),
    ]

    name = models.CharField(max_length=100, help_text="Background video name")
    description = models.TextField(blank=True, help_text="Background description")
    video_file = models.FileField(
        upload_to='backgrounds/videos/',
        help_text="Background video file (MP4, MOV, AVI)"
    )
    thumbnail = models.ImageField(
        upload_to='backgrounds/thumbnails/',
        null=True,
        blank=True,
        help_text="Video thumbnail preview"
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='abstract',
        help_text="Background category"
    )
    duration = models.FloatField(
        null=True,
        blank=True,
        help_text="Original video duration in seconds"
    )
    is_loopable = models.BooleanField(
        default=True,
        help_text="Can this video be looped for longer speeches?"
    )
    is_premium = models.BooleanField(
        default=False,
        help_text="Requires premium subscription"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.category})"

    @property
    def file_size_mb(self):
        """Get file size in MB"""
        if self.video_file:
            return self.video_file.size / (1024 * 1024)
        return 0


class AvatarProject(models.Model):
    """
    Main model for AI influencer video projects
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    ASPECT_RATIO_CHOICES = [
        ('16:9', 'Landscape (16:9)'),
        ('9:16', 'Portrait/TikTok (9:16)'),
        ('1:1', 'Square (1:1)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='avatar_projects')
    title = models.CharField(max_length=200, help_text="Project title")
    script = models.TextField(help_text="Text script for the avatar to speak")

    # Avatar Configuration
    character = models.ForeignKey(
        AvatarCharacter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Predefined character to use"
    )
    custom_avatar_image = models.ImageField(
        upload_to='avatars/custom/',
        null=True,
        blank=True,
        help_text="Custom avatar image (overrides character)"
    )

    # Voice Configuration
    voice = models.ForeignKey(VoiceProfile, on_delete=models.SET_NULL, null=True)
    voice_speed = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.5), MaxValueValidator(2.0)],
        help_text="Voice speed multiplier (0.5-2.0)"
    )
    voice_pitch = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.5), MaxValueValidator(2.0)],
        help_text="Voice pitch multiplier (0.5-2.0)"
    )

    # Video Configuration
    aspect_ratio = models.CharField(
        max_length=10,
        choices=ASPECT_RATIO_CHOICES,
        default='16:9'
    )
    video_quality = models.CharField(
        max_length=10,
        choices=[
            ('720p', '720p HD'),
            ('1080p', '1080p Full HD'),
        ],
        default='1080p'
    )
    background_color = models.CharField(
        max_length=7,
        default='#000000',
        help_text="Background color in hex format"
    )
    background_image = models.ImageField(
        upload_to='avatars/backgrounds/',
        null=True,
        blank=True,
        help_text="Custom background image"
    )
    background_video = models.ForeignKey(
        BackgroundVideo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Background video template"
    )
    background_type = models.CharField(
        max_length=10,
        choices=[
            ('color', 'Solid Color'),
            ('image', 'Static Image'),
            ('video', 'Video Background'),
        ],
        default='color',
        help_text="Type of background to use"
    )

    # Processing Settings
    lip_sync_model = models.CharField(
        max_length=20,
        choices=[
            ('wav2lip', 'Wav2Lip'),
            ('wav2lipv2', 'Wav2Lip v2'),
            ('sadtalker', 'SadTalker'),
        ],
        default='wav2lipv2'
    )
    enable_emotions = models.BooleanField(
        default=True,
        help_text="Enable emotion-based facial expressions"
    )
    head_movement_intensity = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Head movement intensity (0.0-1.0)"
    )

    # Status and Results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress_percentage = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)

    # Generated Content
    generated_audio = models.FileField(
        upload_to='ai_influencer/audio/',
        null=True,
        blank=True,
        help_text="Generated TTS audio file"
    )
    final_video = models.FileField(
        upload_to='ai_influencer/videos/',
        null=True,
        blank=True,
        help_text="Final generated video"
    )
    thumbnail = models.ImageField(
        upload_to='ai_influencer/thumbnails/',
        null=True,
        blank=True,
        help_text="Video thumbnail"
    )

    # Metadata
    video_duration = models.FloatField(null=True, blank=True, help_text="Video duration in seconds")
    file_size_mb = models.FloatField(null=True, blank=True, help_text="File size in MB")
    processing_time = models.IntegerField(null=True, blank=True, help_text="Processing time in seconds")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.email}"

    @property
    def avatar_image_url(self):
        """Get the avatar image URL (custom or character)"""
        if self.custom_avatar_image:
            return self.custom_avatar_image.url
        elif self.character and self.character.avatar_image:
            return self.character.avatar_image.url
        return None

    @property
    def estimated_credits_cost(self):
        """Calculate estimated credits cost based on script length and settings"""
        base_cost = 5  # Base cost for avatar generation
        script_length_multiplier = len(self.script) / 100  # 1 credit per 100 characters
        quality_multiplier = 1.5 if self.video_quality == '1080p' else 1.0

        return max(1, int(base_cost + script_length_multiplier * quality_multiplier))


class ProcessingLog(models.Model):
    """
    Track processing steps and performance
    """
    project = models.ForeignKey(AvatarProject, on_delete=models.CASCADE, related_name='processing_logs')
    step = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=[('started', 'Started'), ('completed', 'Completed'), ('failed', 'Failed')]
    )
    message = models.TextField(blank=True)
    processing_time = models.FloatField(null=True, blank=True, help_text="Step processing time in seconds")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.project.title} - {self.step} ({self.status})"
