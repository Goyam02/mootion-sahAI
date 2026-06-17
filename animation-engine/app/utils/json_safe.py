from __future__ import annotations

import json


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        if stripped.endswith("```"):
            stripped = stripped[:-3]
    return stripped.strip()


def extract_json(text: str):
    """Extract the first JSON object or array from a string."""
    cleaned = _strip_code_fences(text)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(cleaned):
        if ch not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[idx:])
            return value
        except json.JSONDecodeError:
            continue

    raise ValueError("No JSON object or array found in LLM output")
