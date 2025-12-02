# core_logic/video_pipeline.py

"""
Video script generation pipeline for Marketeer.

Phase 5: Use a structured Pydantic schema (VideoScriptResponse)
while keeping the external behaviour compatible with the existing UI.

High-level flow:
1. Build a simple beat plan based on blueprint + duration.
2. For each beat, ask the LLM for a JSON block with:
   - voiceover
   - on_screen
   - shots
   - broll
   - captions
3. Parse JSON into VideoBeat models.
4. Return a VideoScriptResponse (plan + warnings).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Dict, Any

from core_logic.llm_client import generate_text
from core_logic.video_schema import (
    VideoBeat,
    VideoPlan,
    VideoScriptResponse,
)


# --------------------------------------------------------------------
# Request object coming from UI
# --------------------------------------------------------------------


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


# --------------------------------------------------------------------
# Internal helpers: plan building & prompting
# --------------------------------------------------------------------


def _build_basic_plan(req: VideoRequest) -> VideoPlan:
    """
    Build a very simple beat plan based on blueprint and duration.

    Right now we keep this deterministic and lightweight.
    Later, you can make this itself LLM-driven if you want.
    """
    total = max(req.duration_sec, 5)
    blueprint = (req.blueprint_name or "short_ad").lower()

    if blueprint == "short_ad":
        # 3-beat: Hook -> Product -> CTA
        beats_meta = [
            ("Hook / Problem", "Hook viewer, show the pain or context.", 0.0, total * 0.33),
            ("Product Moment", "Show product solving the problem.", total * 0.33, total * 0.66),
            ("CTA / Finish", "Wrap up and clear CTA.", total * 0.66, total),
        ]
    elif blueprint == "ugc_review":
        # 4-beat: Intro -> Problem -> Experience -> Recommendation
        beats_meta = [
            ("Intro / Self", "Introduce the speaker as a real user.", 0.0, total * 0.25),
            ("Problem", "Describe the problem or frustration.", total * 0.25, total * 0.5),
            ("Experience", "Explain how using the product felt / helped.", total * 0.5, total * 0.75),
            ("Recommendation", "Recommend the product and invite viewer to try.", total * 0.75, total),
        ]
    else:  # how_to or fallback
        # 4-beat: Hook -> Step(s) -> Result -> CTA
        beats_meta = [
            ("Hook / Promise", "Hook viewer and promise what they will learn.", 0.0, total * 0.25),
            ("Step-by-step (1)", "Show the first main step.", total * 0.25, total * 0.5),
            ("Step-by-step (2)", "Show the second main step or refinement.", total * 0.5, total * 0.75),
            ("Result / CTA", "Show final outcome and clear CTA.", total * 0.75, total),
        ]

    beats: List[VideoBeat] = []
    for idx, (title, goal, t_start, t_end) in enumerate(beats_meta):
        beats.append(
            VideoBeat(
                beat_index=idx,
                title=title,
                goal=goal,
                t_start=float(round(t_start, 2)),
                t_end=float(round(t_end, 2)),
                voiceover="",    # to be filled by LLM
                on_screen="",    # to be filled by LLM
                shots=[],
                broll=[],
                captions=[],
            )
        )

    plan = VideoPlan(
        blueprint_name=req.blueprint_name,
        duration_sec=total,
        platform_name=req.platform_name,
        style=req.style,
        beats=beats,
    )
    return plan


def _build_beat_prompt(req: VideoRequest, plan: VideoPlan, beat: VideoBeat) -> str:
    """
    Build an instruction to generate **one beat** as a JSON object.
    """
    return f"""
You are helping create a short-form marketing video script.

Brand: {req.brand}
Product: {req.product}
Audience: {req.audience}
Campaign goal: {req.goal}
Platform: {req.platform_name}
Overall style: {req.style}
Extra context: {req.extra_context}

We are currently working on one beat of the video:

