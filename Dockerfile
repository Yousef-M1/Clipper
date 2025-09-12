FROM python:3.11-slim
LABEL maintainer="Yousef"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Copy only requirements first (to maximize caching)
COPY ./requirements.txt /app/requirements.txt

# 2. Install system dependencies + FFmpeg + additional moviepy dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq5 \
    gcc \
    python3-dev \
    curl \
    ca-certificates \
    git \
    # Additional dependencies that moviepy might need
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# 3. Set up virtual environment + install moviepy first
RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    /py/bin/pip install moviepy==1.0.3 && \
    /py/bin/pip install -r /app/requirements.txt

ENV PATH="/py/bin:$PATH"

# 4. Now copy the rest of the project (app code)
COPY . /app

EXPOSE 8000

# Optional non-root user (enable later in prod)
# RUN useradd -M -r -s /usr/sbin/nologin django-user
# USER django-user