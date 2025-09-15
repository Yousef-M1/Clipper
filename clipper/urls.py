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
    path('options/video-formats/', views.get_video_formats, name='video-formats'),
    path('options/platform-presets/', views.get_platform_presets, name='platform-presets'),
    path('options/processing-options/', views.get_processing_options, name='processing-options'),
    path('options/estimate-cost/', views.estimate_processing_cost, name='estimate-cost'),

    # Dashboard endpoints
    path('dashboard/summary/', views.dashboard_summary, name='dashboard-summary'),
    path('video-requests/<int:pk>/detail/', views.VideoRequestDetailView.as_view(), name='video-request-detail'),
    path('clips/<int:clip_id>/download/', views.download_clip, name='download-clip'),
    path('video-requests/<int:video_request_id>/delete/', views.delete_video_request, name='delete-video-request'),
    path('clips/<int:clip_id>/delete/', views.delete_clip, name='delete-clip'),
    path('clips/bulk-download/', views.bulk_download_clips, name='bulk-download-clips'),

    # Rate limiting status
    path('rate-limits/', views.get_rate_limit_status, name='rate-limit-status'),

    # Queue management endpoints
    path('queue/status/', views.get_queue_status, name='queue-status'),
    path('queue/history/', views.get_processing_history, name='processing-history'),
    path('queue/<int:queue_id>/cancel/', views.cancel_processing, name='cancel-processing'),
    path('queue/<int:queue_id>/retry/', views.retry_processing, name='retry-processing'),

    # Enhanced Scene Detection endpoints - CutMagic-like functionality
    path('analysis/composition/', views.analyze_video_composition, name='analyze-composition'),
    path('analysis/enhanced-moments/', views.detect_enhanced_moments, name='enhanced-moments'),
    path('analysis/scene-transitions/', views.detect_scene_transitions, name='scene-transitions'),
    path('analysis/capabilities/', views.get_scene_detection_capabilities, name='scene-capabilities'),

    # Social Media Integration endpoints
    path('video-requests/<int:video_request_id>/social-posting/enable/', views.enable_social_media_posting, name='enable-social-posting'),
    path('video-requests/<int:video_request_id>/social-posting/status/', views.get_social_posting_status, name='social-posting-status'),
]