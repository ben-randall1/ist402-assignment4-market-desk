#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -f frontend/dist/index.html ]; then
  echo 'Build the frontend first: npm ci --prefix frontend && npm run build --prefix frontend'
  exit 1
fi
exec .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
