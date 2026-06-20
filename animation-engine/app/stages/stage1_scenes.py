import json
from utils.llm import call_llm
from utils.json_safe import extract_json
from pathlib import Path

def generate_scenes(topic: str, level: str, rag_context: str = None, language: str = "english"):
    BASE_DIR = Path(__file__).resolve().parent.parent
    prompt = (BASE_DIR / "prompts" / "scene_planner.txt").read_text(encoding="utf-8")
    if rag_context and rag_context.strip():
        safe_rag = str(rag_context).replace("{", "{{").replace("}", "}}")
        prompt += (
            f"\n\nNCERT Textbook Reference (RAG):\n"
            f"IMPORTANT: Base the scene sequence on the following actual textbook excerpts. "
            f"Use the terminology, definitions, and structure exactly as they appear in the textbook:\n"
            f"{safe_rag}"
        )
    if language and language.lower() != "english":
        prompt += (
            f"\n\nIMPORTANT: The target language for the video is {language}. "
            f"You MUST generate the scene JSON fields 'concept', 'action', 'labels_or_equations', and 'color_emphasis' "
            f"entirely in {language}. Keep the 'objects' array names (like 'Circle', 'MathTex') in English so they map to Manim classes."
        )
    prompt = prompt.format(topic=topic, level=level)
    OUTPUT_DIR = BASE_DIR / "outputs"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = call_llm(prompt)
    scenes = extract_json(output)

    Path("outputs/scenes.json").write_text(json.dumps(scenes, indent=2))
    return scenes
