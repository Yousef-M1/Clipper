# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This is a Django-based video clipping SaaS platform that processes videos to automatically create engaging clips with AI-powered moment detection and styled captions. The project is containerized with Docker Compose and uses Celery for background task processing.

### Core Architecture:
- **Django REST API** with PostgreSQL database
- **Celery workers** with Redis broker for video processing tasks
- **AI-powered video processing** using OpenAI Whisper for transcription and custom AI moment detection
- **FFmpeg-based video processing** with quality control and compression options
- **Multi-tenant user system** with credit-based usage limits

### App Structure:
- `app/` - Django project configuration and settings
- `core/` - Core models (User, VideoRequest, Clip, UserCredits, Plan)
- `clipper/` - Main video processing app with views, tasks, and utilities
- `user/` - User management functionality
- `clips/` - Generated video clips storage
- `media/` - User uploaded media files

## Development Commands

### Docker Development:
```bash
# Start all services (web, worker, db, redis)
docker-compose up

# Start with monitoring (includes Flower for Celery monitoring)
docker-compose --profile monitoring up

# Stop services
docker-compose down

# View logs
docker-compose logs -f web
docker-compose logs -f worker
```

### Django Commands (inside container):
```bash
# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell

# Run tests (if test suite exists)
python manage.py test

# Collect static files
python manage.py collectstatic
```

### Celery Commands (for development):
```bash
# Start Celery worker manually (if not using Docker)
celery -A app worker --loglevel=info --concurrency=2

# Start Flower monitoring
celery -A app flower

# Purge all tasks
celery -A app purge
```

## Key Models and Data Flow

### Video Processing Pipeline:
1. **VideoRequest** created with URL and processing settings
2. **Celery task** downloads video and transcribes with Whisper
3. **AI moment detection** or fixed intervals identify engaging segments
4. **Clips** generated with styled captions and quality control
5. **User credits** deducted based on plan and clips created

### Important Models:
- `VideoRequest` - Stores processing settings, status, and metadata
- `Clip` - Individual video clips with timing, quality, and engagement data
- `User` - Custom email-based user model with credit system
- `UserCredits` - Tracks usage and plan limits
- `CaptionSettings` - Customizable caption styling options

## Video Processing Features

### AI Moment Detection:
- Uses custom AI analysis to identify engaging video segments
- Falls back to fixed intervals if AI detection fails
- Configurable via `moment_detection_type` setting

### Quality Control:
- Multiple video quality presets (480p-2160p)
- Three compression levels: high_quality, balanced, compressed
- File size estimation and optimization

### Caption Styling:
- Multiple preset styles (modern_purple, tiktok_style, youtube_style, etc.)
- Word-level highlighting support
- Customizable fonts, colors, and animations

### Processing Settings:
All configurable via `processing_settings` in VideoRequest:
- `moment_detection_type`: 'ai_powered' or 'fixed_intervals'
- `clip_duration`: 5.0-120.0 seconds
- `max_clips`: 1-50 clips
- `video_quality`: '480p', '720p', '1080p', '1440p', '2160p'
- `compression_level`: 'high_quality', 'balanced', 'compressed'
- `caption_style`: Multiple style options available
- `enable_word_highlighting`: Boolean for word-level captions

## Environment Configuration

Required environment variables (set in `.env` or docker-compose.yml):
- `OPENAI_API_KEY` - For Whisper transcription and AI analysis
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - PostgreSQL config
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` - Redis URLs
- `DEBUG` - Django debug mode

## Key Processing Modules

### `clipper/tasks/tasks.py`:
- Main video processing logic
- Celery task definitions
- Error handling and retries
- File cleanup management

### `clipper/ai_moments.py`:
- AI-powered moment detection
- Engagement score calculation
- Moment tagging and classification

### `clipper/video_quality.py`:
- Video quality management
- Compression settings
- File size estimation

### `clipper/caption_styles.py`:
- Caption style templates
- Word-level subtitle generation
- Animation and formatting options

### `clipper/utils.py`:
- Video download utilities
- Whisper transcription
- FFmpeg operations
- Audio validation

## Database Configuration

PostgreSQL is used for persistence with Redis for caching and Celery task queue. The custom User model uses email authentication. Video processing results are stored with comprehensive metadata for analytics and re-processing.

## API Endpoints

The REST API provides endpoints for:
- Creating video requests with custom settings
- Retrieving processing status and clips
- Getting available quality/style options
- Reprocessing videos with different settings
- Processing cost estimation

## File Storage

- Original videos: Downloaded temporarily and cleaned up after processing
- Generated clips: Stored in `/media/clips/` with Django FileField
- Temporary processing: Uses system temp directory with cleanup
- Logs: Stored in `/logs/` directory with rotation