from typing import List
from langchain_core.tools import tool
from langchain_core.tools import BaseTool


@tool
def shorten_copy(text: str, max_words: int = 40) -> str:
    """Shorten the given marketing copy while preserving core meaning and CTA."""
    # simple baseline implementation; the LLM will often rewrite again
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


@tool
def remove_emojis(text: str) -> str:
    """Remove emojis and overly playful styling from the copy."""
    # naive implementation – works fine as a starting point
    import re

    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "]+",
        flags=re.UNICODE,
    )
    no_emoji = emoji_pattern.sub("", text)
    return " ".join(no_emoji.split())


def get_rewrite_tools() -> List[BaseTool]:
    """
    Return the list of tools the agent can use.
    Add tone_shift, expand, etc. here over time.
    """
    return [shorten_copy, remove_emojis]