- Blueprint: {plan.blueprint_name}
- Beat index: {beat.beat_index}
- Beat title: {beat.title}
- Beat goal: {beat.goal}
- Start time: {beat.t_start} seconds
- End time: {beat.t_end} seconds

Return **only** a JSON object (no markdown, no backticks) with this shape:

{{
  "voiceover": "string, the spoken line(s) for this beat",
  "on_screen": "string, short text shown on screen",
  "shots": ["list of camera shot ideas, strings"],
  "broll": ["optional list of B-roll ideas, strings"],
  "captions": ["optional list of caption lines, strings"]
}}

The voiceover should match the platform and style, and help achieve the beat goal.
Keep it concise but vivid.
""".strip()


def _extract_json_from_response(raw: str) -> Dict[str, Any]:
    """
    Try to extract a JSON object from the LLM response.

    If it's already plain JSON, parse that.
    If it's inside a markdown ```json block, extract the inner part.
    Raises ValueError if parsing fails.
    """
    text = raw.strip()

    # Common case: LLM wraps in ```json ... ```
    if "```" in text:
        # Take the content between the first pair of ``` blocks
        parts = text.split("```")
        # Expected pattern: ["", "json\\n{...}", ""]
        if len(parts) >= 3:
            candidate = parts[1]
            # Strip a leading "json" or "JSON" line
            candidate = candidate.lstrip().split("\n", 1)
            if len(candidate) == 2 and candidate[0].lower() in ("json", "json:"):
                text = candidate[1].strip()
            else:
                text = "\n".join(candidate).strip()

    return json.loads(text)


# --------------------------------------------------------------------
# Public API: generate_video_script
# --------------------------------------------------------------------


def generate_video_script(
    req: VideoRequest,
    debug_first: bool = False,
) -> VideoScriptResponse:
    """
    Main entry point used by the UI.

    Generates a structured VideoScriptResponse (plan + warnings). The
    UI can still access:
        resp.plan
        resp.beats   (alias for resp.plan.beats)
        resp.warnings
    """
    plan = _build_basic_plan(req)
    warnings: List[str] = []
    beats_out: List[VideoBeat] = []

    for idx, beat in enumerate(plan.beats):
        prompt = _build_beat_prompt(req, plan, beat)

        raw = generate_text(
            prompt=prompt,
            max_new_tokens=256,
            temperature=0.7,
            top_p=0.9,
        )

        if debug_first and idx == 0:
            print("=== RAW FIRST BEAT RESPONSE ===")
            print(raw)
            print("=" * 32)

        try:
            data = _extract_json_from_response(raw)
            # Merge structured info into the beat
            beat_updated = VideoBeat(
                beat_index=beat.beat_index,
                title=beat.title,
                goal=beat.goal,
                t_start=beat.t_start,
                t_end=beat.t_end,
                voiceover=str(data.get("voiceover", "")).strip(),
                on_screen=str(data.get("on_screen", "")).strip(),
                shots=list(data.get("shots", []) or []),
                broll=list(data.get("broll", []) or []),
                captions=list(data.get("captions", []) or []),
            )
            beats_out.append(beat_updated)
        except Exception as e:
            warnings.append(
                f"Beat {beat.beat_index}: failed to parse JSON from model response ({e})."
            )
            # Fallback: keep the original beat with generic placeholders
            beats_out.append(
                VideoBeat(
                    beat_index=beat.beat_index,
                    title=beat.title,
                    goal=beat.goal,
                    t_start=beat.t_start,
                    t_end=beat.t_end,
                    voiceover="",
                    on_screen="",
                    shots=[],
                    broll=[],
                    captions=[],
                )
            )

    # Construct final structured response
    final_plan = VideoPlan(
        blueprint_name=plan.blueprint_name,
        duration_sec=plan.duration_sec,
        platform_name=plan.platform_name,
        style=plan.style,
        beats=beats_out,
    )

    resp = VideoScriptResponse(
        plan=final_plan,
        warnings=warnings,
    )
    return resp
