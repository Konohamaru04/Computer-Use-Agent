from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SESSIONS_DIR = PROJECT_ROOT / "sessions"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"
ACTIVE_SESSION_PATH = SESSIONS_DIR / "active_session.json"
HISTORY_DB_PATH = DATA_DIR / "computeruse.sqlite3"
CURRENT_SCREENSHOT_PATH = SCREENSHOTS_DIR / "current.png"
PLANNER_SCREENSHOT_PATH = SCREENSHOTS_DIR / "planner.png"
DEBUG_TIMING_LOG_PATH = LOGS_DIR / "debug_timing.jsonl"

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

DEFAULT_MAX_STEPS = 50
DEFAULT_ACTION_DELAY_MS = 1200
DEFAULT_MOVE_SETTLE_MS = 250
DEFAULT_REPAIR_ATTEMPTS = 1
DEFAULT_SCREENSHOT_FORMAT = "PNG"


def ensure_runtime_dirs() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
