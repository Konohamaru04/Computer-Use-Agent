from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, cast

from computeruse.config import HISTORY_DB_PATH, ensure_runtime_dirs
from computeruse.schemas.session import (
    ActiveSession,
    HistorySessionDetail,
    HistorySessionSummary,
    SessionStatus,
    StepRecord,
)


class HistoryStore:
    def __init__(self, path: Path = HISTORY_DB_PATH) -> None:
        ensure_runtime_dirs()
        self.path = path
        self._init_schema()

    def upsert_session(self, session: ActiveSession, *, summary: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    session_id, created_at, updated_at, status, task, selected_model,
                    step_index, last_screenshot_path, last_action_json,
                    last_observation_summary, summary
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    updated_at=excluded.updated_at,
                    status=excluded.status,
                    task=excluded.task,
                    selected_model=excluded.selected_model,
                    step_index=excluded.step_index,
                    last_screenshot_path=excluded.last_screenshot_path,
                    last_action_json=excluded.last_action_json,
                    last_observation_summary=excluded.last_observation_summary,
                    summary=COALESCE(NULLIF(excluded.summary, ''), sessions.summary)
                """,
                (
                    session.session_id,
                    session.created_at,
                    session.updated_at,
                    session.status,
                    session.task,
                    session.selected_model,
                    session.step_index,
                    session.last_screenshot_path,
                    _json_or_none(session.last_action),
                    session.last_observation_summary,
                    summary or "",
                ),
            )

    def upsert_step(
        self,
        *,
        session_id: str,
        step: StepRecord,
        action_payload: dict[str, Any] | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO steps (
                    session_id, step_index, action, thought, confidence, result,
                    ok, screenshot_path, timings_json, action_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, step_index) DO UPDATE SET
                    action=excluded.action,
                    thought=excluded.thought,
                    confidence=excluded.confidence,
                    result=excluded.result,
                    ok=excluded.ok,
                    screenshot_path=excluded.screenshot_path,
                    timings_json=excluded.timings_json,
                    action_json=excluded.action_json
                """,
                (
                    session_id,
                    step.step_index,
                    step.action,
                    step.thought,
                    step.confidence,
                    step.result,
                    1 if step.ok else 0,
                    step.screenshot_path,
                    json.dumps(step.timings, separators=(",", ":"), default=str),
                    _json_or_none(action_payload),
                ),
            )

    def list_sessions(self, limit: int = 50) -> list[HistorySessionSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT session_id, created_at, updated_at, status, task, selected_model,
                       step_index, summary, last_observation_summary, last_screenshot_path
                FROM sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [_summary_from_row(row) for row in rows]

    def get_session(self, session_id: str) -> HistorySessionDetail | None:
        with self._connect() as connection:
            session_row = connection.execute(
                """
                SELECT session_id, created_at, updated_at, status, task, selected_model,
                       step_index, summary, last_observation_summary, last_screenshot_path,
                       last_action_json
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if session_row is None:
                return None

            step_rows = connection.execute(
                """
                SELECT step_index, action, thought, confidence, result, ok,
                       screenshot_path, timings_json
                FROM steps
                WHERE session_id = ?
                ORDER BY step_index ASC
                """,
                (session_id,),
            ).fetchall()

        return _detail_from_rows(session_row, step_rows)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    task TEXT NOT NULL,
                    selected_model TEXT NOT NULL,
                    step_index INTEGER NOT NULL DEFAULT 0,
                    last_screenshot_path TEXT,
                    last_action_json TEXT,
                    last_observation_summary TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    thought TEXT NOT NULL DEFAULT '',
                    confidence REAL NOT NULL DEFAULT 0,
                    result TEXT NOT NULL DEFAULT '',
                    ok INTEGER NOT NULL DEFAULT 0,
                    screenshot_path TEXT,
                    timings_json TEXT NOT NULL DEFAULT '{}',
                    action_json TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id, step_index),
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_updated_at
                    ON sessions(updated_at DESC);

                CREATE INDEX IF NOT EXISTS idx_steps_session_step
                    ON steps(session_id, step_index);
                """
            )


def _summary_from_row(row: sqlite3.Row) -> HistorySessionSummary:
    summary = str(row["summary"] or row["last_observation_summary"] or "")
    return HistorySessionSummary(
        session_id=str(row["session_id"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        status=_status_from_row(row["status"]),
        task=str(row["task"]),
        selected_model=str(row["selected_model"]),
        step_index=int(row["step_index"] or 0),
        summary=summary,
        last_screenshot_path=_optional_str(row["last_screenshot_path"]),
    )


def _detail_from_rows(session_row: sqlite3.Row, step_rows: list[sqlite3.Row]) -> HistorySessionDetail:
    summary = str(session_row["summary"] or session_row["last_observation_summary"] or "")
    steps = [
        StepRecord(
            step_index=int(row["step_index"]),
            action=str(row["action"]),
            thought=str(row["thought"] or ""),
            confidence=float(row["confidence"] or 0.0),
            result=str(row["result"] or ""),
            ok=bool(row["ok"]),
            screenshot_path=_optional_str(row["screenshot_path"]),
            timings=_json_dict(row["timings_json"]),
        )
        for row in step_rows
    ]
    return HistorySessionDetail(
        session_id=str(session_row["session_id"]),
        created_at=str(session_row["created_at"]),
        updated_at=str(session_row["updated_at"]),
        status=_status_from_row(session_row["status"]),
        task=str(session_row["task"]),
        selected_model=str(session_row["selected_model"]),
        step_index=int(session_row["step_index"] or 0),
        summary=summary,
        last_screenshot_path=_optional_str(session_row["last_screenshot_path"]),
        last_action=_json_dict_or_none(session_row["last_action_json"]),
        last_observation_summary=str(session_row["last_observation_summary"] or ""),
        steps=steps,
    )


def _json_or_none(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"), default=str)


def _json_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, str) or not value:
        return {}
    try:
        data: Any = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return cast(dict[str, Any], data) if isinstance(data, dict) else {}


def _json_dict_or_none(value: object) -> dict[str, Any] | None:
    parsed = _json_dict(value)
    return parsed or None


def _status_from_row(value: object) -> SessionStatus:
    text = str(value)
    if text in {"running", "done", "failed", "cancelled"}:
        return cast(SessionStatus, text)
    return "failed"


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None
