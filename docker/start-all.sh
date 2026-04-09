#!/usr/bin/env bash
set -euo pipefail

cd /app

BACKEND_PID=""
BOT_PID=""

cleanup() {
  if [[ -n "${BOT_PID}" ]] && kill -0 "${BOT_PID}" 2>/dev/null; then
    kill "${BOT_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
  wait "${BOT_PID}" 2>/dev/null || true
  wait "${BACKEND_PID}" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

export CAVA_ADDRESS="${CAVA_ADDRESS:-0.0.0.0}"
export CAVA_PORT="${CAVA_PORT:-8000}"
export MENU_API_BASE_URL="${MENU_API_BASE_URL:-http://127.0.0.1:8000}"

python -m cava_backend.run &
BACKEND_PID=$!

python - <<'PY'
import sys
import time
import urllib.request

url = "http://127.0.0.1:8000/health"
deadline = time.time() + 60

while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                sys.exit(0)
    except Exception:
        time.sleep(1)

print("Backend did not become healthy in time.", file=sys.stderr)
sys.exit(1)
PY

if [[ -n "${BOT_TOKEN:-}" ]] && [[ "${BOT_TOKEN}" != "<telegram-bot-token>" ]]; then
  python bot/bot.py &
  BOT_PID=$!
else
  echo "BOT_TOKEN is not configured, so the Telegram bot was skipped."
fi

if [[ -n "${BOT_PID}" ]]; then
  wait -n "${BACKEND_PID}" "${BOT_PID}"
else
  wait "${BACKEND_PID}"
fi
