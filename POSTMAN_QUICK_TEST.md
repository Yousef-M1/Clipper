# 🚀 Postman Quick Test Guide

## Step 1: Create Video Request
**POST** `http://localhost:8000/api/clipper/video-requests/create/`
**Headers:** `Authorization: Token 14ba0fa5f734eaef507417bd1d3f9f0628865185`
**Body:**
```json
{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "moment_detection_type": "ai_powered",
    "video_quality": "720p",
    "max_clips": 3,
    "clip_duration": 30.0
}
```

## Step 2: Generate Blog Post
**POST** `http://localhost:8000/api/content/generate/`
**Headers:** `Authorization: Token 14ba0fa5f734eaef507417bd1d3f9f0628865185`
**Body:**
```json
{
    "video_request": {{VIDEO_REQUEST_ID_FROM_STEP_1}},
    "template": 1,
    "custom_instructions": "Create an engaging blog post with practical insights",
    "target_audience": "General audience",
    "brand_voice": "friendly",
    "custom_keywords": ["music", "entertainment", "video"]
}
```

## Step 3: Check Status
**GET** `http://localhost:8000/api/content/requests/{{CONTENT_REQUEST_ID}}/`
**Headers:** `Authorization: Token 14ba0fa5f734eaef507417bd1d3f9f0628865185`

## Step 4: Get Generated Content
**GET** `http://localhost:8000/api/content/content/{{GENERATED_CONTENT_ID}}/`
**Headers:** `Authorization: Token 14ba0fa5f734eaef507417bd1d3f9f0628865185`

## Available Templates:
1. SEO Blog Post (template: 1)
2. Podcast Show Notes (template: 2)
3. Twitter Thread (template: 3)
4. LinkedIn Post (template: 4)
5. YouTube Description (template: 5)
6. Email Newsletter (template: 6)
7. Key Takeaways (template: 7)
8. Video Summary (template: 8)

## Pro Tips:
- Replace {{VIDEO_REQUEST_ID}} with actual ID from step 1 response
- Replace {{CONTENT_REQUEST_ID}} with ID from step 2 response
- Use different template IDs to generate different content types
- Check status until it shows "completed"