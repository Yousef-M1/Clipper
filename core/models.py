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
    total_clips = models.IntegerField(default=0)  # Filled after processing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.url} ({self.user.email})"


class Clip(models.Model):
    video_request = models.ForeignKey(VideoRequest, on_delete=models.CASCADE, related_name='clips')
    start_time = models.FloatField()  # seconds
    end_time = models.FloatField()    # seconds
    duration = models.FloatField()
    caption_style = models.JSONField(default=dict)  # store style like color, size, animation
    status = models.CharField(max_length=20, default='pending')  # pending, processing, done
    file_path = models.FileField(upload_to='clips/', blank=True, null=True)
    format = models.CharField(max_length=10, default='mp4')


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


