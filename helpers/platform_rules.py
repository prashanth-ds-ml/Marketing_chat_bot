from dataclasses import dataclass
from typing import Dict


# --- Core platform config (caps, hashtags, emojis) ---


@dataclass
class PlatformConfig:
    """
    Basic platform constraints used by the validator and pipelines.
    """
    name: str
    char_cap: int
    hashtags_max: int
    emoji_max: int

    @property
    def cap(self) -> int:
        """
        Backwards-compatible alias for char_cap.
        Some older code might reference .cap instead of .char_cap.
        """
        return self.char_cap


# Character caps and simple rules per platform.
PLATFORM_RULES: Dict[str, PlatformConfig] = {
    "Instagram": PlatformConfig(
        name="Instagram",
        char_cap=2200,
        hashtags_max=5,
        emoji_max=5,
    ),
    "Facebook": PlatformConfig(
        name="Facebook",
        char_cap=125,
        hashtags_max=0,
        emoji_max=1,
    ),
    "LinkedIn": PlatformConfig(
        name="LinkedIn",
        char_cap=3000,
        hashtags_max=3,
        emoji_max=2,
    ),
    "Twitter": PlatformConfig(
        name="Twitter",
        char_cap=280,
        hashtags_max=2,
        emoji_max=2,
    ),
}

DEFAULT_PLATFORM_NAME: str = "Instagram"


# --- Banned phrase map (for safer language) ---


# Regex patterns mapped to replacement phrases.
# The validator will use this to make copy less spammy / risky.
BANNED_MAP: Dict[str, str] = {
    r"\bguarantee(d|s)?\b": "aim to",
    r"\bno[-\s]?risk\b": "low risk",
    # Add more patterns as needed
}


# --- Platform style profiles (Phase 3) ---


# Each entry describes how copy should "feel" on that platform.
# These are used at prompt level in chat_chain so the LLM
# clearly understands the expectations per platform.
PLATFORM_STYLES: Dict[str, Dict] = {
    "Instagram": {
        "name": "Instagram",
        "voice": (
            "fun, casual, and energetic. Speak like a friendly social media manager "
            "talking to followers."
        ),
        "emoji_guideline": (
            "Emojis are welcome. Use them to enhance the energy of the post, "
            "but avoid clutter."
        ),
        "hashtag_guideline": (
            "Use 3–5 relevant hashtags at the end of the post. "
            "Hashtags should be short, readable, and on-topic."
        ),
        "length_guideline": "Short to medium length caption is ideal.",
    },
    "Facebook": {
        "name": "Facebook",
        "voice": (
            "friendly and conversational, but slightly more explanatory than Instagram."
        ),
        "emoji_guideline": (
            "Emojis are allowed, but use them sparingly for emphasis only."
        ),
        "hashtag_guideline": (
            "One or two hashtags are okay, but they are optional. "
            "Focus more on clear, readable text."
        ),
        "length_guideline": "Short to medium length post with a clear main message.",
    },
    "LinkedIn": {
        "name": "LinkedIn",
        "voice": (
            "professional, clear, and value-focused. "
            "Write like a marketer speaking to working professionals."
        ),
        "emoji_guideline": (
            "Avoid or minimize emojis. If used at all, keep them professional and sparse."
        ),
        "hashtag_guideline": (
            "1–3 relevant, professional hashtags are acceptable at the end. "
            "Do not overuse hashtags."
        ),
        "length_guideline": (
            "Short to medium length update. Prioritize clarity and professionalism."
        ),
    },
    "Twitter": {
        "name": "Twitter",
        "voice": (
            "short, punchy, and attention-grabbing. "
            "Get to the point quickly."
        ),
        "emoji_guideline": (
            "Emojis are fine but keep them minimal and highly relevant."
        ),
        "hashtag_guideline": (
            "1–2 strong, relevant hashtags max. Avoid hashtag spam."
        ),
        "length_guideline": "Very concise. Every word should earn its place.",
    },
}

DEFAULT_PLATFORM_STYLE: Dict = PLATFORM_STYLES.get("Instagram")


def get_platform_style(name: str) -> Dict:
    """
    Return a style profile dict for a given platform name.

    If the platform is unknown, fall back to DEFAULT_PLATFORM_STYLE.
    """
    return PLATFORM_STYLES.get(name, DEFAULT_PLATFORM_STYLE)
