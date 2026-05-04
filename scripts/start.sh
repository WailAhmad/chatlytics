#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Chatlytics — single-command local start
#  Runs backend (FastAPI) and frontend (Next.js) in ONE terminal.
#  Press Ctrl+C once to shut down both.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3100}"

# ── colours ──────────────────────────────────────────────────
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No colour

BACKEND_TAG="${CYAN}[backend]${NC} "
FRONTEND_TAG="${GREEN}[frontend]${NC}"

# ── cleanup on exit ──────────────────────────────────────────
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo -e "${YELLOW}⏹  Shutting down...${NC}"
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && echo -e "${FRONTEND_TAG} stopped"
  [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null && echo -e "${BACKEND_TAG} stopped"
  # kill any remaining children
  kill 0 2>/dev/null || true
  echo -e "${GREEN}✓  All processes stopped.${NC}"
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# ── kill stale processes ─────────────────────────────────────
echo -e "${YELLOW}Cleaning stale processes on ports $BACKEND_PORT and $FRONTEND_PORT...${NC}"
lsof -ti:"$BACKEND_PORT" | xargs kill -9 2>/dev/null || true
lsof -ti:"$FRONTEND_PORT" | xargs kill -9 2>/dev/null || true
sleep 1

# ── validate backend venv ───────────────────────────────────
if [ ! -x "$ROOT_DIR/backend/venv/bin/python" ]; then
  echo -e "${RED}✗  Missing backend virtualenv.${NC}"
  echo "  Run:  python3 -m venv backend/venv && source backend/venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

# ── install frontend deps if needed ─────────────────────────
if [ ! -d "$ROOT_DIR/web/node_modules" ]; then
  echo -e "${FRONTEND_TAG} Installing npm dependencies..."
  (cd "$ROOT_DIR/web" && npm install)
fi

# ── banner ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║         ${CYAN}⚡ Chatlytics — Local Dev${NC}${BOLD}            ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}Backend${NC}  → http://localhost:${BACKEND_PORT}"
echo -e "  ${GREEN}Frontend${NC} → http://localhost:${FRONTEND_PORT}"
echo -e "  ${YELLOW}Stop${NC}     → Ctrl+C"
echo ""

# ── start backend ────────────────────────────────────────────
echo -e "${BACKEND_TAG} Starting FastAPI on port ${BACKEND_PORT}..."
(
  cd "$ROOT_DIR"
  backend/venv/bin/python -m uvicorn backend.main:app \
    --host 127.0.0.1 --port "$BACKEND_PORT" --reload 2>&1 | \
    sed "s/^/$(printf "${CYAN}[backend]${NC} ")/"
) &
BACKEND_PID=$!

# give the backend a moment to bind
sleep 2

# ── start frontend ───────────────────────────────────────────
echo -e "${FRONTEND_TAG} Starting Next.js on port ${FRONTEND_PORT}..."
(
  cd "$ROOT_DIR/web"
  npx next dev --port "$FRONTEND_PORT" 2>&1 | \
    sed "s/^/$(printf "${GREEN}[frontend]${NC} ")/"
) &
FRONTEND_PID=$!

# ── wait for both ────────────────────────────────────────────
wait
