"""
Shared data models for the video pipeline.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
import time
import uuid


Platform = Literal["youtube_long", "youtube_short", "instagram_reel", "tiktok", "facebook", "custom"]

PLATFORM_SPECS = {
    "youtube_long":   {"w": 1920, "h": 1080, "max_seconds": 1200, "label": "YouTube (Long)"},
    "youtube_short":  {"w": 1080, "h": 1920, "max_seconds": 60,   "label": "YouTube Shorts"},
    "instagram_reel": {"w": 1080, "h": 1920, "max_seconds": 90,   "label": "Instagram Reel"},
    "tiktok":         {"w": 1080, "h": 1920, "max_seconds": 180,  "label": "TikTok"},
    "facebook":       {"w": 1280, "h": 720,  "max_seconds": 240,  "label": "Facebook"},
    "custom":         {"w": 1080, "h": 1920, "max_seconds": 180,  "label": "Custom"},
}


class JobStatus(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"          # AI writing script/scenes
    SOURCING = "sourcing"          # fetching footage/images
    VOICING = "voicing"            # generating TTS voiceover
    CAPTIONING = "captioning"      # running speech-to-text for subtitles
    SCORING = "scoring"            # picking + mixing background music
    RENDERING = "rendering"        # ffmpeg/moviepy assembly
    THUMBNAIL = "thumbnail"        # generating thumbnail
    DONE = "done"
    FAILED = "failed"


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    platform: Platform = "instagram_reel"
    duration_seconds: Optional[int] = Field(None, ge=5, le=1200)
    voice: Optional[str] = None
    tone: Optional[str] = "energetic"  # energetic | calm | professional | funny | dramatic
    add_captions: bool = True
    add_music: bool = True
    add_voiceover: bool = True
    add_thumbnail: bool = True
    music_mood: Optional[str] = None  # auto if None
    aspect_override: Optional[str] = None  # "9:16" | "16:9" | "1:1"


class Scene(BaseModel):
    index: int
    narration: str
    on_screen_text: Optional[str] = None
    visual_query: str
    duration_seconds: float = 4.0
    visual_source: Optional[str] = None  # filled in after sourcing
    visual_type: Optional[str] = None    # "stock_video" | "stock_image" | "generated_image"


class ScriptPlan(BaseModel):
    title: str
    hook: str
    scenes: List[Scene]
    cta: Optional[str] = None
    suggested_caption: Optional[str] = None
    suggested_hashtags: List[str] = []
    music_mood: str = "upbeat"


class JobState(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0  # 0-100
    message: str = "Queued"
    request: GenerateRequest
    plan: Optional[ScriptPlan] = None
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def touch(self):
        self.updated_at = time.time()


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]
