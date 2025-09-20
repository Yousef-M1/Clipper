from django.urls import path
from . import views

urlpatterns = [
    # Content generation requests
    path('generate/', views.ContentGenerationCreateView.as_view(), name='content-generation-create'),
    path('requests/', views.ContentGenerationRequestListView.as_view(), name='content-generation-requests'),
    path('requests/<int:pk>/', views.ContentGenerationRequestDetailView.as_view(), name='content-generation-request-detail'),
    path('requests/<int:request_id>/retry/', views.retry_content_generation, name='retry-content-generation'),
    path('requests/<int:request_id>/cancel/', views.cancel_content_generation, name='cancel-content-generation'),

    # Generated content management
    path('content/', views.GeneratedContentListView.as_view(), name='generated-content-list'),
    path('content/<int:pk>/', views.GeneratedContentDetailView.as_view(), name='generated-content-detail'),
    path('content/<int:pk>/download/', views.download_generated_content, name='download-generated-content'),
    path('content/<int:pk>/publish/', views.publish_content, name='publish-content'),
    path('content/<int:pk>/rate/', views.rate_content, name='rate-content'),

    # Templates
    path('templates/', views.ContentTemplateListView.as_view(), name='content-template-list'),
    path('templates/<int:pk>/', views.ContentTemplateDetailView.as_view(), name='content-template-detail'),

    # Quick generation endpoints
    path('generate/blog-post/', views.generate_blog_post_from_video, name='generate-blog-post'),
    path('generate/show-notes/', views.generate_show_notes_from_video, name='generate-show-notes'),
    path('generate/social-media/', views.generate_social_media_from_video, name='generate-social-media'),
    path('generate/seo-article/', views.generate_seo_article_from_video, name='generate-seo-article'),

    # Analytics and usage
    path('usage/', views.get_content_generation_usage, name='content-generation-usage'),
    path('analytics/', views.get_content_analytics, name='content-analytics'),

    # System endpoints
    path('options/', views.get_content_generation_options, name='content-generation-options'),
    path('templates/available/', views.get_available_templates, name='available-templates'),

    # Complete workflow test endpoints
    path('test-youtube-workflow/', views.test_complete_youtube_workflow, name='test-youtube-workflow'),
    path('workflow-options/', views.get_workflow_options, name='workflow-options'),
]