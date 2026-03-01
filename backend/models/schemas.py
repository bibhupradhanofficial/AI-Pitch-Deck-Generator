from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class SlideSpec(BaseModel):
    title: str
    bullets: list[str] = Field(default_factory=list)
    notes: str | None = None
    chart: dict[str, Any] | None = None


class PitchDeckRequest(BaseModel):
    prompt: str = Field(min_length=1)
    startup_name: str | None = None
    tone: str = "confident"
    target_audience: str = "investors"
    generate_images: bool = True
    generate_video: bool = True


class PitchDeckResponse(BaseModel):
    deck_filename: str
    deck_path: str | None = None
    deck_url: str | None = None
    slides: list[SlideSpec]
    assets: dict[str, Any] = Field(default_factory=dict)


class PitchRequest(BaseModel):
    idea: str
    industry: str | None = None
    target_market: str | None = None
    tone: str = "professional"


class SlideContent(BaseModel):
    title: str
    body: list[str]
    speaker_notes: str


class ChartSpec(BaseModel):
    chart_type: str
    title: str
    labels: list[str]
    values: list[float]


class SocialCaptions(BaseModel):
    twitter: str
    linkedin: str
    instagram: str


class PitchDeckOutput(BaseModel):
    session_id: str
    slides: list[SlideContent]
    chart_specs: list[ChartSpec]
    chart_urls: list[str]
    image_urls: list[str]
    voiceover_script: str
    video_url: str | None = None
    social_captions: SocialCaptions
    pptx_url: str | None = None
    status: str
