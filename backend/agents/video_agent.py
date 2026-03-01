from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from services.gcs_service import GcsService, GcsServiceConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VideoAgentConfig:
    use_mock: bool = True


class VideoAgent:
    def __init__(self, config: VideoAgentConfig | None = None) -> None:
        self._config = config or VideoAgentConfig()

    def generate_video_clips(self, prompt: str, count: int = 1) -> list[str]:
        if self._config.use_mock:
            safe = "".join(ch for ch in prompt.strip()[:24] if ch.isalnum() or ch in (" ", "-")).strip()
            label = safe.replace(" ", "-") or "mock"
            return [f"mock://video/{label}/{i+1}" for i in range(count)]
        return []


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


def _operation_is_done(operation: object) -> bool:
    done = getattr(operation, "done", None)
    if isinstance(done, bool):
        return done
    if isinstance(operation, dict):
        return bool(operation.get("done"))
    return False


def _extract_first_video_file(operation: object) -> object:
    resp = getattr(operation, "response", None)
    if resp is None and isinstance(operation, dict):
        resp = operation.get("response")
    if resp is None:
        raise ValueError("Veo operation missing response")

    generated_videos = getattr(resp, "generated_videos", None)
    if generated_videos is None and isinstance(resp, dict):
        generated_videos = resp.get("generated_videos") or resp.get("generatedVideos")
    if not isinstance(generated_videos, list) or not generated_videos:
        raise ValueError("Veo response missing generated_videos")

    first = generated_videos[0]
    video = getattr(first, "video", None)
    if video is None and isinstance(first, dict):
        video = first.get("video")
    if video is None:
        raise ValueError("Veo generated video missing video file reference")
    return video


def _extract_video_bytes(video_file: object) -> bytes | None:
    for attr in ("video_bytes", "bytes", "data"):
        b = getattr(video_file, attr, None)
        if isinstance(b, (bytes, bytearray)):
            return bytes(b)
    if isinstance(video_file, dict):
        for key in ("video_bytes", "videoBytes", "bytes", "data"):
            b = video_file.get(key)
            if isinstance(b, (bytes, bytearray)):
                return bytes(b)
    return None


def _get_operation_name(operation: object) -> str | None:
    name = getattr(operation, "name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    if isinstance(operation, dict):
        name = operation.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _refresh_videos_operation(client: genai.Client, operation: object) -> object:
    try:
        return client.operations.get(operation)
    except Exception:
        name = _get_operation_name(operation)
        if not name:
            raise
        op = types.GenerateVideosOperation(name=name)
        return client.operations.get(op)


async def generate_promo_video(veo_prompt: str, session_id: str) -> str | None:
    enhanced_prompt = (
        "Cinematic, professional startup promotional video, 5 seconds, modern tech aesthetic, smooth motion: "
        + (veo_prompt or "")
    )

    try:
        client = _build_genai_client()

        config = types.GenerateVideosConfig(
            duration_seconds=5,
            aspect_ratio="16:9",
            number_of_videos=1,
        )

        if getattr(client, "videos", None) is not None and hasattr(client.videos, "generate"):
            operation: Any = await asyncio.to_thread(
                client.videos.generate,
                model="veo-2.0-generate-001",
                prompt=enhanced_prompt,
                config=config,
            )
        else:
            operation = await asyncio.to_thread(
                client.models.generate_videos,
                model="veo-2.0-generate-001",
                prompt=enhanced_prompt,
                config=config,
            )

        for _ in range(10):
            if _operation_is_done(operation):
                break
            await asyncio.sleep(5)
            operation = await asyncio.to_thread(_refresh_videos_operation, client, operation)

        if not _operation_is_done(operation):
            logger.error("Veo video generation timed out (session_id=%s)", session_id)
            return None

        video_file = _extract_first_video_file(operation)

        try:
            await asyncio.to_thread(client.files.download, file=video_file)
        except TypeError:
            await asyncio.to_thread(client.files.download, video_file)

        tmp_dir = Path("/tmp")
        if not tmp_dir.exists():
            import tempfile

            tmp_dir = Path(tempfile.gettempdir())
        tmp_dir.mkdir(parents=True, exist_ok=True)
        local_path = tmp_dir / f"{session_id}_promo.mp4"

        video_bytes = _extract_video_bytes(video_file)
        if video_bytes is not None:
            await asyncio.to_thread(local_path.write_bytes, video_bytes)
        elif hasattr(video_file, "save"):
            await asyncio.to_thread(video_file.save, str(local_path))
        else:
            raise ValueError("Unable to persist downloaded Veo video to disk")

        gcs_bucket = os.getenv("GCS_BUCKET_NAME")
        gcs_prefix = os.getenv("GCS_PREFIX", "pitch-decks")
        gcs_service = GcsService(GcsServiceConfig(bucket_name=gcs_bucket, prefix=gcs_prefix))

        upload = await asyncio.to_thread(gcs_service.upload_file, local_path)
        url = upload.get("url") if isinstance(upload, dict) else None
        return url
    except Exception:
        logger.exception("Veo promo video generation failed (session_id=%s)", session_id)
        return None
