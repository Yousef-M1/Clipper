"""
URL patterns for social media publishing API
"""

from django.urls import path
from . import views

urlpatterns = [
    # Platform and account management
    path('platforms/', views.get_supported_platforms, name='supported-platforms'),
    path('accounts/', views.get_connected_accounts, name='connected-accounts'),
    path('accounts/connect/', views.connect_social_account, name='connect-account'),
    path('accounts/<int:account_id>/disconnect/', views.disconnect_social_account, name='disconnect-account'),

    # Post scheduling and publishing
    path('posts/schedule/', views.schedule_post, name='schedule-post'),
    path('posts/publish-now/', views.publish_now, name='publish-now'),
    path('posts/', views.get_scheduled_posts, name='scheduled-posts'),
    path('posts/<uuid:post_id>/cancel/', views.cancel_scheduled_post, name='cancel-post'),
    path('posts/<uuid:post_id>/retry/', views.retry_failed_post, name='retry-post'),

    # Analytics
    path('posts/<uuid:post_id>/analytics/', views.get_post_analytics, name='post-analytics'),

    # Dashboard
    path('dashboard/', views.get_dashboard_summary, name='dashboard-summary'),

    # Content suggestions
    path('suggestions/', views.get_content_suggestions, name='content-suggestions'),
    path('suggestions/status/<str:task_id>/', views.get_suggestion_status, name='suggestion-status'),

    # Templates
    path('templates/', views.PostTemplateListCreateView.as_view(), name='template-list'),
    path('templates/<int:pk>/', views.PostTemplateDetailView.as_view(), name='template-detail'),

    # Content calendars
    path('calendars/', views.ContentCalendarListCreateView.as_view(), name='calendar-list'),
    path('calendars/<int:pk>/', views.ContentCalendarDetailView.as_view(), name='calendar-detail'),

    # OAuth callbacks
    path('tiktok/callback/', views.tiktok_oauth_callback, name='tiktok-callback'),
    path('instagram/callback/', views.instagram_oauth_callback, name='instagram-callback'),
    path('youtube/callback/', views.youtube_oauth_callback, name='youtube-callback'),
]