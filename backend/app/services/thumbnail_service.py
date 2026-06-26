"""
Generates a thumbnail automatically: grabs a frame from partway through
the rendered video (usually more visually interesting than frame 0)
and overlays the video title in a bold, social-media-style treatment.
"""
from __future__ import annotations
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from moviepy import VideoFileClip

FONT_PATH_BLACK = None
for candidate in [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]:
    if Path(candidate).exists():
        FONT_PATH_BLACK = candidate
        break


def generate_thumbnail(video_path: Path, title: str, out_path: Path) -> Path:
    clip = VideoFileClip(str(video_path))
    t = min(max(clip.duration * 0.35, 0.2), clip.duration - 0.1) if clip.duration > 0.5 else 0
    frame = clip.get_frame(t)
    clip.close()

    img = Image.fromarray(frame).convert("RGB")
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Color(img).enhance(1.1)

    w, h = img.size
    # darken bottom third for text legibility
    gradient = Image.new("L", (1, h), 0)
    for y in range(h):
        t2 = max(0, (y - h * 0.45) / (h * 0.55))
        gradient.putpixel((0, y), int(180 * t2))
    gradient = gradient.resize((w, h))
    black = Image.new("RGB", (w, h), (0, 0, 0))
    img = Image.composite(black, img, gradient)

    draw = ImageDraw.Draw(img)
    font_size = max(40, w // 14)
    font = ImageFont.truetype(FONT_PATH_BLACK, font_size) if FONT_PATH_BLACK else ImageFont.load_default(font_size)

    margin = int(w * 0.06)
    max_width = w - margin * 2
    words = title.upper().split()
    lines, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    lines = lines[:3]

    line_height = font_size * 1.15
    total_h = line_height * len(lines)
    y = h - margin - total_h

    for line in lines:
        draw.text((margin, y), line, font=font, fill=(255, 255, 255),
                   stroke_width=6, stroke_fill=(0, 0, 0))
        y += line_height

    # accent bar, signature element matching the brand
    bar_h = max(6, h // 90)
    draw.rectangle([0, h - margin - total_h - bar_h - 14, margin + 90, h - margin - total_h - 14],
                   fill=(255, 90, 54))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=92)
    return out_path
