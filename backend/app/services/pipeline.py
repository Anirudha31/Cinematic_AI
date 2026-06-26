"""
Orchestrates the full pipeline for one job, end to end:

  prompt -> script plan -> source visuals -> voiceover -> captions
  -> background music -> render -> thumbnail -> done

Runs in a background thread per job so the HTTP request that kicked
it off returns instantly; the frontend polls /jobs/{id} for progress.
"""
from __future__ import annotations
from pathlib import Path
import traceback

from app.config import get_settings
from app.models.schemas import JobStatus, PLATFORM_SPECS
from app.services import job_store
from app.services.script_planner import plan_script
from app.services.visual_source import source_visual_for_scene
from app.services.tts_service import generate_voiceover, pick_voice
from app.services.caption_service import generate_captions
from app.services.music_service import pick_track
from app.services.video_renderer import render_video
from app.services.thumbnail_service import generate_thumbnail

settings = get_settings()
STORAGE = Path(settings.STORAGE_DIR)


def run_pipeline(job_id: str) -> None:
    job = job_store.get_job(job_id)
    if not job:
        return

    work_dir = STORAGE / "temp" / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        req = job.request

        # 1. Plan the script
        job_store.update_job(job_id, status=JobStatus.PLANNING, progress=8, message="Writing your script and scene plan...")
        plan = plan_script(req)
        job_store.update_job(job_id, plan=plan, progress=18)

        spec = PLATFORM_SPECS[req.platform]
        width, height = spec["w"], spec["h"]

        # 2. Source visuals per scene
        job_store.update_job(job_id, status=JobStatus.SOURCING, progress=22, message="Finding footage for each scene...")
        visual_paths = []
        n = len(plan.scenes)
        for i, scene in enumerate(plan.scenes):
            path = source_visual_for_scene(scene, work_dir / "visuals", width, height)
            visual_paths.append(path)
            job_store.update_job(job_id, progress=22 + int(18 * (i + 1) / max(n, 1)))

        # 3. Voiceover
        voiceover_path = None
        if req.add_voiceover:
            job_store.update_job(job_id, status=JobStatus.VOICING, progress=42, message="Recording the voiceover...")
            full_narration = " ".join(s.narration for s in plan.scenes)
            voice = pick_voice(req.tone or "energetic", req.voice)
            voiceover_path = generate_voiceover(full_narration, work_dir / "voiceover.mp3", voice)

        # 4. Captions (depends on voiceover audio)
        caption_cues = []
        if req.add_captions and voiceover_path:
            job_store.update_job(job_id, status=JobStatus.CAPTIONING, progress=55, message="Auto-generating captions...")
            try:
                caption_cues = generate_captions(voiceover_path)
            except Exception as e:
                print(f"[pipeline] captioning failed, continuing without captions: {e}")
                caption_cues = []

        # 5. Background music
        music_path = None
        if req.add_music:
            job_store.update_job(job_id, status=JobStatus.SCORING, progress=62, message="Selecting background music...")
            music_path = pick_track(req.music_mood or plan.music_mood)

        # 6. Render
        job_store.update_job(job_id, status=JobStatus.RENDERING, progress=68, message="Rendering your video...")
        out_path = STORAGE / "renders" / f"{job_id}.mp4"
        render_video(
            plan=plan,
            scene_visual_paths=visual_paths,
            voiceover_path=voiceover_path,
            music_path=music_path,
            caption_cues=caption_cues,
            platform=req.platform,
            out_path=out_path,
        )
        job_store.update_job(job_id, progress=90, video_path=str(out_path))

        # 7. Thumbnail
        thumb_path = None
        if req.add_thumbnail:
            job_store.update_job(job_id, status=JobStatus.THUMBNAIL, progress=94, message="Generating thumbnail...")
            thumb_path = STORAGE / "renders" / f"{job_id}_thumb.jpg"
            generate_thumbnail(out_path, plan.title, thumb_path)

        job_store.update_job(
            job_id,
            status=JobStatus.DONE,
            progress=100,
            message="Done! Your video is ready.",
            video_path=str(out_path),
            thumbnail_path=str(thumb_path) if thumb_path else None,
        )

    except Exception as e:
        traceback.print_exc()
        job_store.update_job(
            job_id,
            status=JobStatus.FAILED,
            message="Something went wrong while generating your video.",
            error=str(e),
        )
