from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from computeruse.agent.history import HistoryStore
from computeruse.config import ACTIVE_SESSION_PATH, ensure_runtime_dirs
from computeruse.schemas.session import ActiveSession, HistorySessionDetail, HistorySessionSummary, SessionStatus, StepRecord


class SessionManager:
    def __init__(self, path: Path = ACTIVE_SESSION_PATH, history: HistoryStore | None = None) -> None:
        ensure_runtime_dirs()
        self.path = path
        self.history = history or HistoryStore()

    def start(self, task: str, selected_model: str) -> ActiveSession:
        now = _utc_now()
        session = ActiveSession(
            session_id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            status="running",
            task=task,
            selected_model=selected_model,
        )
        self.save(session)
        return session

    def load(self) -> ActiveSession | None:
        if not self.path.exists():
            return None
        return ActiveSession.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, session: ActiveSession) -> ActiveSession:
        session.updated_at = _utc_now()
        session.recent_steps = session.recent_steps[-10:]
        payload = json.dumps(session.model_dump(mode="json"), indent=2)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(payload + "\n", encoding="utf-8")
        tmp_path.replace(self.path)
        self.history.upsert_session(session)
        return session

    def append_step(
        self,
        session: ActiveSession,
        *,
        step_index: int,
        action: str,
        thought: str,
        confidence: float,
        result: str,
        ok: bool,
        screenshot_path: str | None,
        timings: dict[str, Any],
        last_action: dict[str, Any] | None,
    ) -> ActiveSession:
        session.step_index = step_index
        session.last_action = last_action
        session.last_screenshot_path = screenshot_path
        session.last_observation_summary = result
        step = StepRecord(
            step_index=step_index,
            action=action,
            thought=thought,
            confidence=confidence,
            result=result,
            ok=ok,
            screenshot_path=screenshot_path,
            timings=timings,
        )
        session.recent_steps.append(step)
        saved = self.save(session)
        self.history.upsert_step(session_id=saved.session_id, step=step, action_payload=last_action)
        return saved

    def mark_status(
        self,
        session: ActiveSession,
        status: SessionStatus,
        *,
        summary: str,
        last_action: dict[str, Any] | None = None,
    ) -> ActiveSession:
        session.status = status
        session.last_observation_summary = summary
        if last_action is not None:
            session.last_action = last_action
        saved = self.save(session)
        self.history.upsert_session(saved, summary=summary)
        return saved

    def list_history(self, limit: int = 50) -> list[HistorySessionSummary]:
        return self.history.list_sessions(limit=limit)

    def get_history_session(self, session_id: str) -> HistorySessionDetail | None:
        return self.history.get_session(session_id)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
