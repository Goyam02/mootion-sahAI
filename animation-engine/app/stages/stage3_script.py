import json
from utils.llm import call_llm
from utils.json_safe import extract_json
from pathlib import Path
from paths import PROMPTS_DIR

def generate_script(scenes, timestamps, persona, level, rag_context=None, language: str = "english"):
    prompt = (PROMPTS_DIR / "script_writer.txt").read_text(encoding="utf-8")
    if rag_context and rag_context.strip():
        safe_rag = str(rag_context).replace("{", "{{").replace("}", "}}")
        prompt += (
            f"\n\nNCERT Textbook Reference (RAG):\n"
            f"IMPORTANT: Use the following textbook excerpts for narration accuracy. "
            f"Quotes, definitions and terminology must match the textbook exactly:\n"
            f"{safe_rag}"
        )
    prompt = prompt.format(
        scenes=json.dumps(scenes),
        timestamps=json.dumps(timestamps),
        persona=persona,
        level=level,
        language=language
    )

    output = call_llm(prompt)
    script = extract_json(output)

    Path("outputs/script.json").write_text(json.dumps(script, indent=2))
    return script
