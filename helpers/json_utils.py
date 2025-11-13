"""
JSON extraction and fallback utilities for video scripting.

We try to pull a JSON object out of a model's response, and if
that fails, we return None so the caller can use a fallback block.
"""

import json
from typing import Any, Dict, Optional


def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    """
    Try to parse a JSON object from the given text.

    Strategy:
    1. Try json.loads on the whole string.
    2. If that fails, look for the first '{' and last '}' and parse that slice.
    3. If still failing, return None.
    """
    text = text.strip()
    if not text:
        return None

    # 1) raw attempt
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 2) substring between first '{' and last '}'
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start : end + 1]
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None

    return None


def fallback_block(beat_title: str) -> Dict[str, Any]:
    """
    Provide a safe default block when JSON parsing fails.

    The strings here are intentionally generic; the model's real
    responses should normally override these when JSON is valid.
    """
    return {
        "voiceover": f"Introduce the idea for the '{beat_title}' part in a clear, simple line.",
        "on_screen": f"{beat_title} on screen.",
        "shots": [
            f"Shot of the main subject related to {beat_title.lower()}.",
            "Close-up shot for extra detail.",
            "Wide shot to show context or environment.",
        ],
        "broll": [
            "Supporting b-roll that reinforces the message.",
            "Cutaway showing product or user in action.",
        ],
        "captions": [
            f"{beat_title} caption text.",
        ],
    }
