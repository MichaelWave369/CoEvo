#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-0.8.0}"
ARCHIVE_NAME="coevo-${VERSION}-release.zip"
ARCHIVE_DIR="dist"
ARCHIVE_PATH="${ARCHIVE_DIR}/${ARCHIVE_NAME}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p "$ARCHIVE_DIR"
rm -f "$ARCHIVE_PATH"

zip -r "$ARCHIVE_PATH" . \
  -x "*.git*" \
  -x "*/node_modules/*" \
  -x "*/.venv/*" \
  -x "*/__pycache__/*" \
  -x "*/.pytest_cache/*" \
  -x "*.pyc" \
  -x "*.sqlite" \
  -x "*.sqlite3" \
  -x "web/dist/*" \
  -x "dist/*" \
  -x "server/coevo.db" \
  -x "server/storage/*" \
  -x "*.DS_Store"

echo "Created $ARCHIVE_PATH"
