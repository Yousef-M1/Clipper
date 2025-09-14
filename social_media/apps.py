"""
Social Media Django App Configuration
"""

from django.apps import AppConfig


class SocialMediaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'social_media'
    verbose_name = 'Social Media Publishing'

    def ready(self):
        """App ready signal - import tasks to register with Celery"""
        try:
            from . import tasks  # noqa
        except ImportError:
            pass