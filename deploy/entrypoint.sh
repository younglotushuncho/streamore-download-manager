#!/bin/sh
set -e

# ──────────────────────────────────────────────────────────────────
# Entrypoint: launch aria2 RPC (localhost-only), then gunicorn
# ──────────────────────────────────────────────────────────────────

ARIA2_RPC_SECRET="${ARIA2_RPC_SECRET:-changeme_secret}"
ARIA2_DIR="${DOWNLOAD_PATH:-/app/downloads}"
ARIA2_PORT="${ARIA2_PORT:-6800}"

echo "[entrypoint] Starting aria2 RPC on 127.0.0.1:${ARIA2_PORT} ..."
aria2c \
  --enable-rpc \
  --rpc-listen-all=false \
  --rpc-listen-port="${ARIA2_PORT}" \
  --rpc-secret="${ARIA2_RPC_SECRET}" \
  --dir="${ARIA2_DIR}" \
  --max-concurrent-downloads=3 \
  --log=/app/data/aria2.log \
  --daemon \
  --quiet
echo "[entrypoint] aria2 started."

echo "[entrypoint] Starting gunicorn on 0.0.0.0:${FLASK_PORT:-5000} ..."
exec gunicorn \
  --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
  --workers 1 \
  --bind "0.0.0.0:${FLASK_PORT:-5000}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  "backend.app:app"
