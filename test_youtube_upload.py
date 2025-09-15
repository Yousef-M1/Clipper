#!/usr/bin/env python
"""
🎬 Test YouTube Video Upload
Upload a test video to YouTube using OAuth credentials
"""

import os
import requests
import json
import mimetypes
from datetime import datetime

# Your YouTube OAuth credentials from the callback
ACCESS_TOKEN = None  # Will get fresh token from refresh_token
REFRESH_TOKEN = "YOUR_REFRESH_TOKEN_HERE"
CLIENT_ID = "YOUR_CLIENT_ID_HERE"
CLIENT_SECRET = "YOUR_CLIENT_SECRET_HERE"

def create_test_video():
    """Create a simple test video file using FFmpeg"""
    print("🎥 Creating test video...")

    # Create a 10-second test video with text overlay
    cmd = [
        "ffmpeg", "-y",  # Overwrite if exists
        "-f", "lavfi",
        "-i", "testsrc2=duration=10:size=1280x720:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=1000:duration=10",
        "-vf", "drawtext=text='Clipper AI Test Video':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-c:a", "aac",
        "-t", "10",
        "test_video.mp4"
    ]

    import subprocess
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Test video created: test_video.mp4")
        return "test_video.mp4"
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating video: {e}")
        print(f"FFmpeg output: {e.stderr}")
        return None
    except FileNotFoundError:
        print("❌ FFmpeg not found. Please install FFmpeg first.")
        return None

def refresh_access_token():
    """Refresh the access token using the refresh token"""
    print("🔄 Refreshing access token...")

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    }

    response = requests.post(token_url, data=token_data)
    token_info = response.json()

    if 'access_token' in token_info:
        print("✅ Access token refreshed successfully")
        return token_info['access_token']
    else:
        print(f"❌ Error refreshing token: {token_info}")
        return None

def upload_video_to_youtube(video_file, access_token):
    """Upload video to YouTube"""
    print(f"📤 Uploading {video_file} to YouTube...")

    # Video metadata
    metadata = {
        "snippet": {
            "title": "Clipper AI Test Video - Automated Upload",
            "description": "This is a test video uploaded automatically by Clipper AI platform using YouTube API v3.\n\n🤖 Generated with Clipper AI\n📅 " + str(datetime.now()),
            "tags": ["clipper", "ai", "test", "automation", "api"],
            "categoryId": "22",  # People & Blogs
            "defaultLanguage": "en"
        },
        "status": {
            "privacyStatus": "unlisted",  # Make it unlisted for testing
            "selfDeclaredMadeForKids": False
        }
    }

    # Upload URL
    upload_url = "https://www.googleapis.com/upload/youtube/v3/videos"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }

    params = {
        'part': 'snippet,status',
        'uploadType': 'multipart'
    }

    # Read video file
    try:
        with open(video_file, 'rb') as video:
            files = {
                'metadata': (None, json.dumps(metadata), 'application/json'),
                'media': (video_file, video, 'video/mp4')
            }

            response = requests.post(upload_url, headers=headers, params=params, files=files)
            result = response.json()

            if response.status_code == 200:
                video_id = result.get('id')
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                print(f"🎉 Video uploaded successfully!")
                print(f"📺 Video ID: {video_id}")
                print(f"🔗 Video URL: {video_url}")
                print(f"👁️  Status: {result.get('status', {}).get('privacyStatus', 'unknown')}")
                return video_url
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"Error: {result}")
                return None

    except Exception as e:
        print(f"❌ Error reading video file: {e}")
        return None

def main():

    print("🎬 YouTube Video Upload Test")
    print("=" * 50)

    # Step 1: Create test video
    video_file = create_test_video()
    if not video_file:
        print("❌ Failed to create test video. Exiting.")
        return

    # Step 2: Refresh access token (in case it expired)
    fresh_token = refresh_access_token()
    if not fresh_token:
        print("❌ Failed to refresh access token. Using original token...")
        fresh_token = ACCESS_TOKEN

    # Step 3: Upload video
    video_url = upload_video_to_youtube(video_file, fresh_token)

    if video_url:
        print(f"\n🎉 SUCCESS! Test video uploaded to YouTube!")
        print(f"🔗 Watch at: {video_url}")
        print(f"📱 This proves your Clipper AI platform can upload to YouTube!")
    else:
        print(f"\n❌ Upload failed. Check the error messages above.")

    # Cleanup
    try:
        os.remove(video_file)
        print(f"🧹 Cleaned up test file: {video_file}")
    except:
        pass

if __name__ == "__main__":
    main()