"""
URL configuration for AI influencer app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'characters', views.AvatarCharacterViewSet)
router.register(r'voices', views.VoiceProfileViewSet)
router.register(r'projects', views.AvatarProjectViewSet, basename='avatarproject')

app_name = 'ai_influencer'

urlpatterns = [
    path('api/ai-influencer/', include(router.urls)),
]