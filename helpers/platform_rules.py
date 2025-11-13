"""
Platform rules and character caps for Marketeer.

This keeps all platform-specific limits in one place so that
copy_pipeline can look them up easily.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class PlatformConfig:
    name: str
    char_cap: int
    hashtags_max: int = 0
    emoji_max: int = 0


# You can tweak these later to match your marketing notebook
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
    "Twitter": PlatformConfig(  # or "X"
        name="Twitter/X",
        char_cap=280,
        hashtags_max=2,
        emoji_max=2,
    ),
}
# Default platform if user passes something unknown
DEFAULT_PLATFORM_NAME = "Instagram"
