from django.urls import path
from . import views

urlpatterns = [
    # Original endpoints
    path('video-requests/', views.VideoRequestListView.as_view(), name='video-request-list'),
    path('video-requests/create/', views.VideoRequestCreateView.as_view(), name='video-request-create'),
    path('caption-settings/<int:pk>/', views.CaptionSettingsUpdateView.as_view(), name='caption-settings-update'),
    path('video-requests/<int:video_request_id>/clips/', views.ClipListView.as_view(), name='clip-list'),

    # Enhanced endpoints
    path('video-requests/create-enhanced/', views.EnhancedVideoRequestCreateView.as_view(), name='video-request-create-enhanced'),
    path('video-requests/<int:video_request_id>/reprocess/', views.reprocess_video, name='reprocess-video'),

    # Configuration endpoints
    path('options/quality-presets/', views.get_quality_presets, name='quality-presets'),
    path('options/compression-levels/', views.get_compression_levels, name='compression-levels'),
    path('options/caption-styles/', views.get_caption_styles, name='caption-styles'),
    path('options/processing-options/', views.get_processing_options, name='processing-options'),
    path('options/estimate-cost/', views.estimate_processing_cost, name='estimate-cost'),
]