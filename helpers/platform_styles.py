"""
Platform personality profiles for Marketeer.

These capture HOW each platform prefers to communicate:
- voice & tone
- emoji usage
- hashtag style
- formatting preferences
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class PlatformStyle:
    name: str
    voice: str
    emoji_guideline: str
    hashtag_guideline: str
    formatting_guideline: str
    extra_notes: str = ""


# Core style definitions
PLATFORM_STYLES: Dict[str, PlatformStyle] = {
    "Instagram": PlatformStyle(
        name="Instagram",
        voice="Casual, energetic, playful. Focus on vibes, feelings, and moments.",
        emoji_guideline=(
            "Use emojis naturally to enhance mood (1–5 per post). "
            "Avoid overloading every word with emojis."
        ),
        hashtag_guideline=(
            "Use 3–5 relevant hashtags at the end of the post. "
            "Mix branded and generic hashtags (e.g., #BrewBlissCafe, #WeekendVibes)."
        ),
        formatting_guideline=(
            "Short paragraphs, line breaks for readability, occasional emphasis with ALL CAPS "
            "or **bold style** (if supported)."
        ),
        extra_notes="Hook in the first line. Make it thumb-stopping.",
    ),
    "Facebook": PlatformStyle(
        name="Facebook",
        voice="Friendly and conversational, but a bit more explanatory than Instagram.",
        emoji_guideline=(
            "Use emojis sparingly (0–2 per post), mainly to highlight key ideas."
        ),
        hashtag_guideline=(
            "Hashtags are optional. If used, limit to 1–2 relevant tags."
        ),
        formatting_guideline=(
            "1–3 short paragraphs. Clear, readable, and easy to skim."
        ),
        extra_notes="Good place for slightly longer explanations or promotions.",
    ),
    "LinkedIn": PlatformStyle(
        name="LinkedIn",
        voice=(
            "Professional, clear, and value-driven. Focus on benefits, outcomes, and credibility. "
            "Write as if speaking to working professionals."
        ),
        emoji_guideline=(
            "Avoid emojis in most cases. If absolutely necessary, limit to 0–1 subtle emoji."
        ),
        hashtag_guideline=(
            "Use 0–3 professional hashtags at the end if needed (e.g., #Marketing, #CustomerExperience)."
        ),
        formatting_guideline=(
            "Short, well-structured paragraphs. Avoid slang. No all-caps. "
            "Sound confident and polished."
        ),
        extra_notes="Highlight business value, customer experience, and trust.",
    ),
    "Twitter": PlatformStyle(
        name="Twitter",
        voice="Short, punchy, and to the point. Witty if possible.",
        emoji_guideline=(
            "Use emojis sparingly (0–2) to add flavor, not clutter."
        ),
        hashtag_guideline=(
            "Use 1–3 short hashtags. Prioritize relevance over quantity."
        ),
        formatting_guideline=(
            "Single-paragraph or a short thread. Max impact in minimal characters."
        ),
        extra_notes="Lead with the core hook in the first few words.",
    ),
    # Fallback / generic style
    "Generic": PlatformStyle(
        name="Generic",
        voice="Clear, friendly, and informative.",
        emoji_guideline="Use emojis only if they genuinely add clarity or mood.",
        hashtag_guideline="Use a small number of relevant hashtags if appropriate.",
        formatting_guideline="Keep sentences and paragraphs easy to read.",
        extra_notes="Adapt tone slightly based on the brand and audience.",
    ),
}


DEFAULT_STYLE_NAME = "Generic"


def get_platform_style(name: str) -> PlatformStyle:
    """
    Return the platform style for the given name, falling back to Generic.
    """
    if name in PLATFORM_STYLES:
        return PLATFORM_STYLES[name]
    return PLATFORM_STYLES[DEFAULT_STYLE_NAME]
