@echo off
REM Convenience script: sets up and runs the Cinematic AI backend on Windows.
REM Usage: run_backend.bat

cd "%~dp0backend"

where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo ffmpeg not found. Please install it first ^(see https://ffmpeg.org/download.html^)
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing dependencies ^(first run only takes a few minutes^)...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if not exist ".env" (
    copy .env.example .env
    echo Created .env from .env.example ^(edit it to add optional API keys^)
)

echo.
echo Starting backend at http://localhost:8000  (docs at /docs)
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
