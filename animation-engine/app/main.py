import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware  
from stages.stage1_scenes import generate_scenes
from stages.stage2_manim import generate_manim
from stages.stage3_script import generate_script
from stages.stage4_tts import tts_generate
from stages.stage5_stitch import (
    stitch,
    mux_audio,
    extract_audio_from_final,
    send_to_sadtalker,
)

from utils.generate_uid import generate_video_id
from pathlib import Path

app = FastAPI()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/explain")
def explain(
    topic: str,
    level: str = "school",
    persona: str = "teacher",
    face_enabled: bool = False,
    rag_context: str | None = None,
    language: str = "english",
):
    from utils.cost_tracker import init_tracker, finalize_and_log

    video_id = generate_video_id()
    tracker = init_tracker(topic=topic, video_id=video_id)

    try:
        # -------- Stage 1: Scene planning --------
        tracker.start_stage("scene_planning")
        scenes = generate_scenes(topic, level, rag_context, language)
        tracker.end_stage("scene_planning")

        # -------- Stage 2: Manim rendering --------
        tracker.start_stage("manim_rendering")
        manim_data = generate_manim(scenes, rag_context, language)
        scene_ids = manim_data["scene_ids"]   # list of (disk_index, scene_id) tuples
        tracker.end_stage("manim_rendering")

        # -------- Stage 3: Script generation --------
        tracker.start_stage("script_generation")
        script = generate_script(
            scenes,
            manim_data["timestamps"],
            persona,
            level,
            rag_context,
            language,
        )
        tracker.end_stage("script_generation")

        # -------- Stage 4: TTS (ONLY surviving scenes) --------
        tracker.start_stage("tts_generation")
        tts_generate(
            script=script,
            video_id=video_id,
            scene_ids=scene_ids,
            language=language,
        )
        tracker.end_stage("tts_generation")

        # -------- Stage 5: Audio + Video --------
        tracker.start_stage("stitch_and_mux")
        mux_audio(video_id, scene_ids)
        final_video_path = stitch(video_id)
        tracker.end_stage("stitch_and_mux")

        sadtalker_job_id = None
        # -------- Optional: SadTalker --------
        if face_enabled:
            tracker.start_stage("sadtalker")
            final_audio_path = extract_audio_from_final(video_id)
            sadtalker_job_id = send_to_sadtalker(final_audio_path)
            tracker.end_stage("sadtalker")

    finally:
        cost_summary = finalize_and_log()

    response = {
        "status": "complete",
        "video_id": video_id,
        "video_path": str(final_video_path),
        "face_enabled": face_enabled,
        "estimated_cost": cost_summary,
    }

    if face_enabled and sadtalker_job_id:
        response.update({
            "sadtalker_job_id": sadtalker_job_id,
            "avatar_status": "processing",
        })

    return response


@app.get("/video/{video_id}")
def get_video(video_id: str):
    path = PROJECT_ROOT / "outputs" / "videos" / video_id / "final.mp4"

    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(path, media_type="video/mp4")
