#!/usr/bin/env python
"""
🔗 Generate TikTok OAuth URL
Get the authorization URL to connect your TikTok account
"""

import os
import urllib.parse as urlparse
import hashlib
import base64
import secrets

# Your TikTok API credentials
TIKTOK_CLIENT_ID = "aw9ofb5sjhd31dtp"
REDIRECT_URI = "http://localhost:8000/api/social/tiktok/callback/"

def generate_pkce_challenge():
    """Generate PKCE code verifier and challenge for TikTok OAuth"""
    # Generate code verifier (43-128 characters)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

    # Generate code challenge (SHA256 hash of verifier)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')

    return code_verifier, code_challenge

def generate_tiktok_oauth_url():
    """Generate TikTok OAuth authorization URL with PKCE"""

    # Generate PKCE parameters
    code_verifier, code_challenge = generate_pkce_challenge()

    # TikTok OAuth parameters with PKCE
    params = {
        'client_id': TIKTOK_CLIENT_ID,
        'response_type': 'code',
        'scope': 'user.info.basic,video.upload,video.publish',
        'redirect_uri': REDIRECT_URI,
        'state': 'secure-random-state-' + secrets.token_urlsafe(16),
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }

    # TikTok OAuth base URL
    base_url = "https://www.tiktok.com/v2/auth/authorize/"

    # Build complete OAuth URL
    oauth_url = base_url + "?" + urlparse.urlencode(params)

    return oauth_url, code_verifier, params['state']

def main():
    print("TikTok OAuth Setup with PKCE")
    print("=" * 50)

    oauth_url, code_verifier, state = generate_tiktok_oauth_url()

    print("Step 1: Visit this URL to authorize your TikTok account:")
    print(f"URL: {oauth_url}")
    print()
    print("IMPORTANT INFO FOR COMPLETING CONNECTION:")
    print(f"Code Verifier: {code_verifier}")
    print(f"State: {state}")
    print()
    print("Step 2: After authorization, TikTok will redirect you to:")
    print(f"   {REDIRECT_URI}?code=AUTHORIZATION_CODE&state={state}")
    print()
    print("Step 3: Copy the 'code' parameter from the redirect URL")
    print("Step 4: Use that code + code_verifier to complete the connection!")
    print()
    print("IMPORTANT: Make sure you're logged into the TikTok account")
    print("   you want to connect before visiting the URL!")
    print()
    print("SAVE THE CODE VERIFIER - you'll need it to exchange the auth code!")

if __name__ == "__main__":
    main()