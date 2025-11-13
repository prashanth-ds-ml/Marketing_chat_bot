"""
Video planning and scripting pipeline for Marketeer.

High level:
- plan_video() turns a blueprint + duration into timed beats.
- script_video_from_plan() calls the LLM beat-by-beat with JSON instructions.
- generate_video_script() is the main public entry point.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple

from .llm_client import generate_text
from helpers.blueprints import Blueprint, BeatTemplate, get_blueprint
from helpers.json_utils import extract_json_block, fallback_block
from helpers.platform_rules import PlatformConfig, PLATFORM_RULES, DEFAULT_PLATFORM_NAME


@dataclass
class VideoBeat:
    index: int
    title: str
    goal: str
    t_start: float
    t_end: float


@dataclass
class VideoPlan:
    blueprint_name: str
    duration_sec: int
    platform_name: str
    style: str
    beats: List[VideoBeat]


@dataclass
class VideoRequest:
    brand: str
    product: str
    audience: str
    goal: str
    blueprint_name: str
    duration_sec: int
    platform_name: str
    style: str
    extra_context: str = ""


@dataclass
class VideoScriptResponse:
    plan: VideoPlan
    beats: List[Dict[str, Any]]  # list of blocks with voiceover, on_screen, shots, broll, captions
    warnings: List[str]


# ----- Helpers -----


def _get_platform_config(name: str) -> PlatformConfig:
    if name in PLATFORM_RULES:
        return PLATFORM_RULES[name]
    return PLATFORM_RULES[DEFAULT_PLATFORM_NAME]


def plan_video(req: VideoRequest) -> VideoPlan:
    """
    Create a timed video plan (beat schedule) from the request.
    """
    bp: Blueprint = get_blueprint(req.blueprint_name)
    total_duration = max(req.duration_sec, 5)  # sane minimum

    total_weight = sum(beat.weight for beat in bp.beats) or 1.0

    beats: List[VideoBeat] = []
    t_cursor = 0.0

    for idx, beat_tpl in enumerate(bp.beats):
        fraction = beat_tpl.weight / total_weight
        # last beat absorbs any rounding leftovers
        if idx == len(bp.beats) - 1:
            t_end = float(total_duration)
        else:
            t_end = t_cursor + fraction * total_duration

        beat = VideoBeat(
            index=idx,
            title=beat_tpl.title,
            goal=beat_tpl.goal,
            t_start=round(t_cursor, 2),
            t_end=round(t_end, 2),
        )
        beats.append(beat)
        t_cursor = t_end

    return VideoPlan(
        blueprint_name=bp.name,
        duration_sec=total_duration,
        platform_name=req.platform_name,
        style=req.style,
        beats=beats,
    )


def _build_beat_prompt(req: VideoRequest, plan: VideoPlan, beat: VideoBeat) -> str:
    """
    Build a JSON-focused prompt for one beat.

    Constraints (you can tweak later):
    - Voiceover <= 18 words
    - On-screen text <= 36 characters
    - 3 shots
    - 2 b-roll ideas
    - 1–2 caption lines
    """
    lines = [
        "You are a creative short-form video scriptwriter.",
        f"Platform: {plan.platform_name}",
        f"Style: {plan.style}",
        "",
        f"Brand: {req.brand}",
        f"Product: {req.product}",
        f"Target audience: {req.audience}",
        f"Campaign goal: {req.goal}",
    ]
    if req.extra_context.strip():
        lines.append(f"Extra context: {req.extra_context.strip()}")

    lines += [
        "",
        f"This video follows a multi-beat structure. You are writing ONLY the beat:",
        f"- Beat title: {beat.title}",
        f"- Beat goal: {beat.goal}",
        f"- Time window: {beat.t_start:.1f}s to {beat.t_end:.1f}s in the video.",
        "",
        "Return a single JSON object with EXACTLY these keys:",
        '  "voiceover"  (string, <= 18 words)',
        '  "on_screen"  (string, <= 36 characters, like a short overlay text)',
        '  "shots"      (array of 3 short shot descriptions)',
        '  "broll"      (array of 2 short b-roll ideas)',
        '  "captions"   (array of 1–2 short caption strings)',
        "",
        "Do not add any extra keys. Do not add explanations or markdown.",
        "Just output the JSON object.",
    ]

    return "\n".join(lines)


def script_video_from_plan(
    req: VideoRequest,
    plan: VideoPlan,
    debug_first: bool = False,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Call the LLM beat-by-beat to create the video script.

    Returns:
        beats_blocks: list of blocks (one per beat)
        warnings: list of string messages about any fallbacks used
    """
    beats_blocks: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for i, beat in enumerate(plan.beats):
        prompt = _build_beat_prompt(req, plan, beat)

        raw = generate_text(
            prompt=prompt,
            max_new_tokens=256,
            temperature=0.7,
            top_p=0.9,
        )

        if debug_first and i == 0:
            print("=== RAW FIRST BEAT RESPONSE ===")
            print(raw)
            print("================================")

        data = extract_json_block(raw)
        if data is None:
            warnings.append(
                f"Beat {i+1} ('{beat.title}') used fallback block due to invalid JSON."
            )
            data = fallback_block(beat.title)

        # Ensure required keys exist; if missing, fill from fallback
        required_keys = ["voiceover", "on_screen", "shots", "broll", "captions"]
        fb = fallback_block(beat.title)
        for key in required_keys:
            if key not in data or data[key] in (None, "", []):
                warnings.append(
                    f"Beat {i+1} ('{beat.title}') missing key '{key}', using fallback."
                )
                data[key] = fb[key]

        # Attach metadata for clarity
        block = {
            "beat_index": beat.index,
            "beat_title": beat.title,
            "t_start": beat.t_start,
            "t_end": beat.t_end,
            "voiceover": data["voiceover"],
            "on_screen": data["on_screen"],
            "shots": data["shots"],
            "broll": data["broll"],
            "captions": data["captions"],
        }
        beats_blocks.append(block)

    return beats_blocks, warnings


def generate_video_script(
    req: VideoRequest,
    debug_first: bool = False,
) -> VideoScriptResponse:
    """
    Main entry point: plan + script + package response.
    """
    plan = plan_video(req)
    beats_blocks, warnings = script_video_from_plan(req, plan, debug_first=debug_first)
    return VideoScriptResponse(
        plan=plan,
        beats=beats_blocks,
        warnings=warnings,
    )
