#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi

if ! .venv/bin/python -c "import fastapi, sqlalchemy, pdfplumber, openpyxl, reportlab" 2>/dev/null; then
  .venv/bin/pip install -r backend/requirements.txt
fi

if [[ ! -d node_modules ]]; then
  npm install
fi

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

(
  cd backend
  ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

printf '\nFarmaHub iniciado. Abra http://127.0.0.1:3000 no navegador.\n\n'
npm run dev -- --host 127.0.0.1 --port 3000
