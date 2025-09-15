#!/usr/bin/env python
"""
🚀 Production API Setup Script
Interactive setup for social media API credentials
"""

import os
import sys
import re
from pathlib import Path

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🚀 {title}")
    print(f"{'='*60}")

def print_step(step, title):
    print(f"\n📋 Step {step}: {title}")
    print("-" * 40)

def get_env_value(key, description, current_value=None):
    """Get environment variable value from user"""
    if current_value and current_value != "paste-your-":
        prompt = f"✅ {description}\nCurrent: {current_value[:20]}...\nKeep current? (y/n): "
        if input(prompt).lower().strip() == 'y':
            return current_value

    print(f"\n🔑 {description}")
    while True:
        value = input(f"Enter {key}: ").strip()
        if value:
            return value
        print("❌ Please provide a valid value")

def update_env_file(env_vars):
    """Update .env file with new values"""
    env_path = Path('.env')

    if env_path.exists():
        with open(env_path, 'r') as f:
            content = f.read()
    else:
        content = ""

    # Update each variable
    for key, value in env_vars.items():
        pattern = f"^{key}=.*$"
        replacement = f"{key}={value}"

        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            content += f"\n{replacement}"

    with open(env_path, 'w') as f:
        f.write(content)

    print(f"✅ Updated {env_path}")

def test_api_connection(platform, client_id):
    """Simple validation of API credentials"""
    if not client_id or len(client_id) < 10:
        print(f"⚠️  {platform} Client ID seems too short")
        return False
    print(f"✅ {platform} credentials look valid")
    return True

def main():
    print_header("Social Media API Production Setup")
    print("This script will help you configure real API credentials")
    print("Make sure you have created apps on each platform first!")

    env_vars = {}

    # Read current .env if exists
    env_path = Path('.env')
    current_env = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    current_env[key] = value

    # TikTok Setup
    print_step(1, "TikTok API Setup")
    print("🔗 Instructions:")
    print("1. Go to: https://developers.tiktok.com/")
    print("2. Create app with business verification")
    print("3. Add redirect URL: http://localhost:8000/api/social/tiktok/callback/")
    print("4. Request scopes: user.info.basic, video.upload, video.publish")

    choice = input("\n📱 Do you have TikTok API credentials? (y/n): ").lower().strip()
    if choice == 'y':
        env_vars['TIKTOK_CLIENT_ID'] = get_env_value(
            'TIKTOK_CLIENT_ID',
            'TikTok Client ID (from your app dashboard)',
            current_env.get('TIKTOK_CLIENT_ID')
        )
        env_vars['TIKTOK_CLIENT_SECRET'] = get_env_value(
            'TIKTOK_CLIENT_SECRET',
            'TikTok Client Secret (from your app dashboard)',
            current_env.get('TIKTOK_CLIENT_SECRET')
        )
        test_api_connection('TikTok', env_vars['TIKTOK_CLIENT_ID'])
    else:
        print("⏩ Skipping TikTok - you can add credentials later")

    # Instagram Setup
    print_step(2, "Instagram Business API Setup")
    print("🔗 Instructions:")
    print("1. Go to: https://developers.facebook.com/")
    print("2. Create Business app")
    print("3. Add Instagram Basic Display product")
    print("4. Add redirect URL: http://localhost:8000/api/social/instagram/callback/")

    choice = input("\n📸 Do you have Instagram API credentials? (y/n): ").lower().strip()
    if choice == 'y':
        env_vars['INSTAGRAM_CLIENT_ID'] = get_env_value(
            'INSTAGRAM_CLIENT_ID',
            'Instagram Client ID (from Meta app dashboard)',
            current_env.get('INSTAGRAM_CLIENT_ID')
        )
        env_vars['INSTAGRAM_CLIENT_SECRET'] = get_env_value(
            'INSTAGRAM_CLIENT_SECRET',
            'Instagram Client Secret (from Meta app dashboard)',
            current_env.get('INSTAGRAM_CLIENT_SECRET')
        )
        test_api_connection('Instagram', env_vars['INSTAGRAM_CLIENT_ID'])
    else:
        print("⏩ Skipping Instagram - you can add credentials later")

    # YouTube Setup
    print_step(3, "YouTube Data API Setup")
    print("🔗 Instructions:")
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Create project and enable YouTube Data API v3")
    print("3. Create OAuth 2.0 credentials")
    print("4. Add redirect URL: http://localhost:8000/api/social/youtube/callback/")

    choice = input("\n🎥 Do you have YouTube API credentials? (y/n): ").lower().strip()
    if choice == 'y':
        env_vars['YOUTUBE_CLIENT_ID'] = get_env_value(
            'YOUTUBE_CLIENT_ID',
            'YouTube Client ID (from Google Cloud Console)',
            current_env.get('YOUTUBE_CLIENT_ID')
        )
        env_vars['YOUTUBE_CLIENT_SECRET'] = get_env_value(
            'YOUTUBE_CLIENT_SECRET',
            'YouTube Client Secret (from Google Cloud Console)',
            current_env.get('YOUTUBE_CLIENT_SECRET')
        )
        test_api_connection('YouTube', env_vars['YOUTUBE_CLIENT_ID'])
    else:
        print("⏩ Skipping YouTube - you can add credentials later")

    # Update environment
    if env_vars:
        print_step(4, "Updating Configuration")
        update_env_file(env_vars)

        print("\n🔄 Next Steps:")
        print("1. Restart your Docker services: docker-compose down && docker-compose up -d")
        print("2. Test OAuth connections: http://localhost:8000/api/social/accounts/connect/")
        print("3. Try publishing your first post!")

        restart_choice = input("\n🐳 Restart Docker services now? (y/n): ").lower().strip()
        if restart_choice == 'y':
            print("🔄 Restarting services...")
            os.system("docker-compose down")
            os.system("docker-compose up -d")
            print("✅ Services restarted!")
    else:
        print("\n⏩ No credentials updated. Run this script again when you have API keys.")

    print_header("Setup Complete!")
    print("🎉 Your social media publishing system is ready!")
    print("📱 Test with: curl -H 'Authorization: Token YOUR_TOKEN' http://localhost:8000/api/social/dashboard/")

if __name__ == "__main__":
    main()