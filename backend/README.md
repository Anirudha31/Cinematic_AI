# Cinematic AI Backend

Python (FastAPI) backend that powers prompt-to-video generation: script
planning, footage sourcing, AI voiceover, auto captions, background music,
final render, and thumbnail generation.

**Works fully for free with zero API keys.** Optional keys upgrade specific
stages (smarter scripts via Claude, real stock footage via Pexels) but
nothing is required to run it end-to-end.

## Quick start (local, no Docker)

Requires Python 3.11+ and `ffmpeg` installed on your system.

```bash
# 1. Install ffmpeg (required for video rendering)
#    Ubuntu/Debian: sudo apt install ffmpeg
#    macOS:         brew install ffmpeg
#    Windows:       choco install ffmpeg   (or download from ffmpeg.org)

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) configure API keys
cp .env.example .env
# edit .env if you have an Anthropic or Pexels key — otherwise leave blank

# 5. Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is now live at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`.

## Quick start (Docker)

From the project root (one level up from this folder):

```bash
docker compose up --build
```

This starts the backend on port 8000 and serves the frontend on port 8080.

## Architecture

```
app/
  main.py              FastAPI app, CORS, router registration
  config.py            All settings, all optional API keys
  models/schemas.py    Pydantic request/response models, job state
  routers/
    video.py           POST /api/generate, GET /api/jobs/{id}
    download.py        GET /api/download/{id}, GET /api/thumbnail/{id}
  services/
    job_store.py       In-memory + disk-backed job tracking (no DB needed)
    script_planner.py  Prompt -> script/scenes (Claude API or template fallback)
    visual_source.py   Scene -> footage (Pexels free tier or generated placeholder)
    tts_service.py     Narration -> voiceover audio (edge-tts, free)
    caption_service.py Voiceover -> timed captions (faster-whisper, local & free)
    music_service.py   Mood -> background track (from assets/music/<mood>/)
    video_renderer.py  Assembles everything into the final .mp4 (moviepy/ffmpeg)
    thumbnail_service.py  Final video -> styled thumbnail image
    pipeline.py         Orchestrates all of the above per job, in a background thread
```

## How a request flows

1. Frontend `POST /api/generate` with a prompt + platform + options.
2. Backend immediately returns a `job_id` and starts a background thread.
3. Frontend polls `GET /api/jobs/{job_id}` every ~1.8s for progress (0-100)
   and a human-readable stage message.
4. When `status == "done"`, frontend points a `<video>` tag and a download
   link at `GET /api/download/{job_id}`.

## Performance notes

- Rendering uses `libx264` with `preset="veryfast"` — the single biggest
  speed lever in the pipeline. Lower to `"ultrafast"` in
  `app/services/video_renderer.py` if you need it faster still (slightly
  larger file size, marginally lower quality).
- `faster-whisper` runs the `"base"` model by default (good speed/accuracy
  balance on CPU). Switch to `"tiny"` in `.env` (`WHISPER_MODEL_SIZE=tiny`)
  for faster captioning on low-power servers.
- Jobs run in background threads, not blocking the request/response cycle,
  so the API itself stays responsive even while a render is in progress.
- `MAX_CONCURRENT_RENDERS` in `config.py` is a soft guideline for your own
  deployment sizing — wire it into a semaphore in `pipeline.py` if you need
  to hard-cap concurrent renders on a small server.

## Adding background music

See `assets/music/README.md` — drop royalty-free tracks into the mood
folders and the app will start using them automatically.

## Going further (optional upgrades)

- **Smarter scripts**: add `ANTHROPIC_API_KEY` to `.env`.
- **Real stock footage**: add `PEXELS_API_KEY` (free tier, get one at
  pexels.com/api).
- **True AI-generated video clips**: set `TEXT_TO_VIDEO_PROVIDER` and
  `TEXT_TO_VIDEO_API_KEY`, then implement the actual API call in
  `app/services/visual_source.py::_try_text_to_video` for your chosen
  provider (Runway, Pika, Stability) — the hook is already wired into
  the pipeline, just needs the provider-specific request/response code.


