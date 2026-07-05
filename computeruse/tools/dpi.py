from __future__ import annotations

import ctypes
import platform
from functools import lru_cache


@lru_cache(maxsize=1)
def ensure_process_dpi_awareness() -> None:
    if platform.system() != "Windows":
        return

    try:
        # Per-monitor DPI awareness keeps MSS screenshot pixels and PyAutoGUI
        # pointer coordinates in the same physical-pixel coordinate space.
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
