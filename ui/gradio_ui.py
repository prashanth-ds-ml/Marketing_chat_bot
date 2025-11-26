"""
Gradio UI for Marketeer (copy + video script).

New UX:

- User fills the campaign form (brand, product, audience, goal, platform, tone, CTA, extra context).
- Clicking "Generate Copy" creates a FIRST DRAFT and shows it as an assistant
  message in a single chat interface.
- The user then continues the conversation in that SAME chat window
  (no separate one-shot box / separate draft box).
- Feedback is linked to the LAST assistant response via a simple
  rating + comment section under the chat.
"""

from typing import Any, Dict, List

import gradio as gr

from core_logic.copy_pipeline import CopyRequest, generate_copy
from core_logic.video_pipeline import VideoRequest, generate_video_script
# from core_logic.chat_chain import chat_turn
from core_logic.chat_agent import agent_chat_turn
from core_logic.copy_pipeline import CopyRequest




# ----- Small helpers -----


def _build_goal_text(goal_preset: str, goal_custom: str) -> str:
    """
    Combine preset and custom goal fields into one text.

    Logic:
    - If custom goal is provided, use that.
    - Else, use the preset goal (dropdown).
    - Else, empty string.
    """
    goal_custom = (goal_custom or "").strip()
    goal_preset = (goal_preset or "").strip()
    return goal_custom or goal_preset or ""


# ----- Backend wrapper functions for Gradio -----


def _generate_first_copy_ui(
    brand: str,
    product: str,
    audience: str,
    goal_preset: str,
    goal_custom: str,
    platform_name: str,
    tone: str,
    cta_style: str,
    extra_context: str,
):
    """
    First-step copy generation using the form fields.
    The result is shown as the FIRST assistant message in the chat.

    Returns:
    - chat_history: list of [user, assistant] pairs for the Chatbot component
      Here we start with a single assistant message containing the first draft.
    """
    goal_text = _build_goal_text(goal_preset, goal_custom)

    req = CopyRequest(
        brand=brand or "",
        product=product or "",
        audience=audience or "",
        goal=goal_text or "",
        platform_name=platform_name or "Instagram",
        tone=tone or "friendly",
        cta_style=cta_style or "soft",
        extra_context=extra_context or "",
    )

    resp = generate_copy(req)

    first_post = (resp.final or "").strip()
    if not first_post:
        first_post = "I tried to generate a post, but the result was empty. Please try again."

    # Seed chat: one assistant message with the first draft
    chat_history: List[List[str]] = [["", first_post]]

    return chat_history


def _chat_copy_ui(
    chat_history,
    user_message: str,
    brand: str,
    product: str,
    audience: str,
    goal_preset: str,
    goal_custom: str,
    platform_name: str,
    tone: str,
    cta_style: str,
    extra_context: str,
):
    """
    Chat handler for the Copy tab using the advanced agent with tools.

    Parameters must match the order of inputs in send_btn.click():

        inputs=[
            chatbox,
            user_msg,
            brand,
            product,
            audience,
            goal_preset,
            goal_custom,
            platform_name,
            tone,
            cta_style,
            extra_context,
        ]

    - Uses campaign context (brand, product, audience, goal, platform, tone, CTA)
    - Uses chat_history (list of [user, assistant] pairs) as previous conversation
    - Returns updated chat_history and clears the input box.
    """
    # If user_message is empty, just return the same state
    if not user_message or not user_message.strip():
        return chat_history, user_message

    # Merge preset + custom goal into a single text
    goal_text = _build_goal_text(goal_preset, goal_custom)

    # Build the CopyRequest from the form fields
    req = CopyRequest(
        brand=brand or "",
        product=product or "",
        audience=audience or "",
        goal=goal_text,
        platform_name=platform_name or "Instagram",
        tone=tone or "friendly",
        cta_style=cta_style or "soft",
        extra_context=extra_context or "",
    )

    # Gradio Chatbot history comes in as list of [user, assistant] pairs
    history_pairs = chat_history or []

    # Call our advanced agent (which can use rewrite tools internally)
    final_text, raw_text, audit = agent_chat_turn(
        req=req,
        user_message=user_message,
        history_pairs=history_pairs,
    )

    # Append the new turn to history
    new_history = history_pairs + [[user_message, final_text]]

    # Return updated history and clear the input box
    return new_history, ""


