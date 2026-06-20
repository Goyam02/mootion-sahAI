import json
import subprocess
from pathlib import Path
import re
import shutil

from utils.llm import call_llm
from utils.json_safe import extract_json
from utils.timestamps_extractor import extract_timestamps

# ============================================================
# PATHS (ABSOLUTE, SINGLE SOURCE OF TRUTH)
# ============================================================

# This file: app/stages/stage2_manim.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]

APP_DIR = PROJECT_ROOT / "app"
PROMPTS_DIR = APP_DIR / "prompts"

MEDIA_DIR = PROJECT_ROOT / "media"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

ANIMATION_PY = OUTPUTS_DIR / "animation.py"
TIMESTAMPS_JSON = OUTPUTS_DIR / "timestamps.json"
SCENES_OUT_DIR = OUTPUTS_DIR / "scenes"

# ============================================================
# REGEX
# ============================================================

SCENE_CLASS_RE = re.compile(
    r"class\s+(Scene\d+(?:_[A-Za-z0-9_]+)?)\s*\((?:Scene|ThreeDScene|MovingCameraScene)\)"
)

# ============================================================
# HELPERS
# ============================================================

def extract_scene_classes(manim_code: str):
    return SCENE_CLASS_RE.findall(manim_code)


def clean_manim_temp():
    """Remove ALL manim temporary artifacts."""
    for p in [
        MEDIA_DIR / "videos",
        MEDIA_DIR / "Tex",
        MEDIA_DIR / "text",
        MEDIA_DIR / "images",
    ]:
        shutil.rmtree(p, ignore_errors=True)


