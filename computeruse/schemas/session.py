from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SessionStatus = Literal["running", "done", "failed", "cancelled"]


class StepRecord(BaseModel):
    step_index: int
    action: str
    thought: str = ""
    confidence: float = 0.0
    result: str
    ok: bool
    screenshot_path: str | None = None
    timings: dict[str, Any] = Field(default_factory=dict)


def _empty_steps() -> list[StepRecord]:
    return []


class ActiveSession(BaseModel):
    session_id: str
    created_at: str
    updated_at: str
    status: SessionStatus
    task: str
    selected_model: str
    step_index: int = 0
    last_screenshot_path: str | None = None
    last_action: dict[str, Any] | None = None
    last_observation_summary: str = ""
    recent_steps: list[StepRecord] = Field(default_factory=_empty_steps)


class HistorySessionSummary(BaseModel):
    session_id: str
    created_at: str
    updated_at: str
    status: SessionStatus
    task: str
    selected_model: str
    step_index: int = 0
    summary: str = ""
    last_screenshot_path: str | None = None


class HistorySessionDetail(HistorySessionSummary):
    last_action: dict[str, Any] | None = None
    last_observation_summary: str = ""
    steps: list[StepRecord] = Field(default_factory=_empty_steps)
