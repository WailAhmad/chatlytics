#!/usr/bin/env bash
# Starts backend (port 8000) and frontend (port 3000) in two macOS Terminal windows.
# Kills any stale processes on those ports first.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Cleaning stale processes on ports 8000 and 3000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 1

echo "Opening backend terminal..."
osascript <<EOF
tell application "Terminal"
  do script "cd '$ROOT_DIR' && ./scripts/restart_backend.sh"
  activate
end tell
EOF

sleep 2

echo "Opening frontend terminal..."
osascript <<EOF
tell application "Terminal"
  do script "cd '$ROOT_DIR/web' && npm run dev"
  activate
end tell
EOF

echo ""
echo "Done. Backend → http://localhost:8000/health"
echo "     Frontend → http://localhost:3000"