def _clear_chat():
    """
    Clear chat history.
    """
    return []


def _submit_feedback_for_last_reply(
    chat_history,
    fb_rating: str,
    fb_text: str,
    brand: str,
    platform_name: str,
    goal_preset: str,
    goal_custom: str,
):
    """
    Feedback handler tied to the LAST assistant message in the chat.

    We log:
    - Brand, Platform, Goal
    - Rating (e.g., 👍 / 👎)
    - Free-text feedback
    - The last assistant reply text

    and return a short status message.
    """
    if not chat_history:
        return "No messages yet. Generate a post or chat first, then leave feedback."

    # chat_history is a list of [user, assistant] pairs.
    # The last pair's assistant message is the one we care about.
    last_user, last_assistant = chat_history[-1]
    last_assistant = last_assistant or "(empty reply)"

    fb_rating = fb_rating or "(not provided)"
    fb_text = fb_text or "(no comment)"
    brand = brand or "(not provided)"
    platform_name = platform_name or "(not provided)"

    goal_text = _build_goal_text(goal_preset, goal_custom)
    goal_text = goal_text or "(not provided)"

    print("=== MARKETEER FEEDBACK (last reply) ===")
    print(f"Brand: {brand}")
    print(f"Platform: {platform_name}")
    print(f"Goal: {goal_text}")
    print(f"Rating: {fb_rating}")
    print("User feedback text:")
    print(fb_text)
    print("--- Last assistant reply ---")
    print(last_assistant)
    print("=======================================")

    return "✅ Thanks for your feedback on the last reply!"


def _generate_video_ui(
    brand: str,
    product: str,
    audience: str,
    goal: str,
    blueprint_name: str,
    duration_sec: int,
    platform_name: str,
    style: str,
    extra_context: str,
    debug_first: bool,
) -> Dict[str, Any]:
    """
    Wrapper around generate_video_script() for Gradio.
    Returns storyboard text, JSON, and warnings.
    """
    req = VideoRequest(
        brand=brand or "",
        product=product or "",
        audience=audience or "",
        goal=goal or "",
        blueprint_name=blueprint_name or "short_ad",
        duration_sec=int(duration_sec) if duration_sec else 20,
        platform_name=platform_name or "Instagram Reels",
        style=style or "warm",
        extra_context=extra_context or "",
    )

    resp = generate_video_script(req, debug_first=bool(debug_first))

    # Build a human-readable storyboard
    sb_lines: List[str] = []
    for block in resp.beats:
        sb_lines.append(
            f"Beat {block['beat_index'] + 1}: {block['beat_title']} "
            f"({block['t_start']}s – {block['t_end']}s)"
        )
        sb_lines.append(f"  Voiceover: {block['voiceover']}")
        sb_lines.append(f"  On-screen: {block['on_screen']}")
        sb_lines.append("  Shots:")
        for shot in block["shots"]:
            sb_lines.append(f"    • {shot}")
        sb_lines.append("  B-roll:")
        for br in block["broll"]:
            sb_lines.append(f"    • {br}")
        sb_lines.append("  Captions:")
        for cap in block["captions"]:
            sb_lines.append(f"    • {cap}")
        sb_lines.append("")  # blank line between beats

    storyboard_text = "\n".join(sb_lines).strip() or "No beats generated."

    # Warnings text
    if resp.warnings:
        warnings_text = "\n".join(f"- {w}" for w in resp.warnings)
    else:
        warnings_text = "No warnings. All beats parsed without fallback. ✅"

    # JSON-ready object
    script_json: Dict[str, Any] = {
        "plan": {
            "blueprint_name": resp.plan.blueprint_name,
            "duration_sec": resp.plan.duration_sec,
            "platform_name": resp.plan.platform_name,
            "style": resp.plan.style,
            "beats": [
                {
                    "index": b.index,
                    "title": b.title,
                    "goal": b.goal,
                    "t_start": b.t_start,
                    "t_end": b.t_end,
                }
                for b in resp.plan.beats
            ],
        },
        "beats": resp.beats,
        "warnings": resp.warnings,
    }

    return {
        "storyboard_text": storyboard_text,
        "script_json": script_json,
        "warnings_text": warnings_text,
    }


