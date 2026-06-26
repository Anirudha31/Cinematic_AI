from __future__ import annotations
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import get_settings
from app.routers import video, download

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered video creation and editing API: prompt-to-video, "
                "auto voiceover, auto captions, auto music, auto thumbnails.",
    version="1.0.0",
)

origins = ["*"] if settings.CORS_ORIGINS.strip() == "*" else [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Speeds up JSON/job-status polling responses over the wire.
app.add_middleware(GZipMiddleware, minimum_size=512)

# Ensure storage directories exist on boot
for sub in ("uploads", "renders", "temp", "jobs"):
    Path(settings.STORAGE_DIR, sub).mkdir(parents=True, exist_ok=True)

app.include_router(video.router)
app.include_router(download.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
