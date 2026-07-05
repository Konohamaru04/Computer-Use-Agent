from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from computeruse.tools.dpi import ensure_process_dpi_awareness


@dataclass(frozen=True)
class MouseResult:
    ok: bool
    message: str
    execute_ms: int


class _MouseGui(Protocol):
    PAUSE: float

    def click(self, *, x: int, y: int) -> None: ...

    def doubleClick(self, *, x: int, y: int) -> None: ...

    def rightClick(self, *, x: int, y: int) -> None: ...

    def moveTo(self, *, x: int, y: int) -> None: ...


def _pyautogui() -> _MouseGui:
    ensure_process_dpi_awareness()
    import pyautogui

    pyautogui.PAUSE = 0
    return pyautogui  # type: ignore[reportReturnType]


def click(x: int, y: int) -> MouseResult:
    return _run_mouse(lambda gui: gui.click(x=x, y=y), f"clicked ({x}, {y})")


def double_click(x: int, y: int) -> MouseResult:
    return _run_mouse(lambda gui: gui.doubleClick(x=x, y=y), f"double-clicked ({x}, {y})")


def right_click(x: int, y: int) -> MouseResult:
    return _run_mouse(lambda gui: gui.rightClick(x=x, y=y), f"right-clicked ({x}, {y})")


def move(x: int, y: int) -> MouseResult:
    return _run_mouse(lambda gui: gui.moveTo(x=x, y=y), f"moved pointer to ({x}, {y})")


def _run_mouse(operation: Callable[[_MouseGui], Any], success_message: str) -> MouseResult:
    start = time.perf_counter()
    try:
        operation(_pyautogui())
        return MouseResult(True, success_message, int((time.perf_counter() - start) * 1000))
    except Exception as exc:
        return MouseResult(False, f"mouse action failed: {exc}", int((time.perf_counter() - start) * 1000))
