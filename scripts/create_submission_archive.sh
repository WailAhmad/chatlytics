#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCHIVE_PATH="${1:-$ROOT_DIR/aldar-conversational-analytics-submission.zip}"

cd "$ROOT_DIR"

if ! command -v zip >/dev/null 2>&1; then
  echo "zip is required to create the submission archive."
  exit 1
fi

rm -f "$ARCHIVE_PATH"

zip -r "$ARCHIVE_PATH" . \
  -x ".git/*" \
  -x ".env" \
  -x ".claude/*" \
  -x "backend/venv/*" \
  -x "web/node_modules/*" \
  -x "web/.next/*" \
  -x "__pycache__/*" \
  -x "*/__pycache__/*" \
  -x ".pytest_cache/*" \
  -x "data/active_dataset.csv" \
  -x ".DS_Store" \
  -x "*/.DS_Store" \
  -x "aldar-conversational-analytics-submission.zip"

echo "Created $ARCHIVE_PATH"
