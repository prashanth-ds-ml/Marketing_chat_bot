"""
LangChain-based chat helper for copy generation.

We use:
- PromptTemplate from langchain_core
- MarketeerLLM (LangChain LLM wrapper around generate_text)
and keep chat history in the UI (list of [user, assistant] pairs).
"""

from typing import List, Tuple

from langchain_core.prompts import PromptTemplate

from .langchain_llm import MarketeerLLM
from .copy_pipeline import CopyRequest
from helpers.platform_rules import PLATFORM_RULES, DEFAULT_PLATFORM_NAME, PlatformConfig
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
- Tone: {tone}
- Call-to-action style: {cta_style}
- Extra context: {extra_context}

Keep the final post within approximately {char_cap} characters,
and make it engaging but natural.

Below is the chat conversation so far between you and the user
about this campaign:

{history}

Now the user says:
User: {input}

Respond as the assistant with ONLY the post text or edited post text
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
            "history",
            "input",
        ],
        template=template.strip(),
    )


def _format_history(history_pairs: List[Tuple[str, str]]) -> str:
    """
    Convert list of (user, assistant) messages into a text transcript.
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

    - Uses LangChain PromptTemplate + MarketeerLLM
    - Uses history_pairs (from Gradio Chatbot) as conversation history
    - Applies validators (banned terms, char caps)
    - Returns final_text, raw_text, audit
    """
    platform_cfg = _get_platform_config(req.platform_name)

    prompt_tmpl = build_chat_prompt_template()
    history_text = _format_history(history_pairs)

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
        history=history_text,
        input=user_message,
    )

    llm = MarketeerLLM()
    raw_text = llm.invoke(prompt_str)

    final_text, audit = validate_and_edit(raw_text, platform_cfg)

    return final_text, raw_text, audit