def render_scene(scene_class_name: str):
    """Render exactly ONE scene."""
    subprocess.run(
        [
            "manim",
            "-ql",
            str(ANIMATION_PY),
            scene_class_name,
        ],
        cwd=PROJECT_ROOT,  # 🔥 CRITICAL: prevents app/media
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def generate_placeholder_video(scene_id: str, index: int, duration: int = 6):
    """Generate a plain black video as a fallback for scenes that failed to render."""
    SCENES_OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = SCENES_OUT_DIR / f"{index:02d}_{scene_id}.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s=854x480:r=15:d={duration}",
            "-c:v", "libx264",
            "-t", str(duration),
            str(dst),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print(f"⬛ Placeholder video generated → {dst}")
    return dst


def extract_scene_video(scene_class_name: str, scene_id: str, index: int):
    """Move rendered scene video from media/ → outputs/scenes/"""
    candidates = list(MEDIA_DIR.rglob(f"{scene_class_name}.mp4"))

    if not candidates:
        raise RuntimeError(f"No video found for {scene_class_name}")

    SCENES_OUT_DIR.mkdir(parents=True, exist_ok=True)

    dst = SCENES_OUT_DIR / f"{index:02d}_{scene_id}.mp4"
    shutil.move(candidates[0], dst)

    print(f"🎬 Saved → {dst}")
    return dst


def fix_manim_code_with_llm(manim_code: str, error: str) -> str:
    prompt = f"""
You are an expert Manim debugger.

Rules:
- Fix ONLY runtime or syntax errors
- Do NOT rename Scene classes
- Do NOT add or remove scenes
- Return ONLY valid Python code
- Do NOT include markdown
- Do NOT include explanations

Broken Manim code:
{manim_code}

Error:
{error}
"""
    output = call_llm(prompt)
    return output.strip()


MAX_RETRIES = 2

def generate_manim(scenes, rag_context: str | None = None, language: str = "english"):
    # ---------- Generate Manim code ----------
    scenes_json = json.dumps(scenes)
    scenes_category = scenes["category"]
    prompt_path = PROMPTS_DIR / f"{scenes_category.lower()}_manim.txt"
    prompt = prompt_path.read_text(encoding="utf-8").replace(
        "{scenes_json}", scenes_json
    )
    if rag_context and rag_context.strip():
        safe_rag = str(rag_context).replace("{", "{{").replace("}", "}}")
        prompt += (
            f"\n\nTextbook Reference Context (RAG):\n"
            f"Use the following NCERT textbook excerpts to ensure the animation "
            f"accurately reflects the curriculum (correct terminology, structure, "
            f"and key concepts):\n{safe_rag}"
        )
    if language and language.lower() != "english":
        prompt += (
            f"\n\nIMPORTANT: Since the target language is {language}, the labels and text will contain non-English characters. "
            f"You MUST use standard Manim `Text('...')` (or `MarkupText('...')`) for all non-English text labels and annotations. "
            f"Do NOT use `Tex('...')` or `MathTex('...')` for non-English unicode text characters as they will fail to compile in LaTeX. "
            f"Only use `MathTex` for pure mathematical formulas (like 'F = m a') using standard math variables."
        )

    manim_code = ""
    scene_classes = []
    
    # Retry up to 3 times to get the correct number of scene classes
    for attempt in range(3):
        try:
            output = call_llm(prompt)
            data = extract_json(output)
            manim_code = data["manim_code"]
            
            # Harden against self.wait(<=0)
            def fix_wait_durations(match):
                try:
                    val = float(match.group(1))
                    if val <= 0:
                        return "self.wait(1.0)"
                except Exception:
                    pass
                return match.group(0)
                
            manim_code = re.sub(
                r"self\.wait\(\s*(-?\d+(?:\.\d+)?)\s*\)",
                fix_wait_durations,
                manim_code
            )
            
            scene_classes = extract_scene_classes(manim_code)
            
            if len(scene_classes) == len(scenes["scenes"]):
                break
            else:
                print(f"⚠️ Scene count mismatch on attempt {attempt+1}: expected {len(scenes['scenes'])}, got {len(scene_classes)}")
        except Exception as e:
            print(f"⚠️ Error during Manim generation attempt {attempt+1}: {e}")

    if len(scene_classes) != len(scenes["scenes"]):
        raise RuntimeError(
            f"Scene count mismatch between JSON ({len(scenes['scenes'])}) and Manim code ({len(scene_classes)}) after 3 attempts."
        )

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    ANIMATION_PY.write_text(manim_code)

    # ---------- Timestamps ----------
    timestamps = extract_timestamps(manim_code)
    TIMESTAMPS_JSON.write_text(json.dumps(timestamps, indent=2))

    final_scene_ids = []   # list of (disk_index, scene_id)

    # ---------- Per-scene rendering ----------
    for idx, scene_class in enumerate(scene_classes, start=1):
        scene_id = f"scene_{idx}"
        retries = 0

        while retries <= MAX_RETRIES:
            try:
                clean_manim_temp()
                render_scene(scene_class)
                extract_scene_video(scene_class, scene_id, idx)
                final_scene_ids.append((idx, scene_id))
                print(f"✅ Rendered {scene_class}")
                break

            except (subprocess.CalledProcessError, RuntimeError) as e:

                retries += 1
                stderr_text = e.stderr if hasattr(e, "stderr") and e.stderr else str(e)

                print("\n" + "=" * 80)
                print(f"❌ Manim error in {scene_class} (attempt {retries}/{MAX_RETRIES})")
                print("-" * 80)
                print(stderr_text)
                print("=" * 80)

                if retries <= MAX_RETRIES:
                    fixed_code = fix_manim_code_with_llm(manim_code, stderr_text)

                    print("\n🛠 LLM FIX APPLIED (preview):")
                    print("-" * 80)
                    print("\n".join(fixed_code.splitlines()[:30]))
                    print("-" * 80)

                    manim_code = fixed_code
                    ANIMATION_PY.write_text(manim_code)
                else:
                    # All retries exhausted — generate a black placeholder so
                    # downstream stages (TTS, mux, stitch) don't crash.
                    print(f"⬛ Scene {scene_class} failed all retries — inserting placeholder.")
                    try:
                        generate_placeholder_video(scene_id, idx)
                        final_scene_ids.append((idx, scene_id))
                    except Exception as placeholder_err:
                        print(f"⚠️  Could not generate placeholder for {scene_id}: {placeholder_err}")
                    break


    return {
        "manim_code": manim_code,
        "timestamps": timestamps,
        "scene_ids": final_scene_ids,   # list of (disk_index, scene_id)
    }


def clean_manim_output():
    video_dir = Path("media/videos/animation/480p15")
    video_dir.mkdir(parents=True, exist_ok=True)

    for f in video_dir.glob("*.mp4"):
        f.unlink()

