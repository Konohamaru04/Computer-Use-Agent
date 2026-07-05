from __future__ import annotations

import base64
import io
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from computeruse.agent.model_selector import ModelInfo, rank_models
from computeruse.agent.prompts import PLANNER_SYSTEM_PROMPT
from computeruse.config import OLLAMA_BASE_URL


@dataclass(frozen=True)
class PlannerResponse:
    raw: str
    encode_ms: int
    ollama_ms: int


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, timeout_s: float = 180.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout_s))

    async def close(self) -> None:
        await self._client.aclose()

    async def list_models(self) -> list[ModelInfo]:
        response = await self._client.get(f"{self.base_url}/api/tags")
        response.raise_for_status()
        data = response.json()
        return rank_models(data.get("models", []))

    async def plan_action(
        self,
        model: str,
        user_prompt: str,
        screenshot_path: Path,
        repair_context: str | None = None,
    ) -> PlannerResponse:
        encode_start = time.perf_counter()
        image_b64 = encode_png_base64(screenshot_path)
        encode_ms = int((time.perf_counter() - encode_start) * 1000)

        content = user_prompt
        if repair_context:
            content = (
                f"{user_prompt}\n\nThe previous response was invalid. "
                f"Repair it by returning only one valid JSON action.\n{repair_context}"
            )

        payload: dict[str, Any] = {
            "model": model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": content, "images": [image_b64]},
            ],
        }

        request_start = time.perf_counter()
        response = await self._client.post(f"{self.base_url}/api/chat", json=payload)
        ollama_ms = int((time.perf_counter() - request_start) * 1000)
        response.raise_for_status()
        data = response.json()
        raw = data.get("message", {}).get("content") or data.get("response") or ""
        return PlannerResponse(raw=str(raw), encode_ms=encode_ms, ollama_ms=ollama_ms)


def encode_png_base64(path: Path, max_width: int | None = None) -> str:
    if max_width is None:
        return base64.b64encode(path.read_bytes()).decode("ascii")

    with Image.open(path) as image:
        if image.width <= max_width:
            return base64.b64encode(path.read_bytes()).decode("ascii")

        ratio = max_width / image.width
        resized_size: tuple[int, int] = (max_width, int(image.height * ratio))
        resized = image.resize(resized_size, Image.Resampling.LANCZOS)  # type: ignore[reportUnknownMemberType]
        output = io.BytesIO()
        resized.save(output, format="PNG")
        return base64.b64encode(output.getvalue()).decode("ascii")
