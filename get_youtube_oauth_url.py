#!/usr/bin/env python
"""
🔗 Generate YouTube OAuth URL
Get the authorization URL to connect your YouTube account
"""

import os
import urllib.parse as urlparse
import secrets

# Your YouTube API credentials
YOUTUBE_CLIENT_ID = "YOUR_YOUTUBE_CLIENT_ID_HERE"
YOUTUBE_REDIRECT_URI = "http://localhost:8000/api/social/youtube/callback/"

def generate_youtube_oauth_url():
    """Generate YouTube OAuth authorization URL"""

    # YouTube OAuth parameters
    params = {
        'client_id': YOUTUBE_CLIENT_ID,
        'response_type': 'code',
        'scope': 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly',
        'redirect_uri': YOUTUBE_REDIRECT_URI,
        'state': 'secure-random-state-' + secrets.token_urlsafe(16),
        'access_type': 'offline',  # Get refresh token
        'prompt': 'consent'  # Force consent screen to get refresh token
    }

    # YouTube OAuth base URL
    base_url = "https://accounts.google.com/o/oauth2/auth"

    # Build complete OAuth URL
    oauth_url = base_url + "?" + urlparse.urlencode(params)

    return oauth_url, params['state']

def main():
    print("YouTube OAuth Setup")
    print("=" * 50)

    oauth_url, state = generate_youtube_oauth_url()

    print("Step 1: Visit this URL to authorize your YouTube account:")
    print(f"URL: {oauth_url}")
    print()
    print("IMPORTANT INFO FOR COMPLETING CONNECTION:")
    print(f"State: {state}")
    print()
    print("Step 2: After authorization, YouTube will redirect you to:")
    print(f"   {YOUTUBE_REDIRECT_URI}?code=AUTHORIZATION_CODE&state={state}")
    print()
    print("Step 3: Copy the 'code' parameter from the redirect URL")
    print("Step 4: Use that code to complete the connection!")
    print()
    print("SCOPES REQUESTED:")
    print("• youtube.upload - Upload videos to YouTube")
    print("• youtube.readonly - Read channel info and video list")
    print()
    print("IMPORTANT: Make sure you're logged into the YouTube account")
    print("   you want to connect before visiting the URL!")

if __name__ == "__main__":
    main()