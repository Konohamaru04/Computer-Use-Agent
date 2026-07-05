from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowInfo:
    title: str
    active: bool = False


def list_windows() -> list[WindowInfo]:
    try:
        import pywinctl
    except Exception:
        return []

    windows: list[WindowInfo] = []
    for window in pywinctl.getAllWindows():
        title = getattr(window, "title", "") or ""
        if title.strip():
            windows.append(WindowInfo(title=title, active=bool(getattr(window, "isActive", False))))
    return windows
