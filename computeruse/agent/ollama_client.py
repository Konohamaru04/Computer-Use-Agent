from __future__ import annotations

import base64
import io
import inspect
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, cast

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


PlannerStreamCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


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
        stream_callback: PlannerStreamCallback | None = None,
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
            "stream": True,
            "format": "json",
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": content, "images": [image_b64]},
            ],
        }

        request_start = time.perf_counter()
        raw_parts: list[str] = []
        reasoning_parts: list[str] = []

        async with self._client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    decoded = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(decoded, dict):
                    continue
                data = cast(dict[str, Any], decoded)

                content_delta = _extract_content_delta(data)
                reasoning_delta = _extract_reasoning_delta(data)
                if content_delta:
                    raw_parts.append(content_delta)
                if reasoning_delta:
                    reasoning_parts.append(reasoning_delta)

                if stream_callback and (content_delta or reasoning_delta or data.get("done")):
                    raw = "".join(raw_parts)
                    reasoning = "".join(reasoning_parts).strip()
                    await _maybe_await(
                        stream_callback(
                            {
                                "delta": reasoning_delta or content_delta,
                                "text": reasoning or _display_reasoning(raw),
                                "raw": raw,
                                "done": bool(data.get("done")),
                            }
                        )
                    )
                if data.get("done"):
                    break

        ollama_ms = int((time.perf_counter() - request_start) * 1000)
        raw = "".join(raw_parts)
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


def _extract_content_delta(data: dict[str, Any]) -> str:
    message = data.get("message")
    if isinstance(message, dict):
        message_data = cast(dict[str, Any], message)
        content = message_data.get("content")
        if isinstance(content, str):
            return content
    response = data.get("response")
    return response if isinstance(response, str) else ""


def _extract_reasoning_delta(data: dict[str, Any]) -> str:
    message = data.get("message")
    if isinstance(message, dict):
        message_data = cast(dict[str, Any], message)
        for key in ("thinking", "reasoning", "thought"):
            value = message_data.get(key)
            if isinstance(value, str):
                return value
    for key in ("thinking", "reasoning", "thought"):
        value = data.get(key)
        if isinstance(value, str):
            return value
    return ""


def _display_reasoning(raw: str) -> str:
    stripped = raw.strip()
    if not stripped:
        return ""
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        parsed_data = cast(dict[str, Any], parsed)
        thought = parsed_data.get("thought")
        if isinstance(thought, str):
            return thought.strip()

    match = re.search(r'"thought"\s*:\s*"((?:\\.|[^"\\])*)', stripped, re.DOTALL)
    if not match:
        return stripped

    value = match.group(1)
    try:
        return json.loads(f'"{value}"').strip()
    except json.JSONDecodeError:
        return value.replace(r"\"", '"').replace(r"\\", "\\").strip()


async def _maybe_await(result: Awaitable[None] | None) -> None:
    if inspect.isawaitable(result):
        await result
