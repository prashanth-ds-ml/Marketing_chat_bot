# core_logic/video_schema.py

from typing import List, Optional
from pydantic import BaseModel, Field


class VideoBeat(BaseModel):
    """Single beat in the short-form video script."""
    beat_index: int = Field(
        ...,
        description="Zero-based index of this beat in the sequence.",
    )
    title: str = Field(
        ...,
        description="Short title / label for this beat (e.g., 'Hook', 'Product Close-up').",
    )
    goal: str = Field(
        ...,
        description="What this beat is trying to achieve (hook, social proof, CTA, etc.).",
    )
    t_start: float = Field(
        ...,
        description="Approximate start time in seconds from the beginning of the video.",
    )
    t_end: float = Field(
        ...,
        description="Approximate end time in seconds from the beginning of the video.",
    )
    voiceover: str = Field(
        ...,
        description="Suggested voiceover line(s) for this beat.",
    )
    on_screen: str = Field(
        ...,
        description="Short on-screen text / caption for this beat.",
    )
    shots: List[str] = Field(
        default_factory=list,
        description="List of camera shots / visuals in this beat.",
    )
    broll: List[str] = Field(
        default_factory=list,
        description="Optional B-roll ideas for this beat.",
    )
    captions: List[str] = Field(
        default_factory=list,
        description="Suggested caption lines or overlays.",
    )


class VideoPlan(BaseModel):
    """High-level plan for the entire video."""
    blueprint_name: str = Field(
        ...,
        description="Name of the blueprint used (e.g., 'short_ad', 'ugc_review', 'how_to').",
    )
    duration_sec: int = Field(
        ...,
        description="Total target duration of the video in seconds.",
    )
    platform_name: str = Field(
        ...,
        description="Target platform label (e.g., 'Instagram Reels', 'YouTube Shorts').",
    )
    style: str = Field(
        ...,
        description="Overall style (e.g., 'warm and energetic').",
    )
    beats: List[VideoBeat] = Field(
        default_factory=list,
        description="List of beats that make up this video.",
    )


class VideoScriptResponse(BaseModel):
    """
    Full structured response used by the app and UI.
    """
    plan: VideoPlan = Field(
        ...,
        description="High-level plan metadata and beat list.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Any warnings about parsing, timing, or beat structure.",
    )

    @property
    def beats(self) -> List[VideoBeat]:
        """
        Backwards-compatible alias so older code can still do resp.beats.
        Internally, beats live on resp.plan.beats.
        """
        return self.plan.beats