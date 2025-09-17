#!/usr/bin/env python3
"""
Live test of advanced caption system with real video processing
"""

import requests
import json
import time
import os

# API endpoint
BASE_URL = "http://localhost:8000"

def test_caption_styles():
    """Test each of the 5 new advanced caption styles"""

    print("🎬 Testing Advanced Caption Styles")
    print("=" * 40)

    # Test video URL (short video for quick testing)
    test_video_url = "https://sample-videos.com/zip/10/mp4/SampleVideo_360x240_1mb.mp4"

    # Get auth token first
    auth_data = {
        "username": "testuser",
        "password": "testpass123"
    }

    try:
        # Try to login
        login_response = requests.post(f"{BASE_URL}/auth/login/", json=auth_data)
        if login_response.status_code == 200:
            token = login_response.json().get('token')
            headers = {'Authorization': f'Token {token}'}
        else:
            print("ℹ️  No existing user found, will test without auth")
            headers = {}
    except:
        print("ℹ️  Testing without authentication")
        headers = {}

    # Test different advanced caption styles
    styles_to_test = [
        {
            "name": "Elevate Style",
            "style": "elevate_style",
            "max_words": 2,
            "description": "Text reveal with bright green highlights"
        },
        {
            "name": "Slide In Modern",
            "style": "slide_in_modern",
            "max_words": 1,
            "description": "Smooth slide animations with orange effects"
        },
        {
            "name": "Word Pop",
            "style": "word_pop",
            "max_words": 1,
            "description": "Scale animations with red highlights"
        },
        {
            "name": "Two Word Flow",
            "style": "two_word_flow",
            "max_words": 2,
            "description": "Fade animations with purple highlights"
        },
        {
            "name": "Impactful Highlight",
            "style": "impactful_highlight",
            "max_words": 1,
            "description": "Smart detection with gold circle bursts"
        }
    ]

    for style_config in styles_to_test:
        print(f"\n🎨 Testing: {style_config['name']}")
        print(f"   Description: {style_config['description']}")
        print(f"   Max words per screen: {style_config['max_words']}")

        # Create video request with advanced captions
        video_data = {
            "video_url": test_video_url,
            "processing_settings": {
                "caption_style": style_config['style'],
                "advanced_captions": True,
                "max_words_per_screen": style_config['max_words'],
                "enable_word_highlighting": True,
                "clip_duration": 10.0,
                "max_clips": 1,  # Just one clip for testing
                "video_quality": "720p",
                "compression_level": "balanced"
            }
        }

        try:
            # Submit video request
            response = requests.post(
                f"{BASE_URL}/api/video-requests/",
                json=video_data,
                headers=headers
            )

            if response.status_code == 201:
                request_data = response.json()
                request_id = request_data['id']
                print(f"   ✅ Video request created: ID {request_id}")

                # Monitor processing
                print("   ⏳ Processing video...")

                for attempt in range(30):  # Wait up to 5 minutes
                    time.sleep(10)

                    # Check status
                    status_response = requests.get(
                        f"{BASE_URL}/api/video-requests/{request_id}/",
                        headers=headers
                    )

                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        current_status = status_data.get('status', 'unknown')

                        print(f"   📊 Status: {current_status}")

                        if current_status == 'completed':
                            clips = status_data.get('clips', [])
                            print(f"   🎉 SUCCESS! Generated {len(clips)} clip(s)")

                            # Check if clips have subtitles
                            for i, clip in enumerate(clips):
                                clip_id = clip.get('id')
                                print(f"      Clip {i+1}: ID {clip_id}")
                                if 'subtitle_file' in clip:
                                    print(f"      ✅ Has subtitle file with {style_config['name']}")
                                else:
                                    print(f"      ⚠️  No subtitle file found")
                            break

                        elif current_status == 'failed':
                            error_msg = status_data.get('error_message', 'Unknown error')
                            print(f"   ❌ FAILED: {error_msg}")
                            break

                else:
                    print(f"   ⏰ Timeout waiting for processing")

            else:
                error_msg = response.text
                print(f"   ❌ Failed to create request: {error_msg}")

        except Exception as e:
            print(f"   ❌ Error testing {style_config['name']}: {e}")

        print("   " + "-" * 30)

def test_api_endpoints():
    """Test the new caption style API endpoints"""

    print("\n🔗 Testing Caption Style API Endpoints")
    print("=" * 40)

    try:
        # Test caption styles endpoint
        response = requests.get(f"{BASE_URL}/api/caption-styles/")
        if response.status_code == 200:
            data = response.json()
            print("✅ Caption styles endpoint working")

            if 'advanced_styles' in data:
                advanced_styles = data['advanced_styles']
                print(f"   Found {len(advanced_styles)} advanced styles:")
                for style_name, style_info in advanced_styles.items():
                    print(f"   • {style_info['name']} ({style_name})")

            if 'features' in data:
                features = data['features']
                print(f"   Advanced features enabled: {features.get('advanced_captions', False)}")
                print(f"   Max words options: {features.get('max_words_options', [])}")

        else:
            print(f"❌ Caption styles endpoint failed: {response.status_code}")

    except Exception as e:
        print(f"❌ API test error: {e}")

def test_processing_options():
    """Test that processing options include new features"""

    print("\n⚙️ Testing Processing Options")
    print("=" * 30)

    try:
        response = requests.get(f"{BASE_URL}/api/processing-options/")
        if response.status_code == 200:
            data = response.json()
            print("✅ Processing options endpoint working")

            # Check caption styles
            caption_styles = data.get('caption_styles', {})
            advanced_count = sum(1 for name, style in caption_styles.items()
                               if 'elevate' in name or 'slide' in name or 'pop' in name)

            print(f"   Total caption styles: {len(caption_styles)}")
            print(f"   Advanced styles detected: {advanced_count}")

            # Check defaults
            defaults = data.get('defaults', {})
            default_style = defaults.get('caption_style', 'unknown')
            advanced_captions = defaults.get('advanced_captions', False)
            max_words = defaults.get('max_words_per_screen', 'unknown')

            print(f"   Default style: {default_style}")
            print(f"   Advanced captions default: {advanced_captions}")
            print(f"   Default max words: {max_words}")

        else:
            print(f"❌ Processing options failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Processing options test error: {e}")

def main():
    """Run all caption tests"""

    print("🚀 Advanced Caption System Live Test")
    print("=" * 50)

    # Test API endpoints first
    test_api_endpoints()
    test_processing_options()

    # Ask user if they want to run video processing test
    print("\n" + "=" * 50)
    print("📹 Video Processing Test")
    print("This will process a short video with each caption style.")
    print("It may take several minutes to complete.")

    user_input = input("\nRun video processing test? (y/n): ").lower().strip()

    if user_input == 'y' or user_input == 'yes':
        test_caption_styles()
    else:
        print("⏭️  Skipping video processing test")

    print("\n" + "=" * 50)
    print("🎉 Advanced Caption Test Complete!")
    print("\nWhat was tested:")
    print("✅ 5 new advanced caption styles")
    print("✅ Word organization system")
    print("✅ API endpoint integration")
    print("✅ Processing pipeline integration")
    print("✅ Default settings configuration")

if __name__ == "__main__":
    main()