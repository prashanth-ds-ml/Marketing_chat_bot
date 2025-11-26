"""
Agent-style chat for Marketeer using LangChain tools.

- Uses ChatHuggingFace from llm_config.get_local_chat_model()
- Uses rewrite / tone tools from rewrite_tools.py
- Implements a tiny tool-calling loop with .bind_tools() (no AgentExecutor).
"""

from typing import Any, Dict, List, Tuple, Union

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool

from core_logic.llm_config import get_local_chat_model
from core_logic.copy_pipeline import CopyRequest
from helpers.platform_styles import get_platform_style  # <-- dataclass style
from core_logic.rewrite_tools import get_rewrite_tools


Message = Union[HumanMessage, AIMessage]


# --------------------------------------------------------------------
# Helpers for platform style and history
# --------------------------------------------------------------------


def _get_style_attr(style: Any, field: str, default: str = "") -> str:
    """
    Safe attribute getter for PlatformStyle dataclass (or dict fallback).

    This handles both:
    - dataclass PlatformStyle (preferred)
    - dict-like (in case of accidental mix)
    """
    if style is None:
        return default

    # Dataclass / object path
    if hasattr(style, field):
        value = getattr(style, field)
        return default if value is None else str(value)

    # Dict path (just in case)
    if isinstance(style, dict):
        value = style.get(field, default)
        return default if value is None else str(value)

    return default


def _build_system_prompt(req: CopyRequest) -> str:
    """
    Build a system instruction that explains:
    - you are a marketing copywriter
    - you know the campaign context
    - you may optionally use tools to rewrite/edit
    """
    # This comes from helpers.platform_styles and returns a PlatformStyle dataclass
    style = get_platform_style(req.platform_name or "Instagram")

    # Access attributes directly (NO dict-style indexing anywhere)
    voice = getattr(style, "voice", "")
    emoji_guideline = getattr(style, "emoji_guideline", "")
    hashtag_guideline = getattr(style, "hashtag_guideline", "")
    formatting_guideline = getattr(style, "formatting_guideline", "")
    extra_notes = getattr(style, "extra_notes", "")

    return f"""
You are Marketeer, an expert marketing copywriter.

You help users:
- write first-draft posts
- refine tone
- shorten or expand posts
- adapt copy across platforms

Campaign context:
- Brand: {req.brand}
- Product / offer: {req.product}
- Audience: {req.audience}
- Goal: {req.goal}
- Platform: {req.platform_name}
- Tone: {req.tone}
- CTA style: {req.cta_style}
- Extra context: {req.extra_context}

Platform style guidelines:
- Voice: {voice}
- Emoji usage: {emoji_guideline}
- Hashtags: {hashtag_guideline}
- Formatting: {formatting_guideline}
- Extra notes: {extra_notes}

You may have access to special tools that help you:
- adjust tone
- shorten or expand text
- remove or add emojis
- tweak style

When you respond:
- If the user clearly wants a simple answer, respond directly.
- If the user is asking to rewrite existing text (e.g. "shorten this", 
  "make it more professional", "remove emojis"), feel free to call tools
  if they are available.
- Always return clean, user-ready copy (no JSON, no debug).
    """.strip()



def _build_message_history(history_pairs: List[List[str]]) -> List[Message]:
    """
    Convert [[user, assistant], ...] into LangChain Human/AI messages.
    """
    messages: List[Message] = []
    for pair in history_pairs:
        if not pair or len(pair) != 2:
            continue
        user_text, assistant_text = pair
        if user_text:
            messages.append(HumanMessage(content=user_text))
        if assistant_text:
            messages.append(AIMessage(content=assistant_text))
    return messages


def _get_tool_map(tools: List[BaseTool]) -> Dict[str, BaseTool]:
    """
    Convenience map: tool_name -> tool object.
    """
    return {tool.name: tool for tool in tools}


# --------------------------------------------------------------------
# Main agent entry point
# --------------------------------------------------------------------


def agent_chat_turn(
    req: CopyRequest,
    user_message: str,
    history_pairs: List[List[str]] | None = None,
) -> Tuple[str, str, list]:
    ...
    history_pairs = history_pairs or []

    # 1) Build base messages: "system" prompt as a HumanMessage + history + new user
    instructions = _build_system_prompt(req)

    # IMPORTANT: use HumanMessage here, not SystemMessage
    system_msg = HumanMessage(content=instructions)

    history_msgs = _build_message_history(history_pairs)
    new_user_msg = HumanMessage(content=user_message)

    messages: List[Union[Message, ToolMessage]] = (
        [system_msg] + history_msgs + [new_user_msg]
    )


    # 2) Prepare tools & model
    tools: List[BaseTool] = get_rewrite_tools()
    tool_map = _get_tool_map(tools)

    llm = get_local_chat_model()
    llm_with_tools = llm.bind_tools(tools)

    # 3) First model call (decide whether to use tools)
    ai_msg: AIMessage = llm_with_tools.invoke(messages)
    raw_first = ai_msg.content or ""

    # If the model does not request any tools, just return its answer
    if not getattr(ai_msg, "tool_calls", None):
        final_text = raw_first.strip()
        return final_text, raw_first, []

    # 4) Execute any requested tools
    messages.append(ai_msg)
    tool_messages: List[ToolMessage] = []

    for tool_call in ai_msg.tool_calls:
        tool_name = tool_call.get("name")
        args = tool_call.get("args", {})
        call_id = tool_call.get("id") or ""

        tool = tool_map.get(tool_name)
        if tool is None:
            tool_output = f"Tool '{tool_name}' is not available."
        else:
            # LangChain tools usually implement .invoke()
            try:
                tool_output = tool.invoke(args)
            except Exception as e:
                tool_output = f"Tool '{tool_name}' failed with error: {e}"

        tool_msg = ToolMessage(
            content=str(tool_output),
            tool_call_id=call_id,
        )
        tool_messages.append(tool_msg)

    messages.extend(tool_messages)

    # 5) Second model call: let the LLM see tool results and answer
    final_ai: AIMessage = llm_with_tools.invoke(messages)
    final_text = (final_ai.content or "").strip()
    raw_second = final_ai.content or ""

    audit: list = []  # reserved for tool call logs if you want later

    return final_text, raw_second, audit
