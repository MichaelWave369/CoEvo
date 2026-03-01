#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-0.8.0}"
ARCHIVE_NAME="coevo-${VERSION}-release.zip"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

rm -f "$ARCHIVE_NAME"

zip -r "$ARCHIVE_NAME" . \
  -x "*.git*" \
  -x "*/node_modules/*" \
  -x "*/.venv/*" \
  -x "*/__pycache__/*" \
  -x "*.pyc" \
  -x "web/dist/*" \
  -x "server/coevo.db" \
  -x "server/storage/*" \
  -x "*.DS_Store"

echo "Created $ARCHIVE_NAME"