# ----- Gradio layout -----


def create_interface() -> gr.Blocks:
    """
    Create and return the Gradio Blocks interface.
    """
    with gr.Blocks(title="Marketeer – Copy & Video Script Generator") as demo:
        gr.Markdown(
            """
# Marketeer – Copy & Video Script Generator

Fill in your campaign details, generate a first draft, then refine it
in a single chat with your AI copywriter. Also generate short-form video
storyboards for your campaigns.
"""
        )

        with gr.Tabs():
            # --- Tab 1: Copy Chat (single chat interface) ---
            with gr.Tab("Copy Chat"):
                with gr.Row():
                    # LEFT COLUMN: Campaign setup
                    with gr.Column(scale=1):
                        gr.Markdown("### Campaign Setup")

                        brand = gr.Textbox(
                            label="Brand / Company",
                            placeholder="Brew Bliss Café",
                        )
                        product = gr.Textbox(
                            label="Product / Offer",
                            placeholder="signature cold brew",
                        )
                        audience = gr.Textbox(
                            label="Target audience",
                            placeholder=(
                                "young professionals who love coffee but hate waiting in line"
                            ),
                        )

                        # Campaign goal: preset dropdown + optional custom
                        goal_preset = gr.Dropdown(
                            label="Campaign goal",
                            choices=[
                                "Increase brand awareness",
                                "Lead generation",
                                "Drive website traffic",
                                "Promote in-store visits",
                                "Boost engagement",
                                "Announce a new product",
                            ],
                            value="Increase brand awareness",
                        )
                        goal_custom = gr.Textbox(
                            label="Custom goal (optional)",
                            placeholder="e.g. drive in-store visits this weekend",
                            lines=2,
                        )

                        platform_name = gr.Dropdown(
                            label="Platform",
                            choices=["Instagram", "Facebook", "LinkedIn", "Twitter"],
                            value="Instagram",
                        )
                        tone = gr.Dropdown(
                            label="Tone",
                            choices=[
                                "friendly",
                                "professional",
                                "energetic",
                                "storytelling",
                            ],
                            value="friendly",
                        )
                        cta_style = gr.Dropdown(
                            label="CTA style",
                            choices=["soft", "medium", "hard"],
                            value="soft",
                        )

                        extra_context = gr.Textbox(
                            label="Extra context (optional)",
                            placeholder="Mention that we have comfy seating and free Wi-Fi.",
                            lines=3,
                        )

                        generate_copy_btn = gr.Button(
                            "✨ Generate First Draft (and start chat)"
                        )

                    # RIGHT COLUMN: Chat + Feedback
                    with gr.Column(scale=2):
                        gr.Markdown("### Chat with your copywriter")

                        chatbox = gr.Chatbot(
                            label="Copy Chat (context-aware)",
                            height=320,
                        )
                        user_msg = gr.Textbox(
                            label="Your message",
                            placeholder=(
                                "Examples:\n"
                                "- 'Write a first post for this campaign.'\n"
                                "- 'Shorten this and keep the main message.'\n"
                                "- 'Adapt this for LinkedIn, more professional.'"
                            ),
                            lines=3,
                        )
                        with gr.Row():
                            send_btn = gr.Button("Send")
                            clear_btn = gr.Button("Clear Chat")

                        gr.Markdown("#### Feedback on the last reply")
                        fb_rating = gr.Radio(
                            label="How was the last AI reply?",
                            choices=["👍 Helpful", "👌 Okay", "👎 Needs improvement"],
                            value="👍 Helpful",
                        )
                        fb_text = gr.Textbox(
                            label="Feedback (optional)",
                            placeholder="What worked well? What should be improved?",
                            lines=3,
                        )
                        fb_submit = gr.Button("Submit feedback for last reply")
                        fb_status = gr.Markdown("")

                # Wire first-draft generator (seeds chat only)
                generate_copy_btn.click(
                    fn=_generate_first_copy_ui,
                    inputs=[
                        brand,
                        product,
                        audience,
                        goal_preset,
                        goal_custom,
                        platform_name,
                        tone,
                        cta_style,
                        extra_context,
                    ],
                    outputs=[chatbox],
                )

                # Wire chat send button
                send_btn.click(
                    fn=_chat_copy_ui,
                    inputs=[
                        chatbox,
                        user_msg,
                        brand,
                        product,
                        audience,
                        goal_preset,
                        goal_custom,
                        platform_name,
                        tone,
                        cta_style,
                        extra_context,
                    ],
                    outputs=[chatbox, user_msg],
                )

                # Wire chat clear button
                clear_btn.click(
                    fn=_clear_chat,
                    inputs=None,
                    outputs=[chatbox],
                )

                # Wire feedback button (linked to last assistant reply)
                fb_submit.click(
                    fn=_submit_feedback_for_last_reply,
                    inputs=[
                        chatbox,
                        fb_rating,
                        fb_text,
                        brand,
                        platform_name,
                        goal_preset,
                        goal_custom,
                    ],
                    outputs=[fb_status],
                )

            # --- Tab 2: Video Script Generator (unchanged logic) ---
            with gr.Tab("Video Script Generator"):
                with gr.Row():
                    with gr.Column():
                        v_brand = gr.Textbox(
                            label="Brand / Company",
                            placeholder="Brew Bliss Café",
                        )
                        v_product = gr.Textbox(
                            label="Product",
                            placeholder="signature cold brew",
                        )
                        v_audience = gr.Textbox(
                            label="Target audience",
                            placeholder=(
                                "young professionals who love coffee but hate waiting in line"
                            ),
                        )
                        v_goal = gr.Textbox(
                            label="Campaign goal",
                            placeholder="drive in-store visits this weekend",
                        )

                        blueprint_name = gr.Dropdown(
                            label="Blueprint",
                            choices=["short_ad", "ugc_review", "how_to"],
                            value="short_ad",
                        )
                        duration_sec = gr.Slider(
                            label="Video duration (seconds)",
                            minimum=5,
                            maximum=60,
                            step=1,
                            value=20,
                        )
                        platform_name_v = gr.Textbox(
                            label="Platform label (for prompt)",
                            value="Instagram Reels",
                        )
                        style = gr.Textbox(
                            label="Style",
                            value="warm and energetic",
                        )
                        extra_context_v = gr.Textbox(
                            label="Extra context (optional)",
                            placeholder=(
                                "Focus on escaping the grind and enjoying a chilled moment."
                            ),
                            lines=3,
                        )
                        debug_first = gr.Checkbox(
                            label="Print raw first beat to server logs (debug)",
                            value=False,
                        )

                        generate_video_btn = gr.Button("Generate Video Script")

                    with gr.Column():
                        storyboard = gr.Textbox(
                            label="Storyboard (per beat)",
                            lines=18,
                        )
                        warnings_box = gr.Textbox(
                            label="Warnings",
                            lines=6,
                        )
                        script_json = gr.JSON(
                            label="Full script JSON (for download/integration)",
                        )

                generate_video_btn.click(
                    fn=_generate_video_ui,
                    inputs=[
                        v_brand,
                        v_product,
                        v_audience,
                        v_goal,
                        blueprint_name,
                        duration_sec,
                        platform_name_v,
                        style,
                        extra_context_v,
                        debug_first,
                    ],
                    outputs=[storyboard, script_json, warnings_box],
                )

    return demo
