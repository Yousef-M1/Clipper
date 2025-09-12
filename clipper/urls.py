from django.urls import path
from .views import (VideoRequestCreateView, CaptionSettingsUpdateView, ClipListView , VideoRequestListView)


urlpatterns = [
    path('video/', VideoRequestListView.as_view(), name='video-request-list'),
    path('video/create/', VideoRequestCreateView.as_view(), name='video-request-create'),
    path('caption/<int:pk>/', CaptionSettingsUpdateView.as_view(), name='caption-settings-update'),
    path('video/<int:video_request_id>/clips/', ClipListView.as_view(), name='clip-list'),

]