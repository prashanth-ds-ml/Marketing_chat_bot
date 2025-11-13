"""
Gradio UI for Marketeer (copy + video script).

This file wires the core logic into a simple web interface
with two tabs:
- Copy Generator
- Video Script Generator
"""

from typing import Any, Dict, List

import gradio as gr

from core_logic.copy_pipeline import CopyRequest, generate_copy
from core_logic.video_pipeline import VideoRequest, generate_video_script


# ----- Backend wrapper functions for Gradio -----


def _generate_copy_ui(
    brand: str,
    product: str,
    audience: str,
    goal: str,
    platform_name: str,
    tone: str,
    cta_style: str,
    extra_context: str,
):
    """
    Wrapper around generate_copy() for Gradio.
    Returns final_text, raw_text, audit_text in that order.
    """
    req = CopyRequest(
        brand=brand or "",
        product=product or "",
        audience=audience or "",
        goal=goal or "",
        platform_name=platform_name or "Instagram",
        tone=tone or "friendly",
        cta_style=cta_style or "soft",
        extra_context=extra_context or "",
    )

    resp = generate_copy(req)

    # Pretty-print audit log
    if resp.audit:
        audit_lines = []
        for item in resp.audit:
            rule = item.get("rule", "unknown")
            audit_lines.append(f"- {rule}: {item}")
        audit_text = "\n".join(audit_lines)
    else:
        audit_text = "No edits were needed. ✅"

    # RETURN IN ORDER: final_copy, raw_output, audit_log
    return resp.final, resp.raw, audit_text


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
):
    """
    Wrapper around generate_video_script() for Gradio.
    Returns storyboard_text, script_json, warnings_text in that order.
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

    # storyboard text (same as before)
    sb_lines = []
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
        sb_lines.append("")

    storyboard_text = "\n".join(sb_lines).strip() or "No beats generated."

    # warnings text
    if resp.warnings:
        warnings_text = "\n".join(f"- {w}" for w in resp.warnings)
    else:
        warnings_text = "No warnings. All beats parsed without fallback. ✅"

    # JSON object
    script_json = {
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

    # RETURN IN ORDER: storyboard, json, warnings
    return storyboard_text, script_json, warnings_text


# ----- Gradio layout -----


def create_interface() -> gr.Blocks:
    """
    Create and return the Gradio Blocks interface.
    """
    with gr.Blocks(title="Marketeer – Copy & Video Script Generator") as demo:
        gr.Markdown(
            """
# Marketeer – Copy & Video Script Generator

Generate platform-aware marketing copy and short-form video scripts,
powered by your patched Gemma-based backend.
"""
        )

        with gr.Tabs():
            # --- Tab 1: Copy Generator ---
            with gr.Tab("Copy Generator"):
                with gr.Row():
                    with gr.Column():
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
                            placeholder="young professionals who love coffee but hate waiting in line",
                        )
                        goal = gr.Textbox(
                            label="Campaign goal",
                            placeholder="drive in-store visits this weekend",
                        )

                        platform_name = gr.Dropdown(
                            label="Platform",
                            choices=["Instagram", "Facebook", "LinkedIn", "Twitter"],
                            value="Instagram",
                        )
                        tone = gr.Dropdown(
                            label="Tone",
                            choices=["friendly", "professional", "energetic", "storytelling"],
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

                        generate_copy_btn = gr.Button("Generate Copy")

                    with gr.Column():
                        final_copy = gr.Textbox(
                            label="Final Copy",
                            lines=10,
                        )
                        audit_log = gr.Textbox(
                            label="Audit Log",
                            lines=8,
                        )
                        raw_output = gr.Textbox(
                            label="Raw Model Output (debug)",
                            lines=8,
                            visible=False,  # flip to True if you want to see raw text
                        )

                # Wire copy button
                generate_copy_btn.click(
                    fn=_generate_copy_ui,
                    inputs=[
                        brand,
                        product,
                        audience,
                        goal,
                        platform_name,
                        tone,
                        cta_style,
                        extra_context,
                    ],
                    outputs=[final_copy, raw_output, audit_log],
                )

            # --- Tab 2: Video Script Generator ---
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
                            placeholder="young professionals who love coffee but hate waiting in line",
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
                            placeholder="Focus on escaping the grind and enjoying a chilled moment.",
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
