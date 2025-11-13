"""
Validation and gentle editing layer for generated copy.

This module:
- Applies banned-term replacements (e.g., "guaranteed" -> "aim to").
- Trims text to platform character cap.
- Returns an audit log of what changed.
"""

from typing import List, Dict, Tuple

from .platform_rules import PlatformConfig


# Soft language map: you can expand this list as you like
BANNED_MAP = {
    "guaranteed": "aim to",
    "guarantee": "aim to",
    "no risk": "low risk",
}


def _apply_banned_terms(text: str) -> Tuple[str, List[Dict]]:
    """Replace banned phrases and record changes."""
    audit: List[Dict] = []
    cleaned = text

    for bad, replacement in BANNED_MAP.items():
        if bad.lower() in cleaned.lower():
            before = cleaned
            # simple case-insensitive replace
            cleaned = cleaned.replace(bad, replacement)
            cleaned = cleaned.replace(bad.capitalize(), replacement)
            cleaned = cleaned.replace(bad.upper(), replacement.upper())
            audit.append(
                {
                    "rule": "banned_term",
                    "bad": bad,
                    "replacement": replacement,
                }
            )

    return cleaned, audit


def _apply_length_cap(text: str, platform: PlatformConfig) -> Tuple[str, List[Dict]]:
    """Trim text to the platform's character cap if necessary."""
    audit: List[Dict] = []
    cap = platform.char_cap

    if len(text) > cap:
        before_len = len(text)
        trimmed = text[:cap].rstrip()
        audit.append(
            {
                "rule": "length_trim",
                "before_len": before_len,
                "after_len": len(trimmed),
                "cap": cap,
            }
        )
        return trimmed, audit

    return text, audit


def validate_and_edit(
    text: str,
    platform: PlatformConfig,
) -> Tuple[str, List[Dict]]:
    """
    Apply all validators in order and collect a combined audit log.

    Returns:
        final_text, audit_log
    """
    audit_log: List[Dict] = []

    # 1) banned terms
    text, banned_audit = _apply_banned_terms(text)
    audit_log.extend(banned_audit)

    # 2) length trim
    text, trim_audit = _apply_length_cap(text, platform)
    audit_log.extend(trim_audit)

    # (you can add more steps later: CTA normalization, emoji limits, etc.)
    return text, audit_log
