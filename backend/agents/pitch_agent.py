from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from models.schemas import PitchDeckRequest, SlideSpec

from google import genai
from google.genai import types


@dataclass(frozen=True)
class PitchAgentConfig:
    use_mock: bool = True


class PitchAgent:
    def __init__(self, config: PitchAgentConfig | None = None) -> None:
        self._config = config or PitchAgentConfig()

    def generate_slides(self, req: PitchDeckRequest) -> list[SlideSpec]:
        startup = (req.startup_name or "Your Startup").strip()
        now = datetime.utcnow().strftime("%Y-%m-%d")
        prompt = req.prompt.strip()

        base = [
            SlideSpec(
                title=f"{startup}",
                bullets=[
                    f"Pitch deck generated {now}",
                    f"Tone: {req.tone}",
                    f"Audience: {req.target_audience}",
                ],
                notes=prompt,
            ),
            SlideSpec(
                title="Problem",
                bullets=[
                    "A high-impact pain point exists in the market",
                    "Current solutions are fragmented or expensive",
                    "Users waste time and budget on manual work",
                ],
            ),
            SlideSpec(
                title="Solution",
                bullets=[
                    "A multimodal agent generates investor-ready pitch assets",
                    "One prompt produces slides, charts, and media outputs",
                    "Fast iteration with consistent narrative quality",
                ],
            ),
            SlideSpec(
                title="Market",
                bullets=[
                    "Bottom-up wedge in a clear ICP",
                    "Expand to adjacent segments with the same workflow",
                    "Large market driven by AI adoption",
                ],
                chart={
                    "type": "bar",
                    "title": "Market Growth (Illustrative)",
                    "labels": ["2026", "2027", "2028", "2029", "2030"],
                    "values": [1.0, 1.8, 3.0, 4.8, 7.5],
                },
            ),
            SlideSpec(
                title="Traction",
                bullets=[
                    "Pilot customers and early design partners",
                    "Clear funnel from prompt to deliverables",
                    "Measurable time-to-deck reduction",
                ],
            ),
            SlideSpec(
                title="Business Model",
                bullets=[
                    "SaaS subscriptions with usage-based add-ons",
                    "Agency/enterprise plans for higher volume",
                    "Template marketplace for verticals",
                ],
            ),
            SlideSpec(
                title="Go-To-Market",
                bullets=[
                    "Founder-led sales to validate early segments",
                    "Content-driven inbound via pitch examples",
                    "Partnerships with accelerators and VC platforms",
                ],
            ),
            SlideSpec(
                title="Team",
                bullets=[
                    "AI/ML engineering + product design",
                    "Experience shipping production ML systems",
                    "Advisors across fundraising and branding",
                ],
            ),
            SlideSpec(
                title="Ask",
                bullets=[
                    "Funding to scale product and GTM",
                    "Hiring: ML, full-stack, design",
                    "Introductions to design partners",
                ],
            ),
        ]

        if self._config.use_mock:
            return base

        return base


def _build_genai_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)

    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    if project and location:
        return genai.Client(vertexai=True, project=project, location=location)

    if project:
        return genai.Client(vertexai=True, project=project)

    return genai.Client()


def _clean_json_text(raw: str) -> str:
    s = raw.strip()
    if not s:
        return s

    if s.startswith("```"):
        lines = [ln for ln in s.splitlines() if not ln.strip().startswith("```")]
        s = "\n".join(lines).strip()

    return s


def _parse_json_obj(raw: str) -> dict[str, Any]:
    s = _clean_json_text(raw)
    if not s:
        raise ValueError("Empty response")

    try:
        val = json.loads(s)
        if isinstance(val, dict):
            return val
        raise ValueError("Response JSON is not an object")
    except json.JSONDecodeError:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            val = json.loads(s[start : end + 1])
            if isinstance(val, dict):
                return val
        raise


