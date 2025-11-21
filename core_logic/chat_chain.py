"""
LangChain-based chat helper for copy generation.

We use:
- PromptTemplate from langchain_core
- ChatHuggingFace model from llm_config
- Simple chat history from the Gradio Chatbot (list of [user, assistant] pairs)

We DO NOT use SystemMessage, because the current model's chat template
does not support a "system" role. Instead, we fold all instructions and
campaign context into a single HumanMessage prompt.
"""

from typing import List, Tuple

from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage

from core_logic.llm_config import get_local_chat_model
from .copy_pipeline import CopyRequest
from helpers.platform_rules import PLATFORM_RULES, DEFAULT_PLATFORM_NAME, PlatformConfig
from helpers.platform_styles import get_platform_style
from helpers.validators import validate_and_edit


def _get_platform_config(name: str) -> PlatformConfig:
    if name in PLATFORM_RULES:
        return PLATFORM_RULES[name]
    return PLATFORM_RULES[DEFAULT_PLATFORM_NAME]


def build_chat_prompt_template() -> PromptTemplate:
    """
    Template takes:
    - brand, product, audience, goal, platform
    - tone, cta_style, extra_context
    - char_cap
    - platform_style (formatted description)
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
- Preferred tone: {tone}
- Call-to-action style: {cta_style}
- Extra context: {extra_context}

Platform style guidelines:
{platform_style}

Keep the final post within approximately {char_cap} characters,
and make it engaging but natural.

Here is the conversation so far between you and the user
about this campaign:

{history}

Now the user says:
{input}

Respond with ONLY the post text or edited post text
the user asked for. Do not include explanations, analysis, or labels.
Just the post.
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
            "platform_style",
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


def _format_platform_style(platform_name: str) -> str:
    """
    Get a human-readable style description for the given platform.
    """
    style = get_platform_style(platform_name)

    lines = [
        f"- Platform: {style.name}",
        f"- Voice: {style.voice}",
        f"- Emojis: {style.emoji_guideline}",
        f"- Hashtags: {style.hashtag_guideline}",
        f"- Formatting: {style.formatting_guideline}",
    ]
    if style.extra_notes:
        lines.append(f"- Extra notes: {style.extra_notes}")
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
    - Applies validators (banned terms, char caps)
    - Returns final_text, raw_text, audit
    """
    platform_cfg = _get_platform_config(req.platform_name)
    platform_style_text = _format_platform_style(req.platform_name)

    prompt_tmpl = build_chat_prompt_template()
    history_text = _format_history(history_pairs)

    # Build the full prompt string with context + style + history + latest user message
    prompt_str = prompt_tmpl.format(
        brand=req.brand or "",
        product=req.product or "",
        audience=req.audience or "",
        goal=req.goal or "",
        platform=platform_cfg.name,
        tone=req.tone or "friendly",
        cta_style=req.cta_style or "soft",
        extra_context=req.extra_context or "",
        char_cap=str(platform_cfg.char_cap),
        platform_style=platform_style_text,
        history=history_text,
        input=user_message,
    )

    # Call the ChatHuggingFace model with a single HumanMessage
    chat_model = get_local_chat_model()
    ai_msg = chat_model.invoke([HumanMessage(content=prompt_str)])
    raw_text = ai_msg.content

    # Apply your existing validators (banned phrases, length caps, etc.)
    final_text, audit = validate_and_edit(raw_text, platform_cfg)

    return final_text, raw_text, audit
