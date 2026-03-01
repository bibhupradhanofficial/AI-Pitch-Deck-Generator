from __future__ import annotations

import json
import asyncio
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from agents import image_agent, pitch_agent, video_agent
from models.schemas import HealthResponse, PitchRequest
from services import chart_service, gcs_service, pptx_service

from dotenv import load_dotenv

load_dotenv()



app = FastAPI(title="pitch-deck-ai", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    async def _ensure() -> None:
        try:
            await asyncio.to_thread(gcs_service.ensure_bucket_exists)
        except RuntimeError:
            return
        except Exception:
            return

    asyncio.create_task(_ensure())


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse()


def _format_sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.post("/generate")
async def generate(req: PitchRequest) -> StreamingResponse:
    session_id = uuid.uuid4().hex

    async def _event_stream():
        yield _format_sse({"type": "status", "message": "🧠 Generating pitch content with Gemini..."})
        pitch = await pitch_agent.generate_pitch_content(
            idea=req.idea,
            industry=req.industry or "",
            target_market=req.target_market or "",
            tone=req.tone,
        )

        slides_list = pitch.get("slides") if isinstance(pitch, dict) else None
        if not isinstance(slides_list, list):
            slides_list = []

        voiceover_script = pitch.get("voiceover_script") if isinstance(pitch, dict) else None
        if not isinstance(voiceover_script, str):
            voiceover_script = ""

        social_captions_dict = pitch.get("social_captions") if isinstance(pitch, dict) else None
        if not isinstance(social_captions_dict, dict):
            social_captions_dict = {}

        chart_specs = pitch.get("chart_specs") if isinstance(pitch, dict) else None
        if not isinstance(chart_specs, list):
            chart_specs = []

        imagen_prompts = pitch.get("imagen_prompts") if isinstance(pitch, dict) else None
        if not isinstance(imagen_prompts, list):
            imagen_prompts = []

        veo_prompt = pitch.get("veo_prompt") if isinstance(pitch, dict) else None
        if not isinstance(veo_prompt, str):
            veo_prompt = ""

        yield _format_sse({"type": "slides", "data": slides_list})
        yield _format_sse({"type": "voiceover", "data": voiceover_script})
        yield _format_sse({"type": "social", "data": social_captions_dict})

        yield _format_sse({"type": "status", "message": "📊 Generating charts..."})
        try:
            chart_urls_list = await chart_service.generate_charts(chart_specs=chart_specs, session_id=session_id)
        except Exception:
            chart_urls_list = []
        yield _format_sse({"type": "charts", "data": chart_urls_list})

        yield _format_sse({"type": "status", "message": "🎨 Generating product images with Imagen..."})
        try:
            image_urls_list = await image_agent.generate_product_images(prompts=imagen_prompts, session_id=session_id)
        except Exception:
            image_urls_list = []
        yield _format_sse({"type": "images", "data": image_urls_list})

        yield _format_sse({"type": "status", "message": "📄 Building PowerPoint deck..."})
        try:
            pptx_url = await pptx_service.build_pptx(
                slides=slides_list,
                chart_urls=chart_urls_list,
                image_urls=image_urls_list,
                session_id=session_id,
            )
        except Exception:
            pptx_url = None
        yield _format_sse({"type": "pptx", "data": pptx_url})

        yield _format_sse({"type": "status", "message": "🎬 Generating promo video with Veo..."})
        try:
            video_url_or_null = (
                await video_agent.generate_promo_video(veo_prompt=veo_prompt, session_id=session_id)
                if veo_prompt
                else None
            )
        except Exception:
            video_url_or_null = None
        yield _format_sse({"type": "video", "data": video_url_or_null})

        yield _format_sse({"type": "complete", "message": "✅ Pitch deck ready!"})

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
