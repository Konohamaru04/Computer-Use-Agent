from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScreenshotResult:
    path: Path
    width: int
    height: int
    left: int
    top: int
    monitor_width: int
    monitor_height: int
    capture_ms: int
    encode_ms: int
