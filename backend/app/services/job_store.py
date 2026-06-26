"""
Minimal job store.

No external database needed -- jobs live in memory for speed and are
mirrored to a JSON file on disk so they survive a server restart.
This keeps the app free to run anywhere (no Postgres/Redis required)
while still being reasonably robust.
"""
from __future__ import annotations
import json
import threading
from pathlib import Path
from typing import Optional, Dict

from app.models.schemas import JobState
from app.config import get_settings

settings = get_settings()
_lock = threading.Lock()
_jobs: Dict[str, JobState] = {}

_JOBS_DIR = Path(settings.STORAGE_DIR) / "jobs"
_JOBS_DIR.mkdir(parents=True, exist_ok=True)


def _job_file(job_id: str) -> Path:
    return _JOBS_DIR / f"{job_id}.json"


def create_job(job: JobState) -> None:
    with _lock:
        _jobs[job.job_id] = job
        _persist(job)


def get_job(job_id: str) -> Optional[JobState]:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            return job
    # fall back to disk (e.g. after restart)
    f = _job_file(job_id)
    if f.exists():
        data = json.loads(f.read_text())
        job = JobState(**data)
        with _lock:
            _jobs[job_id] = job
        return job
    return None


def update_job(job_id: str, **fields) -> Optional[JobState]:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        for k, v in fields.items():
            setattr(job, k, v)
        job.touch()
        _persist(job)
        return job


def _persist(job: JobState) -> None:
    try:
        _job_file(job.job_id).write_text(job.model_dump_json(indent=2))
    except Exception:
        pass  # persistence is best-effort; in-memory copy is source of truth at runtime
