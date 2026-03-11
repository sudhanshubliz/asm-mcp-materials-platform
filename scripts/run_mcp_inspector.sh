#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v npx >/dev/null 2>&1; then
  echo "Error: npx is required. Install Node.js (includes npm/npx)." >&2
  exit 1
fi

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo "Error: Python interpreter not found at $ROOT_DIR/.venv/bin/python" >&2
  exit 1
fi

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ROOT_DIR/.env"
  set +a
fi

if [ -z "${MATERIALS_API_KEY:-}" ]; then
  echo "Error: MATERIALS_API_KEY is not set. Add it to .env or export it first." >&2
  exit 1
fi

cd "$ROOT_DIR"
exec npx -y @modelcontextprotocol/inspector "$ROOT_DIR/.venv/bin/python" -m app.main
