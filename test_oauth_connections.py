#!/usr/bin/env python
"""
🔗 OAuth Connection Testing Script
Test real social media connections
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"
TOKEN = "c4a7c95338407eb20b2714f3f9371314b9ec1e7c"  # Use your actual token

def test_connection_flow(platform):
    """Test OAuth connection flow for a platform"""
    headers = {"Authorization": f"Token {TOKEN}"}

    print(f"\n🔗 Testing {platform} OAuth Connection")
    print("-" * 40)

    # Step 1: Get OAuth URL
    try:
        response = requests.post(
            f"{BASE_URL}/api/social/accounts/connect/",
            headers=headers,
            json={"platform": platform}
        )

        if response.status_code == 200:
            data = response.json()
            auth_url = data.get('authorization_url')
            print(f"✅ OAuth URL generated")
            print(f"🔗 Visit: {auth_url}")
            print(f"📝 After authorization, you'll get a callback with auth code")

            auth_code = input(f"\n🔑 Enter the authorization code from {platform} callback: ").strip()

            if auth_code:
                # Step 2: Complete connection
                complete_response = requests.post(
                    f"{BASE_URL}/api/social/accounts/connect/",
                    headers=headers,
                    json={
                        "platform": platform,
                        "auth_code": auth_code,
                        "state": data.get('state')
                    }
                )

                if complete_response.status_code == 200:
                    account_data = complete_response.json()
                    print(f"🎉 {platform} account connected successfully!")
                    print(f"👤 Account: @{account_data.get('account', {}).get('username', 'Unknown')}")
                    return True
                else:
                    print(f"❌ Failed to complete connection: {complete_response.text}")
            else:
                print("⏩ Skipping connection completion")

        else:
            print(f"❌ Failed to get OAuth URL: {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

    return False

def test_publishing(platform_account_id):
    """Test publishing to a connected account"""
    headers = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}

    print(f"\n📱 Testing Publishing")
    print("-" * 40)

    post_data = {
        "social_account_id": platform_account_id,
        "video_url": "https://example.com/test-video.mp4",
        "caption": "Testing live social media publishing from my AI video platform! 🚀",
        "hashtags": ["test", "ai", "social", "automation"]
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/social/posts/schedule/",
            headers=headers,
            json=post_data
        )

        if response.status_code == 200:
            post_info = response.json()
            print(f"✅ Post scheduled successfully!")
            print(f"📝 Post ID: {post_info.get('post', {}).get('id')}")
            print(f"⏰ Scheduled for: {post_info.get('post', {}).get('scheduled_time')}")
            return True
        else:
            print(f"❌ Failed to schedule post: {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

    return False

def main():
    print("🚀 OAuth Connection Testing")
    print("=" * 50)

    # Check if services are running
    try:
        response = requests.get(f"{BASE_URL}/api/social/platforms/")
        if response.status_code != 200:
            print("❌ API not accessible. Make sure Docker services are running:")
            print("   docker-compose up -d")
            sys.exit(1)
    except:
        print("❌ Cannot connect to API. Start services first:")
        print("   docker-compose up -d")
        sys.exit(1)

    print("✅ API is accessible")

    # Test each platform
    platforms = ['tiktok', 'instagram', 'youtube']

    for platform in platforms:
        choice = input(f"\n🔗 Test {platform.title()} connection? (y/n): ").lower().strip()
        if choice == 'y':
            success = test_connection_flow(platform)
            if success:
                test_choice = input(f"\n📱 Test posting to {platform.title()}? (y/n): ").lower().strip()
                if test_choice == 'y':
                    # You'd need to get the account ID from the connection response
                    account_id = input(f"Enter {platform} account ID (from connection response): ").strip()
                    if account_id:
                        test_publishing(int(account_id))

    print("\n🎉 Testing Complete!")
    print("📊 Check your dashboard: http://localhost:8000/api/social/dashboard/")

if __name__ == "__main__":
    main()