import json
from utils.llm import call_llm
from utils.json_safe import extract_json
from pathlib import Path

def generate_scenes(topic: str, level: str):
    BASE_DIR = Path(__file__).resolve().parent.parent
    prompt = (BASE_DIR / "prompts" / "scene_planner.txt").read_text(encoding="utf-8")
    prompt = prompt.format(topic=topic, level=level)
    OUTPUT_DIR = BASE_DIR / "outputs"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = call_llm(prompt)
    scenes = extract_json(output)

    Path("outputs/scenes.json").write_text(json.dumps(scenes, indent=2))
    return scenes
