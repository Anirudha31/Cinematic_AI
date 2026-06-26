"""
Turns a user's free-text prompt into a structured ScriptPlan: a hook,
a sequence of scenes (each with narration + a visual search query +
duration), a call-to-action, caption and hashtags.

Two modes:
  1. ANTHROPIC_API_KEY set  -> ask Claude to write the plan as JSON.
  2. No key                 -> deterministic template planner. Still
     produces a coherent multi-scene script so the whole pipeline
     works end-to-end for free.
"""
from __future__ import annotations
import json
import re
from typing import List

from app.config import get_settings
from app.models.schemas import GenerateRequest, ScriptPlan, Scene, PLATFORM_SPECS

settings = get_settings()


SYSTEM_PROMPT = """You are a short-form and long-form video scriptwriter for social media \
(YouTube, Instagram Reels, TikTok, Facebook). Given a topic/prompt, you write a scene-by-scene \
video plan optimized for retention and clarity.

Respond ONLY with valid JSON matching this exact schema, no markdown fences, no preamble:
{
  "title": "string, short punchy video title",
  "hook": "string, the first 1-2 sentences spoken in the first 3 seconds to stop the scroll",
  "scenes": [
    {
      "index": 0,
      "narration": "string, what the voiceover says during this scene",
      "on_screen_text": "string or null, short caption/text overlay for this scene",
      "visual_query": "string, a short visual search phrase describing what footage/image should show",
      "duration_seconds": 4.0
    }
  ],
  "cta": "string, short call to action for the end of the video",
  "suggested_caption": "string, ready-to-post social caption for this video",
  "suggested_hashtags": ["#tag1", "#tag2"],
  "music_mood": "one of: upbeat, calm, cinematic, dramatic, funny, corporate, lofi"
}

Rules:
- Match total duration roughly to the target duration given.
- Scenes should be 3-6 seconds each for short-form, can be longer for long-form.
- Keep narration natural and spoken, not written.
- visual_query should be concrete and searchable (e.g. "person jogging sunrise city park"), not abstract.
"""


def _platform_context(req: GenerateRequest) -> dict:
    spec = PLATFORM_SPECS[req.platform]
    target = req.duration_seconds or min(spec["max_seconds"], 45 if "short" in req.platform or req.platform in ("instagram_reel", "tiktok") else 90)
    return {"spec": spec, "target_seconds": target}


def plan_script(req: GenerateRequest) -> ScriptPlan:
    if settings.ANTHROPIC_API_KEY:
        try:
            return _plan_with_claude(req)
        except Exception as e:
            # Never hard-fail the whole pipeline because the optional AI call failed.
            print(f"[planner] Claude planning failed, falling back to template: {e}")
    return _plan_with_template(req)


def _plan_with_claude(req: GenerateRequest) -> ScriptPlan:
    import anthropic

    ctx = _platform_context(req)
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_msg = (
        f"Topic/prompt: {req.prompt}\n"
        f"Platform: {PLATFORM_SPECS[req.platform]['label']}\n"
        f"Target total duration: {ctx['target_seconds']} seconds\n"
        f"Tone: {req.tone}\n"
        f"Music mood preference: {req.music_mood or 'auto - pick the best fit'}\n"
    )

    resp = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    data = json.loads(text)

    scenes = [Scene(**s) for s in data["scenes"]]
    return ScriptPlan(
        title=data["title"],
        hook=data["hook"],
        scenes=scenes,
        cta=data.get("cta"),
        suggested_caption=data.get("suggested_caption"),
        suggested_hashtags=data.get("suggested_hashtags", []),
        music_mood=data.get("music_mood", "upbeat"),
    )


# ---------------------------------------------------------------------------
# Free fallback: deterministic template planner (no API key required)
# ---------------------------------------------------------------------------

_HOOK_TEMPLATES = [
    "Wait — you need to see this about {topic}.",
    "Here's what nobody tells you about {topic}.",
    "This changed how I think about {topic} completely.",
    "{topic}? Let me break it down in under a minute.",
]

