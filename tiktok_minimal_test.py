#!/usr/bin/env python
"""
🔗 Minimal TikTok OAuth Test
Test with basic permissions only
"""

import urllib.parse as urlparse
import hashlib
import base64
import secrets

TIKTOK_CLIENT_ID = "aw9ofb5sjhd31dtp"
REDIRECT_URI = "http://localhost:8000/api/social/tiktok/callback/"

def generate_minimal_oauth():
    """Generate minimal OAuth URL for testing"""

    # Minimal PKCE
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')

    # Minimal parameters - just basic info
    params = {
        'client_id': TIKTOK_CLIENT_ID,
        'response_type': 'code',
        'scope': 'user.info.basic',  # Only basic info first
        'redirect_uri': REDIRECT_URI,
        'state': 'test-' + secrets.token_urlsafe(8),
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }

    base_url = "https://www.tiktok.com/v2/auth/authorize/"
    oauth_url = base_url + "?" + urlparse.urlencode(params)

    return oauth_url, code_verifier, params['state']

def main():
    print("TikTok Minimal OAuth Test")
    print("=" * 40)

    oauth_url, code_verifier, state = generate_minimal_oauth()

    print("TESTING WITH MINIMAL PERMISSIONS ONLY")
    print("(Just user.info.basic - no video upload)")
    print()
    print("Test URL:")
    print(oauth_url)
    print()
    print(f"Code Verifier: {code_verifier}")
    print(f"State: {state}")
    print()
    print("If this works, we know the app is configured correctly")
    print("and can add video permissions later.")

if __name__ == "__main__":
    main()