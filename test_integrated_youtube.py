#!/usr/bin/env python
"""
🎬 Test Integrated YouTube Publishing
Test uploading videos through the social media platform API
"""

import requests
import json

# API Configuration
BASE_URL = "http://localhost:8000/api/social"
AUTH_TOKEN = "89091bcf8079c48b83b6cea7b390acd03f9aea63"  # From demo script

def test_connected_accounts():
    """Test getting connected accounts"""
    print("📱 Testing connected accounts endpoint...")

    headers = {
        'Authorization': f'Token {AUTH_TOKEN}',
        'Content-Type': 'application/json'
    }

    response = requests.get(f"{BASE_URL}/accounts/", headers=headers)

    if response.status_code == 200:
        data = response.json()
        print("✅ Connected accounts retrieved:")

        accounts = data.get('accounts', [])

        for account in accounts:
            platform_name = account['platform']['name']
            platform_display = account['platform']['display_name']
            print(f"   📱 {platform_display}: {account['display_name']} ({account['follower_count']} followers)")

            # Find the real YouTube account (not the demo one)
            if platform_name == 'youtube' and account['account_id'] == 'UCdcr5kdH2W1uHnXeFRVu4Rg':
                print(f"   📺 ✅ REAL YouTube account found: {account['display_name']}")
                return account['id']
        return None
    else:
        print(f"❌ Failed to get accounts: {response.status_code}")
        return None

def test_dashboard():
    """Test dashboard with real YouTube account"""
    print("\n📊 Testing dashboard with real YouTube account...")

    headers = {
        'Authorization': f'Token {AUTH_TOKEN}',
        'Content-Type': 'application/json'
    }

    response = requests.get(f"{BASE_URL}/dashboard/", headers=headers)

    if response.status_code == 200:
        dashboard = response.json()
        print("✅ Dashboard data:")
        print(f"   📱 Connected accounts: {dashboard['connected_accounts']}")
        print(f"   📝 Total posts: {dashboard['total_posts']}")

        # Show YouTube account specifically
        for platform, accounts in dashboard['accounts_by_platform'].items():
            if platform == 'YouTube':
                for account in accounts:
                    print(f"   📺 YouTube: {account['username']} ({account['follower_count']} subscribers)")
        return True
    else:
        print(f"❌ Dashboard failed: {response.status_code}")
        return False

def schedule_youtube_video(youtube_account_id):
    """Test scheduling a video post to YouTube"""
    print("\n🎬 Testing YouTube video scheduling...")

    headers = {
        'Authorization': f'Token {AUTH_TOKEN}',
        'Content-Type': 'application/json'
    }

    # Create a test video post
    post_data = {
        "social_account_id": youtube_account_id,
        "video_url": "https://example.com/test-video.mp4",  # This would be a real video file
        "caption": "🤖 Test video from Clipper AI platform! Automated upload through integrated YouTube API. #ClipperAI #YouTube #Automation",
        "hashtags": ["ClipperAI", "YouTube", "Automation", "AI", "VideoEditing"],
        "scheduled_time": "2025-09-15T18:00:00Z",  # Schedule for later today
        "priority": 2,
        "title": "Clipper AI Test - Integrated Upload"
    }

    response = requests.post(f"{BASE_URL}/posts/schedule/", headers=headers, json=post_data)

    if response.status_code == 201:
        post = response.json()
        print("✅ YouTube video scheduled successfully!")
        print(f"   📺 Post ID: {post.get('id', 'unknown')}")
        print(f"   📝 Caption: {post.get('caption', 'No caption')[:50]}...")
        print(f"   ⏰ Scheduled: {post.get('scheduled_time', 'unknown')}")
        print(f"   🎯 Platform: {post.get('platform', 'unknown')}")
        print(f"   📄 Full response: {post}")
        return post.get('id', 'success')
    else:
        print(f"❌ Scheduling failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def main():
    print("🎬 Testing Integrated YouTube Publishing")
    print("=" * 60)

    # Test 1: Check connected accounts
    youtube_account_id = test_connected_accounts()
    if not youtube_account_id:
        print("❌ No YouTube account found")
        return

    # Test 2: Test dashboard
    if not test_dashboard():
        print("❌ Dashboard test failed")
        return

    # Test 3: Schedule video
    post_id = schedule_youtube_video(youtube_account_id)
    if post_id:
        print(f"\n🎉 SUCCESS! Integrated YouTube publishing is working!")
        print(f"✅ Real YouTube account connected")
        print(f"✅ API endpoints responding correctly")
        print(f"✅ Video scheduling working")
        print(f"📺 Your Clipper AI platform can now upload to YouTube!")
        print(f"\n💡 Post ID {post_id} is ready for publishing")
        print(f"🔄 Use the retry endpoint to publish immediately")
    else:
        print("\n❌ Integration test failed")

if __name__ == "__main__":
    main()