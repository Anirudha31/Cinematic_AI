"""
Generates timed captions from the voiceover audio using faster-whisper
(runs locally, fully free, no API key, no internet required after the
model weights are first downloaded).

Returns a list of caption "cues": {start, end, text} suitable for
burning into the video or exporting as an .srt file.
"""
from __future__ import annotations
from pathlib import Path
from typing import List, TypedDict
from functools import lru_cache

from app.config import get_settings

settings = get_settings()


class Cue(TypedDict):
    start: float
    end: float
    text: str


@lru_cache(maxsize=1)
def _get_model():
    from faster_whisper import WhisperModel
    return WhisperModel(settings.WHISPER_MODEL_SIZE, device=settings.WHISPER_DEVICE, compute_type="int8")


def generate_captions(audio_path: Path, max_words_per_cue: int = 5) -> List[Cue]:
    """
    Transcribes audio_path and groups words into short caption cues
    (a few words at a time) so captions read like punchy social-media
    subtitles rather than long subtitle blocks.
    """
    model = _get_model()
    segments, _info = model.transcribe(str(audio_path), word_timestamps=True)

    words = []
    for seg in segments:
        if seg.words:
            words.extend(seg.words)

    if not words:
        return []

    cues: List[Cue] = []
    bucket = []
    for w in words:
        bucket.append(w)
        if len(bucket) >= max_words_per_cue:
            cues.append({
                "start": bucket[0].start,
                "end": bucket[-1].end,
                "text": "".join(x.word for x in bucket).strip(),
            })
            bucket = []
    if bucket:
        cues.append({
            "start": bucket[0].start,
            "end": bucket[-1].end,
            "text": "".join(x.word for x in bucket).strip(),
        })
    return cues


def cues_to_srt(cues: List[Cue]) -> str:
    def fmt(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    lines = []
    for i, c in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{fmt(c['start'])} --> {fmt(c['end'])}")
        lines.append(c["text"])
        lines.append("")
    return "\n".join(lines)
