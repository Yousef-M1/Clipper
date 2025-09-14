FROM python:3.11-slim
LABEL maintainer="Yousef"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 1. Copy only requirements first (to maximize caching)
COPY ./requirements.txt /app/requirements.txt

# 2. Install system dependencies + FFmpeg with codec support
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essential system packages
    gcc \
    python3-dev \
    libpq5 \
    curl \
    ca-certificates \
    git \
    wget \
    # FFmpeg with codec support - CRITICAL for audio
    ffmpeg \
    # Available audio/video libraries
    libmp3lame0 \
    libopus0 \
    libvorbis0a \
    libvorbisenc2 \
    libtheora0 \
    libx264-164 \
    # Additional dependencies for moviepy
    imagemagick \
    # For yt-dlp and headless processing
    xvfb \
    # Computer vision dependencies for OpenCV
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    # Python compilation dependencies
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 3. Set up virtual environment and install Python packages
RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip setuptools wheel

# Install packages in order of stability (most stable first)
RUN /py/bin/pip install --no-cache-dir \
    # Core dependencies first
    django==5.0.2 \
    psycopg2-binary \
    redis \
    celery[redis] \
    # Video processing (install these separately for better error handling)
    imageio[ffmpeg] \
    imageio-ffmpeg \
    && /py/bin/pip install --no-cache-dir moviepy==1.0.3

# Install computer vision dependencies for scene detection
RUN /py/bin/pip install --no-cache-dir \
    opencv-python-headless==4.8.1.78 \
    numpy>=1.24.0 \
    scikit-learn>=1.3.0

# Install social media publishing dependencies
RUN /py/bin/pip install --no-cache-dir \
    requests>=2.31.0 \
    requests-oauthlib>=1.3.1 \
    python-dateutil>=2.8.2 \
    Pillow>=10.0.0

# Install remaining requirements
RUN /py/bin/pip install --no-cache-dir -r /app/requirements.txt

ENV PATH="/py/bin:$PATH"

# 4. Configure ImageMagick policy for video processing
RUN for policy_file in /etc/ImageMagick-6/policy.xml /etc/ImageMagick-7/policy.xml /etc/ImageMagick/policy.xml /usr/local/etc/ImageMagick-6/policy.xml /usr/local/etc/ImageMagick-7/policy.xml; do \
    if [ -f "$policy_file" ]; then \
        sed -i 's/policy domain="path" rights="none" pattern="@\*"/policy domain="path" rights="read|write" pattern="@*"/' "$policy_file"; \
        echo "Updated ImageMagick policy at $policy_file"; \
        break; \
    fi; \
done || echo "No ImageMagick policy file found - skipping configuration"

# 5. Create necessary directories
RUN mkdir -p /app/media /app/logs /tmp/video_processing

# 6. Copy the project code
COPY . /app

# 7. Set proper permissions
RUN chmod +x /app/manage.py

# 8. Test FFmpeg installation
RUN ffmpeg -version && ffprobe -version

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/admin/ || exit 1

# Optional: Create non-root user for production
RUN groupadd -r django && useradd -r -g django django-user
RUN chown -R django-user:django /app
# USER django-user  # Uncomment for production