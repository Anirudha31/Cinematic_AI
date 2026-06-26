"""
Generates voiceover audio from narration text.

Uses edge-tts by default (Microsoft's free neural voices, no API key,
no usage limits) with gTTS as a fallback if edge-tts is unreachable
(e.g. blocked network). Both are completely free.
"""
from __future__ import annotations
import asyncio
from pathlib import Path

from app.config import get_settings

settings = get_settings()

# A curated set of natural-sounding free voices, grouped by tone.
VOICE_PRESETS = {
    "energetic": "en-US-AriaNeural",
    "calm": "en-US-JennyNeural",
    "professional": "en-US-GuyNeural",
    "funny": "en-US-AnaNeural",
    "dramatic": "en-GB-RyanNeural",
}


def pick_voice(tone: str, override: str | None) -> str:
    if override:
        return override
    return VOICE_PRESETS.get(tone, settings.DEFAULT_VOICE)


async def _edge_tts_generate(text: str, voice: str, out_path: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def _gtts_generate(text: str, out_path: Path) -> None:
    from gtts import gTTS
    tts = gTTS(text=text, lang="en")
    tts.save(str(out_path))


def generate_voiceover(text: str, out_path: Path, voice: str) -> Path:
    """Synchronous wrapper - generates an mp3 voiceover for the given text."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        asyncio.run(_edge_tts_generate(text, voice, out_path))
        if out_path.exists() and out_path.stat().st_size > 0:
            return out_path
        raise RuntimeError("edge-tts produced empty file")
    except Exception as e:
        print(f"[tts] edge-tts failed ({e}), falling back to gTTS")
        _gtts_generate(text, out_path)
        return out_path