def _mock_pitch_content(idea: str, industry: str, target_market: str, tone: str) -> dict[str, Any]:
    ind = (industry or "General").strip()
    tm = (target_market or "Mixed").strip()
    t = (tone or "professional").strip()
    one_liner = (idea or "A startup").strip()

    slides: list[dict[str, Any]] = [
        {
            "title": "Problem",
            "body": [
                "High-value teams lose time to manual, fragmented workflows",
                "Decision-making is slowed by missing context and inconsistent data",
                "Legacy tools are expensive and hard to operationalize",
            ],
            "speaker_notes": f"Open with a clear pain point tied to {ind} and the buyer. Keep it crisp and measurable.",
        },
        {
            "title": "Solution",
            "body": [
                f"{one_liner}",
                "An AI workflow that turns messy inputs into clear outputs",
                "Fast iteration with consistent narrative and artifacts",
            ],
            "speaker_notes": f"Explain the solution in one sentence, then list 2-3 outcomes. Tone: {t}.",
        },
        {
            "title": "Market Size",
            "body": [
                "Start with a focused ICP wedge",
                "Expand to adjacent segments with the same workflow",
                "Large and growing spend driven by AI adoption",
            ],
            "speaker_notes": f"Anchor the market in {tm}. Use a simple TAM/SAM/SOM story without overclaiming.",
        },
        {
            "title": "Product Demo",
            "body": [
                "Input: a single prompt + optional context",
                "Output: slides, charts, scripts, and social copy",
                "Export: investor-ready deck in minutes",
            ],
            "speaker_notes": "Walk through the before/after. Show speed, quality, and consistency.",
        },
        {
            "title": "Business Model",
            "body": [
                "Subscription tiers based on seats and usage",
                "Add-ons: brand templates, team workflows, compliance",
                "Services: onboarding and custom narrative packs",
            ],
            "speaker_notes": "Keep pricing simple and believable. Emphasize expansion and retention levers.",
        },
        {
            "title": "Traction",
            "body": [
                "Design partners validating workflow fit",
                "Early pilots measuring time-to-deck reduction",
                "Strong engagement signals from repeat usage",
            ],
            "speaker_notes": "If traction is unknown, state what you will measure and why it proves demand.",
        },
        {
            "title": "Team",
            "body": [
                "AI + product leadership with shipping experience",
                "Deep domain insight in the target workflow",
                "Advisors in fundraising, design, and GTM",
            ],
            "speaker_notes": "Highlight why this team can execute fast. Keep it credible and specific.",
        },
        {
            "title": "Call to Action",
            "body": [
                "Raising to accelerate product and GTM",
                "Seeking intros to design partners and early adopters",
                "Next step: live demo + pilot proposal",
            ],
            "speaker_notes": "End with a clear ask and a concrete next step.",
        },
    ]

    chart_specs = [
        {
            "chart_type": "bar",
            "title": "Time Saved per Deck (Illustrative)",
            "labels": ["Manual", "With AI"],
            "values": [10, 1],
        },
        {
            "chart_type": "line",
            "title": "Adoption Growth (Illustrative)",
            "labels": ["Month 1", "Month 2", "Month 3", "Month 4", "Month 5"],
            "values": [5, 14, 28, 46, 70],
        },
    ]

    imagen_prompts = [
        f"Modern product UI mockup for a {ind} startup, dark theme glassmorphism, dashboard with charts, purple blue gradient accents, high detail, clean typography",
        f"Photorealistic scene of a team reviewing an investor pitch deck on a large screen, {tm} context, cinematic lighting, subtle purple blue gradient highlights, high detail",
    ]

    voiceover_script = (
        f"In {ind}, teams still spend hours turning raw ideas into investor-ready decks. "
        f"{one_liner} In under a minute, it generates a coherent story: slides, charts, a voiceover script, and social captions. "
        "Founders iterate faster, stay consistent, and focus on building instead of formatting. "
        "We’re starting with a focused wedge, proving time savings and engagement, then expanding across adjacent workflows."
    )

    veo_prompt = (
        f"A sleek 5-second promo video for an AI pitch deck generator in {ind}. "
        "Dark futuristic visuals, glass UI overlays, purple-blue gradient accents, quick cuts of decks, charts, and product mockups."
    )

    social_captions = {
        "twitter": "Turn your startup idea into an investor-ready pitch deck in 60 seconds. Slides, charts, voiceover + social copy—done. #startups #pitchdeck #AI",
        "linkedin": "Founders shouldn’t spend days formatting decks. Our AI turns a single idea into an investor-ready pitch narrative with slides, charts, and supporting assets in minutes. If you’re raising soon, let’s connect for a demo.",
        "instagram": "Idea → pitch deck in 60 seconds. Slides, charts, scripts, and captions—all in one flow. Built for founders in motion. #startup #founderlife #pitchdeck #ai",
    }

    return {
        "slides": slides,
        "chart_specs": chart_specs,
        "imagen_prompts": imagen_prompts,
        "voiceover_script": voiceover_script,
        "veo_prompt": veo_prompt,
        "social_captions": social_captions,
    }


