"""
Video blueprints for Marketeer.

These define high-level structures (beats) for different
short-form video types like short ads, UGC reviews, and how-tos.
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class BeatTemplate:
    id: str
    title: str
    goal: str
    weight: float  # relative share of total duration (sum of weights ≈ 1.0)


@dataclass
class Blueprint:
    name: str
    description: str
    beats: List[BeatTemplate]


def _short_ad() -> Blueprint:
    beats = [
        BeatTemplate(
            id="hook",
            title="Hook",
            goal="Grab attention in the first second and stop the scroll.",
            weight=0.2,
        ),
        BeatTemplate(
            id="problem",
            title="Problem",
            goal="Show the pain point the viewer feels right now.",
            weight=0.2,
        ),
        BeatTemplate(
            id="solution",
            title="Solution",
            goal="Introduce the product as the clear solution.",
            weight=0.3,
        ),
        BeatTemplate(
            id="proof",
            title="Proof",
            goal="Show quick proof: results, social proof, or credibility.",
            weight=0.2,
        ),
        BeatTemplate(
            id="cta",
            title="Call to Action",
            goal="Give a clear, simple next step.",
            weight=0.1,
        ),
    ]
    return Blueprint(
        name="short_ad",
        description="Punchy short ad for Reels/Shorts/TikTok with strong hook and CTA.",
        beats=beats,
    )


def _ugc_review() -> Blueprint:
    beats = [
        BeatTemplate(
            id="intro",
            title="UGC Intro",
            goal="Introduce yourself quickly and mention the product.",
            weight=0.2,
        ),
        BeatTemplate(
            id="before",
            title="Before",
            goal="Describe life before using the product (the struggle).",
            weight=0.25,
        ),
        BeatTemplate(
            id="experience",
            title="Experience",
            goal="Describe what it was like actually trying the product.",
            weight=0.3,
        ),
        BeatTemplate(
            id="after",
            title="After",
            goal="Describe the positive results / outcome.",
            weight=0.15,
        ),
        BeatTemplate(
            id="recommend",
            title="Recommendation & CTA",
            goal="Recommend the product and give a simple prompt to act.",
            weight=0.1,
        ),
    ]
    return Blueprint(
        name="ugc_review",
        description="User-generated style review with before/after flow.",
        beats=beats,
    )


def _how_to() -> Blueprint:
    beats = [
        BeatTemplate(
            id="intro",
            title="Intro",
            goal="Tell viewers what they will learn and why it matters.",
            weight=0.2,
        ),
        BeatTemplate(
            id="step1",
            title="Step 1",
            goal="Explain and demo the first key step.",
            weight=0.25,
        ),
        BeatTemplate(
            id="step2",
            title="Step 2",
            goal="Explain and demo the second key step.",
            weight=0.25,
        ),
        BeatTemplate(
            id="step3",
            title="Step 3",
            goal="Optional third step or bonus tip.",
            weight=0.15,
        ),
        BeatTemplate(
            id="wrap",
            title="Recap & CTA",
            goal="Recap key points and suggest the next action.",
            weight=0.15,
        ),
    ]
    return Blueprint(
        name="how_to",
        description="Educational explainer with clear steps and recap.",
        beats=beats,
    )


BLUEPRINTS: Dict[str, Blueprint] = {
    "short_ad": _short_ad(),
    "ugc_review": _ugc_review(),
    "how_to": _how_to(),
}


DEFAULT_BLUEPRINT = "short_ad"


def get_blueprint(name: str) -> Blueprint:
    """Return a known blueprint or the default one."""
    if name in BLUEPRINTS:
        return BLUEPRINTS[name]
    return BLUEPRINTS[DEFAULT_BLUEPRINT]
