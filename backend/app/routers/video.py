from __future__ import annotations
import threading

from fastapi import APIRouter, HTTPException

from app.models.schemas import GenerateRequest, JobState, JobStatus, new_job_id, PLATFORM_SPECS
from app.services import job_store
from app.services.pipeline import run_pipeline

router = APIRouter(prefix="/api", tags=["video"])


@router.get("/platforms")
def list_platforms():
    return {key: {**val, "key": key} for key, val in PLATFORM_SPECS.items()}


@router.post("/generate")
def generate_video(req: GenerateRequest):
    job_id = new_job_id()
    job = JobState(job_id=job_id, request=req, status=JobStatus.QUEUED, message="Queued")
    job_store.create_job(job)

    thread = threading.Thread(target=run_pipeline, args=(job_id,), daemon=True)
    thread.start()

    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/jobs/{job_id}")
def cancel_job(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Cooperative cancel: pipeline checks aren't interrupt-based in this
    # lightweight implementation, so we just mark it and let the frontend
    # stop polling; the render thread will finish but the result is
    # simply not surfaced as "done" to the user.
    job_store.update_job(job_id, status=JobStatus.FAILED, message="Cancelled by user", error="cancelled")
    return {"ok": True}
