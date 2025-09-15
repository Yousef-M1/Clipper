# 🚀 Complete Social Media Publishing Setup Guide

## 📋 **Quick Setup Checklist**

- [ ] Get TikTok API credentials
- [ ] Get Instagram Business API credentials
- [ ] Get YouTube Data API credentials
- [ ] Create `.env` file with all API keys
- [ ] Test OAuth connections
- [ ] Test video publishing
- [ ] Enable automation scheduler

---

## 🔑 **API Credentials Setup**

### **1. TikTok API Setup**

**Step 1: Create Developer Account**
- Go to: https://developers.tiktok.com/
- Sign up with TikTok account
- Complete business verification

**Step 2: Create App**
- App Name: "YourSaaS Video Publisher"
- Category: "Content & Publishing"
- Use case: "Video content management"

**Step 3: OAuth Configuration**
```
Redirect URL: http://localhost:8000/api/social/tiktok/callback/
Scopes: user.info.basic, video.upload, video.publish
```

**Step 4: Get Credentials**
```
TIKTOK_CLIENT_ID=your-app-id
TIKTOK_CLIENT_SECRET=your-app-secret
```

### **2. Instagram Business API Setup**

**Step 1: Create Meta App**
- Go to: https://developers.facebook.com/
- Create Business app
- App Name: "YourSaaS Video Publisher"

**Step 2: Add Instagram Basic Display**
- Add Product → Instagram Basic Display
- Configure OAuth redirect URI

**Step 3: OAuth Configuration**
```
Redirect URL: http://localhost:8000/api/social/instagram/callback/
Scopes: instagram_graph_user_profile, instagram_graph_user_media
```

**Step 4: Get Credentials**
```
INSTAGRAM_CLIENT_ID=your-app-id
INSTAGRAM_CLIENT_SECRET=your-app-secret
```

### **3. YouTube Data API Setup**

**Step 1: Create Google Cloud Project**
- Go to: https://console.cloud.google.com/
- Create new project: "YourSaaS Video Publisher"

**Step 2: Enable YouTube Data API v3**
- APIs & Services → Library
- Search "YouTube Data API v3" → Enable

**Step 3: Create OAuth 2.0 Credentials**
- APIs & Services → Credentials
- Create OAuth 2.0 Client ID
- Web application type

**Step 4: OAuth Configuration**
```
Redirect URL: http://localhost:8000/api/social/youtube/callback/
Scopes: youtube.upload, youtube.readonly
```

**Step 5: Get Credentials**
```
YOUTUBE_CLIENT_ID=your-client-id
YOUTUBE_CLIENT_SECRET=your-client-secret
```

---

## 🔧 **Environment Setup**

**Step 1: Create `.env` File**
```bash
cp .env.example .env
```

**Step 2: Add Your API Credentials**
```env
# Social Media API Configuration
TIKTOK_CLIENT_ID=your-tiktok-client-id
TIKTOK_CLIENT_SECRET=your-tiktok-client-secret

INSTAGRAM_CLIENT_ID=your-instagram-client-id
INSTAGRAM_CLIENT_SECRET=your-instagram-client-secret

YOUTUBE_CLIENT_ID=your-youtube-client-id
YOUTUBE_CLIENT_SECRET=your-youtube-client-secret

# Optional
FRONTEND_URL=http://localhost:3000
```

**Step 3: Restart Services**
```bash
docker-compose down
docker-compose up -d
```

---

## 🔗 **Testing OAuth Connections**

### **Test TikTok Connection**
```bash
# Get OAuth URL
curl -H "Authorization: Token YOUR_TOKEN" \
  "http://localhost:8000/api/social/accounts/connect/" \
  -d '{"platform": "tiktok"}'

# Follow returned authorization_url
# Use callback code to complete connection
```

### **Test Instagram Connection**
```bash
# Get OAuth URL
curl -H "Authorization: Token YOUR_TOKEN" \
  "http://localhost:8000/api/social/accounts/connect/" \
  -d '{"platform": "instagram"}'
```

