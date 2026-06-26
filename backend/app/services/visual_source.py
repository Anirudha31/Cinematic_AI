"""
Sources a visual (video clip or image) for each scene.

Priority order:
  1. If TEXT_TO_VIDEO_PROVIDER + TEXT_TO_VIDEO_API_KEY configured -> paid
     text-to-video API hook (stubbed adapters; fill in your provider's
     real endpoint when you have a key).
  2. If PEXELS_API_KEY configured -> free stock video/photo search
     (Pexels free tier: 200 req/hour, 20,000/month).
  3. Always-available fallback -> procedurally generated gradient/
     pattern image with the scene's on-screen text, using Pillow.
     This guarantees the pipeline runs with zero API keys.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFilter

from app.config import get_settings
from app.models.schemas import Scene

settings = get_settings()

PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"
PEXELS_PHOTO_SEARCH = "https://api.pexels.com/v1/search"


def source_visual_for_scene(scene: Scene, work_dir: Path, width: int, height: int) -> Path:
    """Returns a local file path (image or video) to use for this scene."""
    work_dir.mkdir(parents=True, exist_ok=True)

    if settings.TEXT_TO_VIDEO_PROVIDER and settings.TEXT_TO_VIDEO_API_KEY:
        path = _try_text_to_video(scene, work_dir, width, height)
        if path:
            scene.visual_type = "generated_video"
            return path

    if settings.PEXELS_API_KEY:
        path = _try_pexels_video(scene, work_dir, width, height)
        if path:
            scene.visual_type = "stock_video"
            return path
        path = _try_pexels_photo(scene, work_dir)
        if path:
            scene.visual_type = "stock_image"
            return path

    # Guaranteed fallback - always succeeds, no network/keys required.
    scene.visual_type = "generated_image"
    return _generate_placeholder_image(scene, work_dir, width, height)


# ---------------------------------------------------------------------------
# Paid text-to-video hook (stub - wire up your provider here)
# ---------------------------------------------------------------------------

def _try_text_to_video(scene: Scene, work_dir: Path, width: int, height: int) -> Optional[Path]:
    """
    Stub adapter for paid text-to-video providers (Runway, Pika, Stability).
    To enable: set TEXT_TO_VIDEO_PROVIDER and TEXT_TO_VIDEO_API_KEY in .env,
    then implement the actual API call for your chosen provider below.
    Returning None falls through to the free stock/placeholder path.
    """
    provider = settings.TEXT_TO_VIDEO_PROVIDER.lower()
    try:
        if provider == "runway":
            # Example shape only - replace with Runway's real endpoint/payload.
            # resp = requests.post("https://api.runwayml.com/v1/generate", ...)
            return None
        elif provider == "pika":
            return None
        elif provider == "stability":
            return None
    except Exception as e:
        print(f"[visual_source] text-to-video provider '{provider}' failed: {e}")
    return None


# ---------------------------------------------------------------------------
# Free stock footage via Pexels
# ---------------------------------------------------------------------------

def _try_pexels_video(scene: Scene, work_dir: Path, width: int, height: int) -> Optional[Path]:
    try:
        orientation = "portrait" if height > width else "landscape"
        r = requests.get(
            PEXELS_VIDEO_SEARCH,
            headers={"Authorization": settings.PEXELS_API_KEY},
            params={"query": scene.visual_query, "per_page": 3, "orientation": orientation},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        videos = data.get("videos", [])
        if not videos:
            return None
        # pick a reasonably sized file (avoid 4K to keep renders fast)
        best_file = None
        for v in videos:
            for f in v.get("video_files", []):
                if f.get("width") and 480 <= f["width"] <= 1280:
                    best_file = f
                    break
            if best_file:
                break
        if not best_file:
            best_file = videos[0]["video_files"][0]

        out_path = work_dir / f"scene_{scene.index}_{_hash(scene.visual_query)}.mp4"
        _download(best_file["link"], out_path)
        return out_path
    except Exception as e:
        print(f"[visual_source] Pexels video search failed: {e}")
        return None


def _try_pexels_photo(scene: Scene, work_dir: Path) -> Optional[Path]:
    try:
        r = requests.get(
            PEXELS_PHOTO_SEARCH,
            headers={"Authorization": settings.PEXELS_API_KEY},
            params={"query": scene.visual_query, "per_page": 3},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        photos = data.get("photos", [])
        if not photos:
            return None
        url = photos[0]["src"]["large2x"]
        out_path = work_dir / f"scene_{scene.index}_{_hash(scene.visual_query)}.jpg"
        _download(url, out_path)
        return out_path
    except Exception as e:
        print(f"[visual_source] Pexels photo search failed: {e}")
        return None


def _download(url: str, out_path: Path) -> None:
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Guaranteed free fallback: generated gradient placeholder
# ---------------------------------------------------------------------------

_PALETTES = [
    ((255, 90, 54), (14, 15, 18)),
    ((61, 220, 132), (12, 18, 16)),
    ((90, 140, 255), (12, 14, 22)),
    ((255, 200, 60), (20, 16, 10)),
    ((200, 80, 220), (18, 12, 22)),
]


def _generate_placeholder_image(scene: Scene, work_dir: Path, width: int, height: int) -> Path:
    seed = int(_hash(scene.visual_query), 16)
    c1, c2 = _PALETTES[seed % len(_PALETTES)]

    img = Image.new("RGB", (width, height), c2)
    draw = ImageDraw.Draw(img)

    # diagonal gradient
    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # soft circular highlight for visual interest
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    cx, cy = width * 0.5, height * 0.35
    radius = max(width, height) * 0.4
    odraw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(255, 255, 255, 28))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius / 3))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    out_path = work_dir / f"scene_{scene.index}_{_hash(scene.visual_query)}.jpg"
    img.save(out_path, quality=90)
    return out_path
