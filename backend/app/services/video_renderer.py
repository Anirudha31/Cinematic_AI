"""
Assembles the final video from:
  - per-scene visuals (image or short video clip)
  - a single voiceover audio track (or per-scene, concatenated)
  - background music (mixed under the voiceover at lower volume)
  - burned-in animated captions

Performance notes (this is the part that determines "how fast it runs"):
  - We render at the platform's native resolution, not upscaled.
  - We use libx264 with preset="veryfast" and threads=N to balance
    speed vs quality -- this is the single biggest speed lever.
  - Images are held as static clips (cheaper than re-encoding video
    sources) unless a stock video clip was sourced for that scene.
  - Caption text is rendered once per unique cue via PIL (cached),
    not regenerated per-frame.
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from moviepy import (
    VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip,
    CompositeAudioClip, concatenate_videoclips,
)
try:
    from moviepy.audio.fx import MultiplyVolume
except Exception:
    MultiplyVolume = None

from app.config import get_settings
from app.models.schemas import ScriptPlan, PLATFORM_SPECS
from app.services.caption_service import Cue

settings = get_settings()

FONT_PATH_BOLD = None  # resolved lazily; falls back to PIL default if not found
for candidate in [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]:
    if Path(candidate).exists():
        FONT_PATH_BOLD = candidate
        break


def _scene_clip(visual_path: Path, duration: float, width: int, height: int):
    """Builds a clip for one scene, cropped/scaled to fill the target frame."""
    suffix = visual_path.suffix.lower()
    if suffix in (".mp4", ".mov", ".webm"):
        clip = VideoFileClip(str(visual_path))
        if clip.duration < duration:
            loops = math.ceil(duration / clip.duration)
            clip = concatenate_videoclips([clip] * loops)
        clip = clip.subclipped(0, duration)
    else:
        clip = ImageClip(str(visual_path)).with_duration(duration)

    clip = _cover_resize(clip, width, height)
    return clip


def _cover_resize(clip, width: int, height: int):
    """Scale+crop clip to fully cover (width,height) like CSS background-size:cover."""
    cw, ch = clip.size
    scale = max(width / cw, height / ch)
    clip = clip.resized(scale)
    nw, nh = clip.size
    x1 = max(0, (nw - width) / 2)
    y1 = max(0, (nh - height) / 2)
    clip = clip.cropped(x1=x1, y1=y1, width=width, height=height)
    return clip


def _caption_image(text: str, width: int, font_size: int) -> Image.Image:
    """Renders one caption cue as a transparent PNG (PIL), used as an ImageClip overlay."""
    font = ImageFont.truetype(FONT_PATH_BOLD, font_size) if FONT_PATH_BOLD else ImageFont.load_default(font_size)
    padding = 24

    dummy = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(dummy)
    bbox = d.textbbox((0, 0), text, font=font, stroke_width=6)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    img = Image.new("RGBA", (text_w + padding * 2, text_h + padding * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # black outline for legibility over any footage, white fill on top
    d.text((padding - bbox[0], padding - bbox[1]), text, font=font,
            fill=(255, 255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0, 255))
    return img


def _build_caption_clips(cues: List[Cue], width: int, height: int, font_size: int):
    clips = []
    for cue in cues:
        if not cue["text"].strip():
            continue
        img = _caption_image(cue["text"].upper(), width, font_size)
        arr = np.array(img)
        clip = (ImageClip(arr)
                .with_start(cue["start"])
                .with_duration(max(cue["end"] - cue["start"], 0.4))
                .with_position(("center", height * 0.78)))
        clips.append(clip)
    return clips


def render_video(
    plan: ScriptPlan,
    scene_visual_paths: List[Path],
    voiceover_path: Optional[Path],
    music_path: Optional[Path],
    caption_cues: List[Cue],
    platform: str,
    out_path: Path,
) -> Path:
    spec = PLATFORM_SPECS[platform]
    width, height = spec["w"], spec["h"]
    font_size = max(36, width // 18)

    scene_clips = []
    for scene, visual_path in zip(plan.scenes, scene_visual_paths):
        clip = _scene_clip(visual_path, scene.duration_seconds, width, height)
        scene_clips.append(clip)

    video = concatenate_videoclips(scene_clips, method="compose")
    total_duration = video.duration

    audio_tracks = []
    if voiceover_path and voiceover_path.exists():
        vo = AudioFileClip(str(voiceover_path))
        audio_tracks.append(vo)
        total_duration = max(total_duration, vo.duration)

    if music_path and music_path.exists():
        music = AudioFileClip(str(music_path))
        if music.duration < total_duration:
            from moviepy.audio.AudioClip import concatenate_audioclips
            loops = math.ceil(total_duration / music.duration)
            music = concatenate_audioclips([music] * loops)
        music = music.subclipped(0, total_duration)
        if MultiplyVolume:
            music = music.with_effects([MultiplyVolume(0.18)])
        audio_tracks.append(music)

    if video.duration < total_duration:
        # Hold the last frame for the extra time so video length matches audio length.
        last_frame_clip = ImageClip(video.get_frame(max(video.duration - 0.04, 0))).with_duration(
            total_duration - video.duration
        )
        video = concatenate_videoclips([video, last_frame_clip], method="compose")

    if audio_tracks:
        final_audio = CompositeAudioClip(audio_tracks)
        video = video.with_audio(final_audio)

    if caption_cues:
        caption_clips = _build_caption_clips(caption_cues, width, height, font_size)
        video = CompositeVideoClip([video, *caption_clips], size=(width, height))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    video.write_videofile(
        str(out_path),
        fps=settings.DEFAULT_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="veryfast",       # speed lever: veryfast trades a little quality for a lot of speed
        threads=settings.RENDER_THREADS,
        bitrate="4500k" if width <= 1280 else "6000k",
        logger=None,
    )

    for c in scene_clips:
        c.close()
    video.close()

    return out_path