async def generate_pitch_content(
    idea: str,
    industry: str,
    target_market: str,
    tone: str,
) -> dict[str, Any]:
    model = (os.getenv("GEMINI_MODEL") or "gemini-2.0-flash").strip()
    system_instruction = (
        "You are a world-class startup pitch deck consultant and creative director. "
        "When given a startup idea, you generate a complete, investor-ready pitch deck package. "
        "Always respond in valid JSON only."
    )

    base_prompt = f"""
Create a complete startup pitch deck package for this idea: "{idea}"
Industry: {industry or "detect from idea"}
Target Market: {target_market or "detect from idea"}
Tone: {tone}

Return a JSON object with EXACTLY these keys:
{{
  "slides": [
    {{
      "title": "slide title",
      "body": ["bullet 1", "bullet 2", "bullet 3"],
      "speaker_notes": "what to say during this slide"
    }}
  ],
  "chart_specs": [
    {{
      "chart_type": "bar|pie|line",
      "title": "chart title",
      "labels": ["label1", "label2"],
      "values": [10, 20]
    }}
  ],
  "imagen_prompts": ["detailed image prompt 1 for product mockup", "detailed image prompt 2"],
  "voiceover_script": "Full 60-second voiceover script for the pitch",
  "veo_prompt": "A short 5-second cinematic promotional video prompt for this startup",
  "social_captions": {{
    "twitter": "tweet under 280 chars with hashtags",
    "linkedin": "professional LinkedIn post 150 words",
    "instagram": "engaging instagram caption with emojis and hashtags"
  }}
}}

Generate exactly 8 slides: Problem, Solution, Market Size, Product Demo, Business Model, Traction, Team, Call to Action.
Generate exactly 2 chart specs relevant to market size or business model.
Generate exactly 2 imagen_prompts for product mockup visuals.
""".strip()

    try:
        client = _build_genai_client()
    except Exception:
        return _mock_pitch_content(idea=idea, industry=industry, target_market=target_market, tone=tone)

    def _stream_generate(prompt: str) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
        )
        contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
        chunks: list[str] = []
        for event in client.models.generate_content_stream(model=model, contents=contents, config=config):
            text = getattr(event, "text", None)
            if text:
                chunks.append(text)
        return "".join(chunks)

    try:
        raw = await asyncio.to_thread(_stream_generate, base_prompt)
        return _parse_json_obj(raw)
    except Exception:
        retry_prompt = base_prompt + "\n\nReturn only raw JSON, no markdown, no code fences, no extra text."
        try:
            raw = await asyncio.to_thread(_stream_generate, retry_prompt)
            return _parse_json_obj(raw)
        except Exception as e:
            return {"error": "Failed to generate valid JSON pitch content", "details": str(e)}
