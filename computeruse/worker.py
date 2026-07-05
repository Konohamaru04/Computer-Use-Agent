from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from computeruse.agent.loop import AgentRunner, LoopControl
from computeruse.agent.ollama_client import OllamaClient
from computeruse.agent.session import SessionManager
from computeruse.config import DEFAULT_MAX_STEPS, ensure_runtime_dirs
from computeruse.tools.screenshot import capture_screenshot


TERMINAL_HISTORY_EVENTS = {"session_started", "session_done", "session_failed", "session_cancelled"}


class Worker:
    def __init__(self) -> None:
        ensure_runtime_dirs()
        self.ollama = OllamaClient()
        self.sessions = SessionManager()
        self.control: LoopControl | None = None
        self.current_task: asyncio.Task[Any] | None = None

    async def run(self) -> None:
        await self.emit({"type": "ready"})
        while True:
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line:
                await self.stop_current_task()
                await self.ollama.close()
                return

            try:
                command = json.loads(line)
            except json.JSONDecodeError as exc:
                await self.emit({"type": "error", "message": f"invalid command JSON: {exc}"})
                continue

            await self.handle_command(command)

    async def handle_command(self, command: dict[str, Any]) -> None:
        command_type = command.get("type")

        if command_type == "list_models":
            try:
                models = await self.ollama.list_models()
                await self.emit({"type": "models", "models": [model.as_dict() for model in models]})
            except Exception as exc:
                await self.emit({"type": "error", "message": f"failed to list models: {exc}"})
            return

        if command_type == "take_screenshot":
            try:
                shot = capture_screenshot()
                await self.emit(
                    {
                        "type": "screenshot",
                        "path": str(shot.path),
                        "width": shot.width,
                        "height": shot.height,
                        "left": shot.left,
                        "top": shot.top,
                        "monitor_width": shot.monitor_width,
                        "monitor_height": shot.monitor_height,
                    }
                )
            except Exception as exc:
                await self.emit({"type": "error", "message": f"failed to capture screenshot: {exc}"})
            return

        if command_type == "list_history":
            await self.emit_history(limit=_int_option(command.get("limit"), default=50))
            return

        if command_type == "get_history_session":
            session_id = str(command.get("session_id") or "").strip()
            if not session_id:
                await self.emit({"type": "error", "message": "get_history_session requires session_id"})
                return
            session = self.sessions.get_history_session(session_id)
            await self.emit(
                {
                    "type": "history_session",
                    "session": session.model_dump(mode="json") if session else None,
                }
            )
            return

        if command_type == "start_task":
            await self.start_task(command)
            return

        if command_type == "pause":
            if self.control:
                self.control.pause()
            await self.emit({"type": "status", "status": "paused"})
            return

        if command_type == "resume":
            if self.control:
                self.control.resume()
            await self.emit({"type": "status", "status": "running"})
            return

        if command_type == "stop":
            await self.stop_current_task()
            return

        await self.emit({"type": "error", "message": f"unknown command type: {command_type}"})

    async def start_task(self, command: dict[str, Any]) -> None:
        if self.current_task and not self.current_task.done():
            await self.emit({"type": "error", "message": "a task is already running"})
            return

        task = str(command.get("task") or "").strip()
        model = str(command.get("model") or "").strip()
        if not task:
            await self.emit({"type": "error", "message": "start_task requires task"})
            return
        if not model:
            await self.emit({"type": "error", "message": "start_task requires model"})
            return

        self.control = LoopControl()
        runner = AgentRunner(ollama=self.ollama, sessions=self.sessions, emit=self.emit)
        self.current_task = asyncio.create_task(
            runner.run_task(
                task=task,
                model=model,
                dry_run=bool(command.get("dry_run", False)),
                max_steps=int(command.get("max_steps") or DEFAULT_MAX_STEPS),
                control=self.control,
            )
        )

    async def emit_history(self, *, limit: int = 50) -> None:
        sessions = self.sessions.list_history(limit=limit)
        await self.emit(
            {
                "type": "history",
                "sessions": [session.model_dump(mode="json") for session in sessions],
            }
        )

    async def stop_current_task(self) -> None:
        if self.control:
            self.control.stop()
        if self.current_task and not self.current_task.done():
            await self.emit({"type": "status", "status": "cancelled"})
            return
        await self.emit({"type": "status", "status": "idle"})

    async def emit(self, event: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(event, separators=(",", ":")) + "\n")
        sys.stdout.flush()
        if event.get("type") in TERMINAL_HISTORY_EVENTS:
            await self.emit_history()


def _int_option(value: object, *, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if not isinstance(value, str):
        return default
    try:
        return int(value)
    except ValueError:
        return default


def main() -> None:
    asyncio.run(Worker().run())


if __name__ == "__main__":
    main()
