# ReelForge — AI Video Studio

Type a prompt, get a fully edited, ready-to-post video: script, scenes,
footage, AI voiceover, auto captions, background music, and a thumbnail —
sized correctly for YouTube (long-form and Shorts), Instagram Reels,
TikTok, or Facebook.

**Frontend** and **backend** are kept completely separate (`/frontend`
and `/backend`), so you can deploy, scale, or replace either one
independently.

## Free by default

Every stage of the pipeline has a free, working path with zero API
keys configured:

| Stage          | Free path (default)                  | Optional upgrade               |
|----------------|---------------------------------------|---------------------------------|
| Script/scenes  | Template-based planner                | Claude API (smarter scripts)    |
| Footage        | Generated placeholder visuals         | Pexels API (real stock footage) |
| Voiceover      | edge-tts (free neural voices)         | -                                |
| Captions       | faster-whisper (runs locally, free)   | -                                |
| Music          | Your own royalty-free library         | -                                |
| Video clips    | Stock/generated images                | Paid text-to-video API (Runway/Pika/Stability) |

Nothing here requires a credit card to try.

## Project structure

```
reelforge/
  frontend/          HTML + CSS + vanilla JS, no build step
  backend/            Python (FastAPI) API + video pipeline
  docker-compose.yml  Runs both together
```

## Fastest way to run it: Docker

```bash
docker compose up --build
```
- Frontend at http://localhost:8080
- Backend API at http://localhost:8000 (docs at /docs)

## Running without Docker

**Backend:**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional: add API keys here
uvicorn app.main:app --reload --port 8000
```
You'll also need `ffmpeg` installed on your system (see backend/README.md).

**Frontend** (in a second terminal):
```bash
cd frontend
python3 -m http.server 8080
```
Visit http://localhost:8080.

## Deploying for real use

- **Backend**: any VPS/cloud host that can run Docker (DigitalOcean,
  Render, Railway, AWS EC2, etc). Use the provided `Dockerfile`. Make
  sure the host has at least 2 CPU cores for reasonable render speed -
  video encoding is CPU-bound.
- **Frontend**: any static host (Netlify, Vercel, Cloudflare Pages,
  GitHub Pages, S3+CloudFront) - it's just static files. Set
  `window.REELFORGE_API_BASE` to your backend's public URL (see
  `frontend/README.md`).

## Updating / extending

Both halves are intentionally simple and modular so you (or future-you,
or another developer) can extend them without archaeology:

- Add a platform: one entry in `backend/app/models/schemas.py` in
  `PLATFORM_SPECS`. The frontend picks it up automatically.
- Add a voice/tone: one entry in `backend/app/services/tts_service.py` in
  `VOICE_PRESETS`.
- Swap the script-writing AI: edit `backend/app/services/script_planner.py`.
- Add real stock footage: get a free Pexels key, drop it in `.env`.
- Add music: drop mp3s into `backend/assets/music/<mood>/`.
- Re-skin the site: everything is CSS variables in
  `frontend/css/styles.css`.

## Performance

- The backend returns a `job_id` immediately and renders in a background
  thread - the UI never blocks waiting on a single long HTTP request.
- The frontend polls job status roughly every 1.8 seconds, so progress
  updates feel close to real-time without hammering the server.
- Video encoding uses `libx264` at `preset=veryfast` - tunable in
  `backend/app/services/video_renderer.py` if you want to trade
  encode speed for quality (or vice versa).
- Realistic expectation: a render is bounded by your server's CPU. A
  30-60 second vertical video typically renders in well under a minute
  on a modest 2-4 core server; longer/long-form videos take
  proportionally longer.

## Honest limitations

- This does not generate true AI video clips (like Sora/Runway) out of
  the box for free - that technology isn't free anywhere. The free path
  uses stock footage + generated placeholder visuals matched to your
  script. The paid-API hook is wired in if you want to add one later.
- "Fast" here means "as fast as your server's CPU can encode video" -
  it's optimized, not instant. A laptop will render slower than a
  multi-core cloud server.
