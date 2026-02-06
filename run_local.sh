#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if [ ! -d "$BACKEND_DIR" ]; then
  echo "No existe $BACKEND_DIR" >&2
  exit 1
fi

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "Creando venv en backend/.venv"
  python3 -m venv "$BACKEND_DIR/.venv"
fi

source "$BACKEND_DIR/.venv/bin/activate"

pip install -r "$BACKEND_DIR/requirements.txt"

PORT="8012"
URL="http://127.0.0.1:${PORT}"
if command -v open >/dev/null 2>&1; then
  (sleep 2 && open "$URL") &
elif command -v xdg-open >/dev/null 2>&1; then
  (sleep 2 && xdg-open "$URL") &
fi

uvicorn --app-dir "$BACKEND_DIR" app.main:app --reload --port "$PORT"
