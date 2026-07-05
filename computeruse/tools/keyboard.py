from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class KeyboardResult:
    ok: bool
    message: str
    execute_ms: int


class _KeyboardGui(Protocol):
    PAUSE: float

    def write(self, message: str, interval: float = 0) -> None: ...

    def press(self, key: str) -> None: ...

    def hotkey(self, *args: str) -> None: ...


def _pyautogui() -> _KeyboardGui:
    import pyautogui

    pyautogui.PAUSE = 0
    return pyautogui  # type: ignore[reportReturnType]


def type_text(text: str) -> KeyboardResult:
    return _run_keyboard(lambda gui: gui.write(text, interval=0), f"typed {len(text)} characters")


def press(key: str) -> KeyboardResult:
    return _run_keyboard(lambda gui: gui.press(key), f"pressed {key}")


def hotkey(keys: list[str]) -> KeyboardResult:
    return _run_keyboard(lambda gui: gui.hotkey(*keys), f"pressed {'+'.join(keys)}")


def _run_keyboard(operation: Callable[[_KeyboardGui], Any], success_message: str) -> KeyboardResult:
    start = time.perf_counter()
    try:
        operation(_pyautogui())
        return KeyboardResult(True, success_message, int((time.perf_counter() - start) * 1000))
    except Exception as exc:
        return KeyboardResult(False, f"keyboard action failed: {exc}", int((time.perf_counter() - start) * 1000))
