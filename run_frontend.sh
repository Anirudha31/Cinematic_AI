#!/usr/bin/env bash
# Convenience script: serves the ReelForge frontend on http://localhost:8080
set -e
cd "$(dirname "$0")/frontend"
echo "Serving frontend at http://localhost:8080"
python3 -m http.server 8080
