from __future__ import annotations

import asyncio
import io
import os
import re
from dataclasses import dataclass
from pathlib import Path

import aiofiles
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

from services.gcs_service import GcsService, GcsServiceConfig


@dataclass(frozen=True)
class ImageAgentConfig:
    use_mock: bool = True


class ImageAgent:
    def __init__(self, config: ImageAgentConfig | None = None) -> None:
        self._config = config or ImageAgentConfig()

    def generate_images(self, prompt: str, count: int = 1) -> list[str]:
        if self._config.use_mock:
            safe = "".join(ch for ch in prompt.strip()[:24] if ch.isalnum() or ch in (" ", "-")).strip()
            label = safe.replace(" ", "-") or "mock"
            return [f"mock://image/{label}/{i+1}" for i in range(count)]
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


def _extract_startup_name(prompt: str) -> str:
    s = (prompt or "").strip()
    if not s:
        return "Startup"

    m = re.search(r"[\"“”']([^\"“”']{2,80})[\"“”']", s)
    if m:
        name = m.group(1).strip()
        if name:
            return name

    prefix = "Professional product mockup, startup pitch deck visual, clean white background, modern design, high quality, 4k: "
    if s.startswith(prefix):
        s = s[len(prefix) :].strip()

    s = re.split(r"[:,-]", s, maxsplit=1)[0].strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^A-Za-z0-9 &+._-]", "", s).strip()
    if not s:
        return "Startup"

    words = s.split(" ")[:6]
    name = " ".join(words).strip()
    return name or "Startup"


def _render_placeholder_png_bytes(startup_name: str) -> bytes:
    w, h = 1024, 576
    img = Image.new("RGB", (w, h))
    start = (0x66, 0x7E, 0xEA)
    end = (0x76, 0x4B, 0xA2)

    px = img.load()
    for y in range(h):
        t = y / (h - 1) if h > 1 else 0.0
        r = int(start[0] * (1 - t) + end[0] * t)
        g = int(start[1] * (1 - t) + end[1] * t)
        b = int(start[2] * (1 - t) + end[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)

    draw = ImageDraw.Draw(img)

    font: ImageFont.ImageFont
    try:
        font = ImageFont.truetype("arial.ttf", size=56)
    except Exception:
        font = ImageFont.load_default()

    text = (startup_name or "Startup").strip()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (w - text_w) / 2
    y = (h - text_h) / 2
    draw.text((x, y), text, fill=(255, 255, 255), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _extract_first_image_bytes(resp: object) -> bytes:
    if resp is None:
        raise ValueError("Empty Imagen response")

    generated_images = getattr(resp, "generated_images", None)
    if generated_images:
        first = generated_images[0]
        image = getattr(first, "image", None)
        if image is not None:
            b = getattr(image, "bytes", None)
            if isinstance(b, (bytes, bytearray)):
                return bytes(b)
            b = getattr(image, "image_bytes", None)
            if isinstance(b, (bytes, bytearray)):
                return bytes(b)

        b = getattr(first, "bytes", None)
        if isinstance(b, (bytes, bytearray)):
            return bytes(b)

    if isinstance(resp, dict):
        gi = resp.get("generated_images") or resp.get("images")
        if isinstance(gi, list) and gi:
            first = gi[0]
            if isinstance(first, dict):
                image = first.get("image") if "image" in first else first
                if isinstance(image, dict):
                    b = image.get("bytes") or image.get("image_bytes")
                    if isinstance(b, (bytes, bytearray)):
                        return bytes(b)

    raise ValueError("Unable to extract image bytes from Imagen response")


def _generate_imagen_image_bytes(client: genai.Client, model: str, prompt: str) -> bytes:
    try:
        config = types.GenerateImagesConfig(number_of_images=1)
        resp = client.models.generate_images(model=model, prompt=prompt, config=config)
    except TypeError:
        resp = client.models.generate_images(model=model, prompt=prompt)
    return _extract_first_image_bytes(resp)


async def generate_product_images(prompts: list[str], session_id: str) -> list[str]:
    imagen_model = (os.getenv("IMAGEN_MODEL") or "imagen-3.0-generate-002").strip()
    prompt_prefix = (
        "Professional product mockup, startup pitch deck visual, clean white background, modern design, high quality, 4k: "
    )

    client = _build_genai_client()

    gcs_bucket = os.getenv("GCS_BUCKET_NAME")
    gcs_prefix = os.getenv("GCS_PREFIX", "pitch-decks")
    gcs_service = GcsService(GcsServiceConfig(bucket_name=gcs_bucket, prefix=gcs_prefix))

    tmp_dir = Path("/tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    urls: list[str] = []
    for i, original_prompt in enumerate(prompts):
        enhanced_prompt = prompt_prefix + (original_prompt or "")
        local_path = tmp_dir / f"{session_id}_image_{i}.png"

        try:
            image_bytes = await asyncio.to_thread(_generate_imagen_image_bytes, client, imagen_model, enhanced_prompt)
        except Exception:
            startup_name = _extract_startup_name(original_prompt or enhanced_prompt)
            image_bytes = await asyncio.to_thread(_render_placeholder_png_bytes, startup_name)

        async with aiofiles.open(local_path, "wb") as f:
            await f.write(image_bytes)

        upload = await asyncio.to_thread(gcs_service.upload_file, local_path)
        url = upload.get("url") if isinstance(upload, dict) else None
        urls.append(url or str(local_path))

    return urls
