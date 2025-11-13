"""
Copy generation pipeline for Marketeer.

This wraps the low-level LLM client and the helper utilities
into a single `generate_copy` function that other parts of
the app (like the Gradio UI) can call.

High level:
- Build a structured prompt using the provided context.
- Call the LLM to generate text.
- Run validators (banned terms, length caps, etc.).
- Return raw text, final text, and an audit log.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple

from .llm_client import generate_text
from helpers.platform_rules import PLATFORM_RULES, DEFAULT_PLATFORM_NAME, PlatformConfig
from helpers.validators import validate_and_edit


@dataclass
class CopyRequest:
    brand: str
    product: str
    audience: str
    goal: str
    platform_name: str
    tone: str
    cta_style: str
    extra_context: str = ""


@dataclass
class CopyResponse:
    platform: str
    raw: str
    final: str
    cap: int
    audit: List[Dict[str, Any]]


def _get_platform_config(name: str) -> PlatformConfig:
    """Return a known PlatformConfig or default to Instagram."""
    if name in PLATFORM_RULES:
        return PLATFORM_RULES[name]
    # allow simple aliases like "X" or "Twitter/X" later if you want
    return PLATFORM_RULES[DEFAULT_PLATFORM_NAME]


def _build_prompt(req: CopyRequest, platform: PlatformConfig) -> str:
    """
    Build a reasonably structured prompt for the LLM.

    This is intentionally simple for now; you can make it
    fancier later (add examples, formatting, etc.).
    """

    lines = [
        f"You are an expert social media marketer.",
        f"Write a single post for {platform.name}.",
        "",
        f"Brand: {req.brand}",
        f"Product/Offer: {req.product}",
        f"Target audience: {req.audience}",
        f"Campaign goal: {req.goal}",
        f"Tone: {req.tone}",
        f"Call-to-action style: {req.cta_style}",
    ]

    if req.extra_context.strip():
        lines.append(f"Extra context: {req.extra_context.strip()}")

    lines.append("")
    lines.append(
        f"Keep the copy within approximately {platform.char_cap} characters, "
        f"and make it engaging but natural."
    )
    lines.append("Do not include explanations, just the post text itself.")

    return "\n".join(lines)


def generate_copy(req: CopyRequest) -> CopyResponse:
    """
    Main entry point for marketing copy generation.

    1) Resolve platform config.
    2) Build a prompt.
    3) Call the LLM.
    4) Run validators and collect audit.
    5) Return structured response.
    """
    platform = _get_platform_config(req.platform_name)

    prompt = _build_prompt(req, platform)

    raw_text = generate_text(
        prompt=prompt,
        max_new_tokens=256,
        temperature=0.8,
        top_p=0.9,
    )

    final_text, audit = validate_and_edit(raw_text, platform)

    return CopyResponse(
        platform=platform.name,
        raw=raw_text,
        final=final_text,
        cap=platform.char_cap,
        audit=audit,
    )
