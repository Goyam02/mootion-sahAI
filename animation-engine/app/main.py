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
    video_id = generate_video_id()

    # -------- Stage 1: Scene planning --------
    scenes = generate_scenes(topic, level, rag_context, language)

    # -------- Stage 2: Manim rendering --------
    manim_data = generate_manim(scenes, rag_context, language)
    scene_ids = manim_data["scene_ids"]   # list of (disk_index, scene_id) tuples

    # -------- Stage 3: Script generation --------
    script = generate_script(
        scenes,
        manim_data["timestamps"],
        persona,
        level,
        rag_context,
        language,
    )

    # -------- Stage 4: TTS (ONLY surviving scenes) --------
    tts_generate(
        script=script,
        video_id=video_id,
        scene_ids=scene_ids,
        language=language,
    )

    # -------- Stage 5: Audio + Video --------
    mux_audio(video_id, scene_ids)
    final_video_path = stitch(video_id)

    response = {
        "status": "complete",
        "video_id": video_id,
        "video_path": str(final_video_path),
        "face_enabled": face_enabled,
    }

    # -------- Optional: SadTalker --------
    if face_enabled:
        final_audio_path = extract_audio_from_final(video_id)
        job_id = send_to_sadtalker(final_audio_path)

        response.update({
            "sadtalker_job_id": job_id,
            "avatar_status": "processing",
        })

    return response


@app.get("/video/{video_id}")
def get_video(video_id: str):
    path = PROJECT_ROOT / "outputs" / "videos" / video_id / "final.mp4"

    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(path, media_type="video/mp4")
