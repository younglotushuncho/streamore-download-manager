# ── Stage 1: build ────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps for curl-cffi, Pillow, lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ libssl-dev libffi-dev \
        libjpeg-dev zlib1g-dev libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt \
 && pip install --no-cache-dir --prefix=/install gunicorn flask-socketio[gevent] gevent


# ── Stage 2: runtime ──────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime libs only
RUN apt-get update && apt-get install -y --no-install-recommends \
        libssl3 libffi8 libjpeg62-turbo zlib1g libxml2 libxslt1.1 \
        aria2 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy project source
COPY backend/   ./backend/
COPY shared/    ./shared/

# Create required directories (volume mount points - data/ is on Fly volume)
RUN mkdir -p /app/data/cache/posters /app/downloads

# Environment defaults (override via fly secrets / docker -e)
ENV FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5000 \
    FLASK_DEBUG=False \
    DOWNLOAD_PATH=/app/downloads \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 5000

# Entrypoint: start aria2 daemon in background then serve via gunicorn
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
