from __future__ import annotations

from dataclasses import dataclass
from typing import Any

VISION_MODEL_HINTS = (
    "llava",
    "bakllava",
    "moondream",
    "minicpm-v",
    "minicpmv",
    "qwen-vl",
    "qwenvl",
    "qwen2-vl",
    "qwen2.5-vl",
    "qwen2.5vl",
    "qwen3-vl",
    "gemma3",
    "gemma-3",
)


@dataclass(frozen=True)
class ModelInfo:
    name: str
    vision: bool
    size: int | None = None
    modified_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "vision": self.vision,
            "size": self.size,
            "modified_at": self.modified_at,
        }


def is_known_vision_model(name: str) -> bool:
    normalized = name.lower().replace("_", "-")
    return any(hint in normalized for hint in VISION_MODEL_HINTS)


def rank_models(models: list[dict[str, Any]]) -> list[ModelInfo]:
    ranked: list[ModelInfo] = []
    for model in models:
        name = str(model.get("name") or model.get("model") or "")
        if not name:
            continue
        size_raw = model.get("size")
        modified_raw = model.get("modified_at")
        ranked.append(
            ModelInfo(
                name=name,
                vision=is_known_vision_model(name),
                size=size_raw if isinstance(size_raw, int) else None,
                modified_at=modified_raw if isinstance(modified_raw, str) else None,
            )
        )
    return sorted(ranked, key=lambda item: (not item.vision, item.name.lower()))
