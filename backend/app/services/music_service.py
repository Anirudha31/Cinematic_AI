"""
Auto-selects a royalty-free background music track based on the
script's detected mood.

This reads from backend/assets/music/<mood>/*.mp3. We ship this
folder empty (audio files aren't something we can bundle here), but
the README explains exactly where to drop free tracks from sources
like YouTube Audio Library, Pixabay Music, or Free Music Archive --
all of which offer royalty-free downloads with no API key needed.

If no track is found for a mood (e.g. folder is empty), we fall back
to silence (the voiceover still plays fine without music) so the
pipeline never breaks.
"""
from __future__ import annotations
import random
from pathlib import Path
from typing import Optional

MUSIC_ROOT = Path(__file__).resolve().parent.parent.parent / "assets" / "music"

MOODS = ["upbeat", "calm", "cinematic", "dramatic", "funny", "corporate", "lofi"]


def pick_track(mood: str) -> Optional[Path]:
    mood = mood if mood in MOODS else "upbeat"
    folder = MUSIC_ROOT / mood
    if not folder.exists():
        return None
    candidates = [p for p in folder.glob("*.mp3")] + [p for p in folder.glob("*.wav")]
    if not candidates:
        return None
    return random.choice(candidates)
