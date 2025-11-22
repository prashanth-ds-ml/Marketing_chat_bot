"""
LangChain-based chat helper for copy generation.

We use:
- PromptTemplate from langchain_core
- ChatHuggingFace model from llm_config
- Simple chat history from the Gradio Chatbot (list of [user, assistant] pairs)

We DO NOT use SystemMessage, because the current model's chat template
does not support a "system" role. Instead, we fold all instructions and
campaign context into a single HumanMessage prompt, including platform
style guidelines (Phase 3).
"""

from typing import List, Tuple

from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage

from core_logic.llm_config import get_local_chat_model
from .copy_pipeline import CopyRequest
from helpers.platform_rules import (
    PLATFORM_RULES,
    DEFAULT_PLATFORM_NAME,
    PlatformConfig,
    get_platform_style,
)
from helpers.validators import validate_and_edit


def _get_platform_config(name: str) -> PlatformConfig:
    if name in PLATFORM_RULES:
        return PLATFORM_RULES[name]
    return PLATFORM_RULES[DEFAULT_PLATFORM_NAME]


def build_chat_prompt_template() -> PromptTemplate:
    """
    Template takes:
    - brand, product, audience, goal, platform, tone, cta_style, extra_context
    - char_cap
    - style_voice, style_emoji_guideline, style_hashtag_guideline, style_length_guideline
    - history (chat transcript as text)
    - input (latest user message)
    """
    template = """
You are an expert social media marketer.
You help refine and iterate on social media posts for {platform}.

Campaign context:
- Brand: {brand}
- Product/Offer: {product}
- Target audience: {audience}
- Campaign goal: {goal}
- Tone requested by user: {tone}
- Call-to-action style: {cta_style}
- Extra context from the user: {extra_context}

Platform style guidelines for {platform}:
- Voice and personality: {style_voice}
- Emojis: {style_emoji_guideline}
- Hashtags: {style_hashtag_guideline}
- Length: {style_length_guideline}
- Character limit: approximately {char_cap} characters.

Here is the conversation so far between you and the user
about this campaign:

{history}

Now the user says:
{input}

Your task:
- Follow the platform style guidelines and tone.
- Respect the character limit as much as reasonably possible.
- If the user asks to edit or adapt an existing post, transform it accordingly.
- Do NOT include explanations, analysis, or labels in your answer.

Respond with ONLY the post text or edited post text
the user asked for. Do not add any extra commentary.
"""
    return PromptTemplate(
        input_variables=[
            "brand",
            "product",
            "audience",
            "goal",
            "platform",
            "tone",
            "cta_style",
            "extra_context",
            "char_cap",
            "style_voice",
            "style_emoji_guideline",
            "style_hashtag_guideline",
            "style_length_guideline",
            "history",
            "input",
        ],
        template=template.strip(),
    )


def _format_history(history_pairs: List[Tuple[str, str]]) -> str:
    """
    Convert list of (user, assistant) messages into a simple text transcript.
    """
    if not history_pairs:
        return "(No previous conversation yet.)"

    lines = []
    for u, a in history_pairs:
        if u:
            lines.append(f"User: {u}")
        if a:
            lines.append(f"Assistant: {a}")
    return "\n".join(lines)


def chat_turn(
    req: CopyRequest,
    user_message: str,
    history_pairs: List[Tuple[str, str]],
):
    """
    Run one chat turn:

    - Uses LangChain PromptTemplate + ChatHuggingFace (via get_local_chat_model)
    - Uses history_pairs (from Gradio Chatbot) as conversation history
    - Applies platform style guidelines (Phase 3)
    - Applies validators (banned terms, char caps, etc.)
    - Returns final_text, raw_text, audit
    """
    platform_cfg = _get_platform_config(req.platform_name)
    style = get_platform_style(req.platform_name)

    prompt_tmpl = build_chat_prompt_template()
    history_text = _format_history(history_pairs)

    # Build the full prompt string with context + style + history + latest user message
    prompt_str = prompt_tmpl.format(
        brand=req.brand or "",
        product=req.product or "",
        audience=req.audience or "",
        goal=req.goal or "",
        platform=style.get("name", req.platform_name or "Unknown platform"),
        tone=req.tone or "friendly",
        cta_style=req.cta_style or "soft",
        extra_context=req.extra_context or "",
        char_cap=str(platform_cfg.cap)
        if hasattr(platform_cfg, "cap")
        else str(getattr(platform_cfg, "char_cap", 280)),
        style_voice=style.get("voice", ""),
        style_emoji_guideline=style.get("emoji_guideline", ""),
        style_hashtag_guideline=style.get("hashtag_guideline", ""),
        style_length_guideline=style.get("length_guideline", ""),
        history=history_text,
        input=user_message,
    )

    # Call the ChatHuggingFace model with a single HumanMessage
    chat_model = get_local_chat_model()
    ai_msg = chat_model.invoke([HumanMessage(content=prompt_str)])
    raw_text = ai_msg.content

    # Apply your existing validators (banned phrases, length, etc.)
    final_text, audit = validate_and_edit(raw_text, platform_cfg)

    return final_text, raw_text, audit
