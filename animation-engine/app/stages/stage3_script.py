import json
from utils.llm import call_llm
from utils.json_safe import extract_json
from pathlib import Path
from paths import PROMPTS_DIR

def generate_script(scenes, timestamps, persona, level):
    prompt = (PROMPTS_DIR / "script_writer.txt").read_text(encoding="utf-8")
    prompt = prompt.format(
        scenes=json.dumps(scenes),
        timestamps=json.dumps(timestamps),
        persona=persona,
        level=level
    )

    output = call_llm(prompt)
    script = extract_json(output)

    Path("outputs/script.json").write_text(json.dumps(script, indent=2))
    return script