### **Test YouTube Connection**
```bash
# Get OAuth URL
curl -H "Authorization: Token YOUR_TOKEN" \
  "http://localhost:8000/api/social/accounts/connect/" \
  -d '{"platform": "youtube"}'
```

---

## 📱 **Testing Video Publishing**

### **Schedule a Post**
```bash
curl -X POST "http://localhost:8000/api/social/posts/schedule/" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "social_account_id": 1,
    "video_url": "https://example.com/video.mp4",
    "caption": "Amazing AI-generated content! 🔥",
    "hashtags": ["ai", "video", "viral"],
    "scheduled_time": "2025-01-15T18:00:00Z"
  }'
```

### **Publish Immediately**
```bash
curl -X POST "http://localhost:8000/api/social/posts/publish-now/" \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "social_account_id": 1,
    "video_url": "https://example.com/video.mp4",
    "caption": "Live content! 🚀",
    "hashtags": ["live", "content"]
  }'
```

---

## ⚡ **Enable Automation**

### **Start Celery Beat Scheduler**
```bash
# Enable automated posting
docker-compose --profile automation up -d

# This starts:
# - Scheduled post processing (every 5 minutes)
# - Analytics updates (daily at 2 AM)
# - Token refresh (daily at 1 AM)
```

### **Monitor Automation**
```bash
# View Celery tasks
docker-compose --profile monitoring up -d
# Access Flower at: http://localhost:5555
```

---

## 📊 **Analytics & Dashboard**

### **Get Dashboard Summary**
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  "http://localhost:8000/api/social/dashboard/"
```

### **Get Post Analytics**
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  "http://localhost:8000/api/social/posts/POST_ID/analytics/"
```

---

## 🎯 **Production Deployment**

### **Environment Variables for Production**
```env
# Update redirect URLs for production
TIKTOK_REDIRECT_URI=https://yourdomain.com/api/social/tiktok/callback/
INSTAGRAM_REDIRECT_URI=https://yourdomain.com/api/social/instagram/callback/
YOUTUBE_REDIRECT_URI=https://yourdomain.com/api/social/youtube/callback/

# Frontend URL
FRONTEND_URL=https://yourdomain.com

# Security
DEBUG=False
DJANGO_LOG_LEVEL=WARNING
```

### **Required App Reviews**
- **TikTok**: Submit for production review
- **Instagram**: Request additional permissions
- **YouTube**: Verify app for increased quotas

---

## 🚀 **Integration with Video Processing**

### **Auto-Publish After Clipping**
```python
# In your video processing workflow
from social_media.tasks import schedule_post

# After video is processed
schedule_post.delay(
    user_id=user.id,
    video_url=processed_video_url,
    platforms=['tiktok', 'youtube'],
    caption="AI-generated clip! 🔥",
    auto_hashtags=True
)
```

### **Batch Publishing**
```python
# Publish to multiple platforms
from social_media.services import SocialMediaManager

manager = SocialMediaManager()
results = manager.publish_to_multiple_platforms(
    user=user,
    video_url=video_url,
    platforms=['tiktok', 'instagram', 'youtube'],
    caption="Multi-platform content!",
    schedule_time=None  # Publish immediately
)
```

---

## 🔍 **Troubleshooting**

### **Common Issues**

**OAuth Redirect Mismatch**
- Ensure redirect URLs match exactly in platform settings
- Check HTTP vs HTTPS
- Verify port numbers

**API Rate Limits**
- TikTok: 1000 requests/day (free tier)
- Instagram: 200 requests/hour
- YouTube: 10,000 quota units/day

**Token Expiration**
- Automatic refresh enabled via Celery beat
- Manual refresh available via API

### **Debug Commands**
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs social_media

# Test API endpoints
docker-compose exec web python social_media/test_integration.py
```

---

## 📈 **Next Steps**

1. **✅ Complete API setup** (you're here)
2. **🔗 Test OAuth connections**
3. **📱 Test video publishing**
4. **⚡ Enable automation**
5. **📊 Monitor analytics**
6. **🚀 Deploy to production**

**Your enterprise-level social media publishing system is ready! 🎉**