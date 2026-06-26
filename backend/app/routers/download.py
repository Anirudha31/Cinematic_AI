from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.schemas import JobStatus
from app.services import job_store

router = APIRouter(prefix="/api", tags=["download"])


@router.get("/download/{job_id}")
def download_video(job_id: str):
    job = job_store.get_job(job_id)
    if not job or job.status != JobStatus.DONE or not job.video_path:
        raise HTTPException(status_code=404, detail="Video not ready or not found")
    path = Path(job.video_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video file missing on disk")
    filename = f"{(job.plan.title if job.plan else 'video').strip().replace(' ', '_')[:50]}.mp4"
    return FileResponse(path, media_type="video/mp4", filename=filename)


@router.get("/thumbnail/{job_id}")
def download_thumbnail(job_id: str):
    job = job_store.get_job(job_id)
    if not job or not job.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not ready or not found")
    path = Path(job.thumbnail_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file missing on disk")
    return FileResponse(path, media_type="image/jpeg", filename=f"{job_id}_thumbnail.jpg")
