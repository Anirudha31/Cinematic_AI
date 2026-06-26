#!/usr/bin/env bash
# Convenience script: sets up and runs the ReelForge backend.
# Usage: ./run_backend.sh
set -e

cd "$(dirname "$0")/backend"

if ! command -v ffmpeg &> /dev/null; then
  echo "ffmpeg not found. Please install it first:"
  echo "  Ubuntu/Debian: sudo apt install ffmpeg"
  echo "  macOS:         brew install ffmpeg"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing dependencies (first run only takes a few minutes)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example (edit it to add optional API keys)"
fi

echo ""
echo "Starting backend at http://localhost:8000  (docs at /docs)"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