_BEAT_TEMPLATES = [
    "Let's start with the basics of {topic}.",
    "Here's the part most people get wrong about {topic}.",
    "Now here's the interesting twist with {topic}.",
    "This next bit about {topic} matters more than you'd think.",
    "Putting it all together, here's what {topic} really means for you.",
]

_CTA_TEMPLATES = [
    "Follow for more on {topic} — you won't want to miss what's next.",
    "Drop a comment if you want a deeper dive into {topic}.",
    "Save this and share it with someone who needs to see {topic}.",
]

_MOOD_KEYWORDS = {
    "funny": "funny", "comedy": "funny", "joke": "funny",
    "calm": "calm", "relax": "calm", "meditation": "calm", "sleep": "calm",
    "business": "corporate", "finance": "corporate", "startup": "corporate", "marketing": "corporate",
    "story": "cinematic", "travel": "cinematic", "adventure": "cinematic",
    "dramatic": "dramatic", "horror": "dramatic", "thriller": "dramatic",
    "study": "lofi", "focus": "lofi", "chill": "lofi",
}


def _guess_mood(prompt: str, tone: str) -> str:
    p = prompt.lower()
    for kw, mood in _MOOD_KEYWORDS.items():
        if kw in p:
            return mood
    return {"energetic": "upbeat", "calm": "calm", "professional": "corporate",
            "funny": "funny", "dramatic": "dramatic"}.get(tone, "upbeat")


def _topic_phrase(prompt: str) -> str:
    p = prompt.strip().rstrip(".")
    # Use prompt directly if short, otherwise trim to a punchy phrase
    if len(p) <= 60:
        return p
    return p[:57] + "..."


def _plan_with_template(req: GenerateRequest) -> ScriptPlan:
    ctx = _platform_context(req)
    target = ctx["target_seconds"]
    topic = _topic_phrase(req.prompt)
    mood = req.music_mood or _guess_mood(req.prompt, req.tone or "energetic")

    scene_len = 5.0 if target <= 60 else 7.0
    n_scenes = max(3, min(12, round((target - 4) / scene_len)))  # leave room for hook+cta beat
    scenes: List[Scene] = []

    hook = _HOOK_TEMPLATES[hash(req.prompt) % len(_HOOK_TEMPLATES)].format(topic=topic)
    scenes.append(Scene(
        index=0,
        narration=hook,
        on_screen_text=topic.upper() if len(topic) < 40 else None,
        visual_query=f"{topic} close up dynamic",
        duration_seconds=3.5,
    ))

    for i in range(n_scenes):
        beat = _BEAT_TEMPLATES[i % len(_BEAT_TEMPLATES)].format(topic=topic)
        scenes.append(Scene(
            index=i + 1,
            narration=beat,
            on_screen_text=None,
            visual_query=f"{topic} {['detail shot','wide shot','action shot','people','b-roll'][i % 5]}",
            duration_seconds=scene_len,
        ))

    cta = _CTA_TEMPLATES[hash(topic) % len(_CTA_TEMPLATES)].format(topic=topic)
    scenes.append(Scene(
        index=len(scenes),
        narration=cta,
        on_screen_text="FOLLOW FOR MORE",
        visual_query=f"{topic} outro bright",
        duration_seconds=4.0,
    ))

    hashtags = ["#" + re.sub(r"[^a-zA-Z0-9]", "", w) for w in topic.split()[:4] if len(w) > 2]
    hashtags += ["#reels", "#fyp", "#viral"]

    return ScriptPlan(
        title=topic if len(topic) < 60 else topic[:57] + "...",
        hook=hook,
        scenes=scenes,
        cta=cta,
        suggested_caption=f"{topic} 🎬 {cta}",
        suggested_hashtags=list(dict.fromkeys(hashtags))[:8],
        music_mood=mood,
    )
