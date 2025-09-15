#!/usr/bin/env python
"""
🚀 Social Media Publishing Demo Script
Creates mock data and demonstrates the complete workflow
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django environment
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from social_media.models import (
    SocialPlatform, SocialAccount, ScheduledPost,
    PostAnalytics, ContentCalendar, PostTemplate
)

User = get_user_model()

def create_demo_data():
    """Create comprehensive demo data for social media system"""

    print("🚀 Creating Social Media Demo Data")
    print("=" * 50)

    # 1. Create or get test user
    print("👤 Setting up test user...")
    user, created = User.objects.get_or_create(
        email='demo@socialmedia.com',
        defaults={
            'first_name': 'Demo',
            'last_name': 'User',
            'is_active': True
        }
    )
    if created:
        user.set_password('demo123')
        user.save()

    # Create auth token
    token, _ = Token.objects.get_or_create(user=user)
    print(f"✅ User created: {user.email}")
    print(f"🔑 Auth Token: {token.key}")

    # 2. Create social platforms
    print("\n📱 Setting up social platforms...")

    platforms_data = [
        {
            'name': 'tiktok',
            'display_name': 'TikTok',
            'is_active': True,
            'supported_formats': ['mp4', 'mov'],
            'max_file_size_mb': 50,  # 50MB
            'max_video_duration': 60,  # 60 seconds
            'aspect_ratios': ['9:16', '1:1'],
            'api_version': 'v1'
        },
        {
            'name': 'instagram',
            'display_name': 'Instagram',
            'is_active': True,
            'supported_formats': ['mp4', 'mov'],
            'max_file_size_mb': 100,  # 100MB
            'max_video_duration': 90,  # 90 seconds
            'aspect_ratios': ['1:1', '9:16', '4:5'],
            'api_version': 'v1'
        },
        {
            'name': 'youtube',
            'display_name': 'YouTube',
            'is_active': True,
            'supported_formats': ['mp4', 'mov', 'avi'],
            'max_file_size_mb': 2048,  # 2GB
            'max_video_duration': 3600,  # 1 hour
            'aspect_ratios': ['16:9', '9:16', '1:1'],
            'api_version': 'v3'
        }
    ]

    platforms = []
    for platform_data in platforms_data:
        platform, created = SocialPlatform.objects.get_or_create(
            name=platform_data['name'],
            defaults=platform_data
        )
        platforms.append(platform)
        status = "Created" if created else "Updated"
        print(f"✅ {platform.display_name}: {status}")

    # 3. Create mock social accounts
    print("\n🔗 Creating connected social accounts...")

    accounts_data = [
        {
            'platform': platforms[0],  # TikTok
            'account_id': 'demo_tiktok_user_123',
            'username': 'demo_creator',
            'display_name': 'Demo Creator',
            'profile_picture': 'https://example.com/tiktok-avatar.jpg',
            'access_token': 'demo_tiktok_token_123',
            'status': 'connected',
            'follower_count': 15420,
            'is_verified': False
        },
        {
            'platform': platforms[1],  # Instagram
            'account_id': 'demo_instagram_business_456',
            'username': 'demo_business',
            'display_name': 'Demo Business',
            'profile_picture': 'https://example.com/instagram-avatar.jpg',
            'access_token': 'demo_instagram_token_456',
            'status': 'connected',
            'follower_count': 8950,
            'is_business_account': True
        },
        {
            'platform': platforms[2],  # YouTube
            'account_id': 'demo_youtube_channel_789',
            'username': 'DemoChannel',
            'display_name': 'Demo YouTube Channel',
            'profile_picture': 'https://example.com/youtube-avatar.jpg',
            'access_token': 'demo_youtube_token_789',
            'status': 'connected',
            'follower_count': 3240,
            'is_verified': False
        }
    ]

    accounts = []
    for account_data in accounts_data:
        account, created = SocialAccount.objects.get_or_create(
            user=user,
            platform=account_data['platform'],
            account_id=account_data['account_id'],
            defaults=account_data
        )
        accounts.append(account)
        status = "Connected" if created else "Updated"
        print(f"✅ {account.platform.display_name} (@{account.username}): {status} - {account.follower_count:,} followers")

    # 4. Create post templates
    print("\n📝 Creating post templates...")

    templates_data = [
        {
            'name': 'AI Video Clip',
            'description': 'Template for AI-generated content',
            'caption_template': 'Amazing AI-generated content! 🤖✨ {description}',
            'hashtags': ['ai', 'video', 'viral', 'content', 'amazing'],
            'default_time_offset': 30
        },
        {
            'name': 'Behind the Scenes',
            'description': 'Template for behind-the-scenes content',
            'caption_template': 'Behind the scenes of creating {title} 🎬 {description}',
            'hashtags': ['bts', 'creating', 'process', 'content', 'maker'],
            'default_time_offset': 60
        },
        {
            'name': 'Tutorial Clip',
            'description': 'Template for educational content',
            'caption_template': 'Quick tutorial: {title} 📚 {description}',
            'hashtags': ['tutorial', 'learn', 'howto', 'education', 'tips'],
            'default_time_offset': 120
        }
    ]

    templates = []
    for template_data in templates_data:
        template, created = PostTemplate.objects.get_or_create(
            user=user,
            name=template_data['name'],
            defaults=template_data
        )
        templates.append(template)
        status = "Created" if created else "Updated"
        print(f"✅ Template '{template.name}': {status}")

    # 5. Create scheduled posts
    print("\n⏰ Creating scheduled posts...")

    now = timezone.now()
    posts_data = [
        {
            'social_account': accounts[0],  # TikTok
            'video_url': 'https://example.com/demo-video-1.mp4',
            'caption': 'Amazing AI-generated dance moves! 🕺✨ This AI can create viral content in seconds!',
            'hashtags': ['ai', 'dance', 'viral', 'tiktok', 'amazing'],
            'scheduled_time': now + timedelta(minutes=30),
            'status': 'scheduled',
            'priority': 2
        },
        {
            'social_account': accounts[1],  # Instagram
            'video_url': 'https://example.com/demo-video-2.mp4',
            'caption': 'Professional content creation with AI 📱✨ Building the future of social media!',
            'hashtags': ['business', 'ai', 'content', 'instagram', 'professional'],
            'scheduled_time': now + timedelta(hours=2),
            'status': 'scheduled',
            'priority': 2
        },
        {
            'social_account': accounts[2],  # YouTube
            'video_url': 'https://example.com/demo-video-3.mp4',
            'caption': 'How AI Creates Viral Content: Complete Tutorial 🎬 Learn the secrets behind AI-powered video creation!',
            'hashtags': ['tutorial', 'ai', 'youtube', 'education', 'viral'],
            'scheduled_time': now + timedelta(hours=6),
            'status': 'scheduled',
            'priority': 3
        },
        {
            'social_account': accounts[0],  # TikTok (posted)
            'video_url': 'https://example.com/demo-video-published.mp4',
            'caption': 'Already viral! 🔥 This AI clip got 50K views in 2 hours!',
            'hashtags': ['viral', 'ai', 'success', 'trending'],
            'scheduled_time': now - timedelta(hours=3),
            'posted_at': now - timedelta(hours=2, minutes=45),
            'status': 'posted',
            'platform_post_id': 'tiktok_post_123456',
            'platform_url': 'https://tiktok.com/@demo_creator/video/123456'
        }
    ]

    posts = []
    for post_data in posts_data:
        post, created = ScheduledPost.objects.get_or_create(
            user=user,
            social_account=post_data['social_account'],
            video_url=post_data['video_url'],
            defaults=post_data
        )
        posts.append(post)
        status = "Created" if created else "Updated"
        post_status = post.get_status_display()
        platform_name = post.social_account.platform.display_name
        print(f"✅ {platform_name} post: {status} - Status: {post_status}")

    # 6. Create analytics for published posts
    print("\n📊 Creating analytics data...")

    published_posts = [p for p in posts if p.status == 'posted']
    for post in published_posts:
        analytics, created = PostAnalytics.objects.get_or_create(
            scheduled_post=post,
            defaults={
                'views': 52400,
                'likes': 4830,
                'comments': 892,
                'shares': 347,
                'saves': 156,
                'engagement_rate': 11.2,
                'reach': 48900,
                'impressions': 67800,
                'platform_metrics': {
                    'hourly_views': [1200, 3400, 8900, 12400, 15600, 18900, 22100],
                    'demographics': {
                        'age_groups': {'18-24': 45, '25-34': 35, '35-44': 20},
                        'gender': {'male': 52, 'female': 48},
                        'top_countries': ['US', 'UK', 'CA', 'AU']
                    },
                    'engagement_timeline': {
                        'first_hour': 1840,
                        'first_6_hours': 28900,
                        'first_24_hours': 52400
                    }
                }
            }
        )
        if created:
            print(f"✅ Analytics for {post.social_account.platform.display_name} post: {analytics.views:,} views, {analytics.engagement_rate}% engagement")

    # 7. Create content calendar
    print("\n📅 Creating content calendar...")

    calendar, created = ContentCalendar.objects.get_or_create(
        user=user,
        name='Demo Content Calendar - January 2025',
        defaults={
            'description': 'Planned content for viral video campaign',
            'start_date': now.date(),
            'end_date': (now + timedelta(days=30)).date(),
            'is_active': True
        }
    )

    if created:
        print(f"✅ Content Calendar: {calendar.name}")

    print("\n" + "=" * 50)
    print("🎉 Demo Data Creation Complete!")
    print("=" * 50)

    return {
        'user': user,
        'token': token.key,
        'platforms': platforms,
        'accounts': accounts,
        'posts': posts,
        'templates': templates,
        'analytics': [PostAnalytics.objects.filter(scheduled_post__in=published_posts)],
        'calendar': calendar
    }

def display_summary(data):
    """Display a summary of created demo data"""

    print(f"\n📋 DEMO DATA SUMMARY")
    print("=" * 50)
    print(f"👤 User: {data['user'].email}")
    print(f"🔑 Token: {data['token'][:20]}...")
    print(f"📱 Platforms: {len(data['platforms'])} connected")
    print(f"🔗 Accounts: {len(data['accounts'])} linked")
    print(f"📝 Posts: {len(data['posts'])} total")
    print(f"📊 Analytics: Available for published posts")
    print(f"📅 Calendar: {data['calendar'].name}")

    print(f"\n🔗 CONNECTED ACCOUNTS:")
    for account in data['accounts']:
        print(f"  • {account.platform.display_name}: @{account.username} ({account.follower_count:,} followers)")

    print(f"\n📝 SCHEDULED POSTS:")
    for post in data['posts']:
        status_emoji = {"scheduled": "⏰", "posted": "✅", "failed": "❌"}.get(post.status, "📝")
        print(f"  {status_emoji} {post.social_account.platform.display_name}: {post.caption[:50]}...")

    print(f"\n🚀 NEXT STEPS:")
    print(f"  1. Test API endpoints with token: {data['token'][:20]}...")
    print(f"  2. View dashboard: GET /api/social/dashboard/")
    print(f"  3. Check scheduled posts: GET /api/social/posts/")
    print(f"  4. Monitor analytics: GET /api/social/posts/{{id}}/analytics/")

if __name__ == "__main__":
    try:
        demo_data = create_demo_data()
        display_summary(demo_data)

        print(f"\n✨ Ready to test! Use this token for API calls:")
        print(f"Authorization: Token {demo_data['token']}")

    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        import traceback
        traceback.print_exc()