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

    def moveTo(self, *, x: int, y: int, duration: float = 0) -> None: ...

    def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> None: ...

    def mouseDown(self, *, x: int | None = None, y: int | None = None, button: str = "left") -> None: ...

    def mouseUp(self, *, x: int | None = None, y: int | None = None, button: str = "left") -> None: ...


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


def scroll(clicks: int, x: int | None = None, y: int | None = None) -> MouseResult:
    target = f" at ({x}, {y})" if x is not None and y is not None else ""
    direction = "up" if clicks > 0 else "down"
    return _run_mouse(lambda gui: gui.scroll(clicks, x=x, y=y), f"scrolled {direction} {abs(clicks)} clicks{target}")


def drag(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 500) -> MouseResult:
    duration_s = max(0, duration_ms) / 1000

    def operation(gui: _MouseGui) -> None:
        pressed = False
        gui.moveTo(x=start_x, y=start_y)
        gui.mouseDown(x=start_x, y=start_y, button="left")
        pressed = True
        try:
            gui.moveTo(x=end_x, y=end_y, duration=duration_s)
        finally:
            if pressed:
                gui.mouseUp(x=end_x, y=end_y, button="left")

    return _run_mouse(
        operation,
        f"dragged from ({start_x}, {start_y}) to ({end_x}, {end_y}) over {duration_ms} ms",
    )


def _run_mouse(operation: Callable[[_MouseGui], Any], success_message: str) -> MouseResult:
    start = time.perf_counter()
    try:
        operation(_pyautogui())
        return MouseResult(True, success_message, int((time.perf_counter() - start) * 1000))
    except Exception as exc:
        return MouseResult(False, f"mouse action failed: {exc}", int((time.perf_counter() - start) * 1000))
