#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8000}"

cd "$ROOT_DIR"

if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN || true)"
  if [ -n "$PIDS" ]; then
    echo "Stopping stale backend process(es) on port $PORT: $PIDS"
    kill $PIDS || true
    sleep 1
  fi
fi

if [ ! -x "backend/venv/bin/python" ]; then
  echo "Missing backend virtualenv. Run: python3 -m venv backend/venv && source backend/venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

echo "Starting backend from: $ROOT_DIR"
echo "Health endpoint will show the serving cwd and git commit."
exec backend/venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port "$PORT" --reload
