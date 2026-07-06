from __future__ import annotations

import asyncio
import inspect
import time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from httpx import HTTPError

from computeruse.agent.metrics import MetricsSampler, append_debug_timing_log
from computeruse.agent.ollama_client import OllamaClient
from computeruse.agent.perception import collect_screen_elements
from computeruse.agent.prompts import build_user_prompt
from computeruse.agent.session import SessionManager
from computeruse.config import (
    DEFAULT_ACTION_DELAY_MS,
    DEFAULT_MAX_STEPS,
    DEFAULT_MOVE_SETTLE_MS,
    DEFAULT_REPAIR_ATTEMPTS,
)
from computeruse.schemas.actions import ActionName, PlannerAction, parse_planner_action
from computeruse.schemas.session import ActiveSession
from computeruse.tools.executor import execute_action
from computeruse.tools.screen import ScreenshotResult
from computeruse.tools.screenshot import capture_screenshot, create_planner_screenshot

EventEmitter = Callable[[dict[str, Any]], Awaitable[None] | None]


def _noop_emit(_event: dict[str, Any]) -> None:
    return None


class StopRequested(Exception):
    pass


class LoopControl:
    def __init__(self) -> None:
        self._resume_event = asyncio.Event()
        self._resume_event.set()
        self.stop_requested = False

    def pause(self) -> None:
        self._resume_event.clear()

    def resume(self) -> None:
        self._resume_event.set()

    def stop(self) -> None:
        self.stop_requested = True
        self._resume_event.set()

    async def checkpoint(self) -> None:
        if self.stop_requested:
            raise StopRequested()
        await self._resume_event.wait()
        if self.stop_requested:
            raise StopRequested()


class AgentRunner:
    def __init__(
        self,
        *,
        ollama: OllamaClient | None = None,
        sessions: SessionManager | None = None,
        emit: EventEmitter | None = None,
        action_delay_ms: int = DEFAULT_ACTION_DELAY_MS,
        repair_attempts: int = DEFAULT_REPAIR_ATTEMPTS,
    ) -> None:
        self.ollama = ollama or OllamaClient()
        self.sessions = sessions or SessionManager()
        self.emit: EventEmitter = emit or _noop_emit
        self.action_delay_ms = action_delay_ms
        self.repair_attempts = repair_attempts
        self.metrics = MetricsSampler()

    async def run_task(
        self,
        *,
        task: str,
        model: str,
        dry_run: bool = False,
        max_steps: int = DEFAULT_MAX_STEPS,
        control: LoopControl | None = None,
    ) -> ActiveSession:
        control = control or LoopControl()
        session = self.sessions.start(task=task, selected_model=model)
        await self._emit({"type": "session_started", "session_id": session.session_id})

        try:
            for step_index in range(1, max_steps + 1):
                await control.checkpoint()
                await self._emit({"type": "step_started", "step_index": step_index})

                observe = capture_screenshot()
                await self._emit_screenshot(observe)
                perception = collect_screen_elements(observe)

                prompt = build_user_prompt(
                    task=task,
                    step_index=step_index,
                    screenshot_width=observe.width,
                    screenshot_height=observe.height,
                    recent_steps=session.recent_steps,
                    elements=perception.elements,
                    perception_message=perception.message,
                )

                action, model_timing = await self._get_valid_action(
                    model=model,
                    prompt=prompt,
                    screenshot=observe,
                    elements=perception.elements,
                    step_index=step_index,
                )
                action_payload = action.model_dump(mode="json")
                await self._emit({"type": "model_action", "action": action_payload})

                if action.action == ActionName.DONE:
                    timings = _timings(
                        observe,
                        model_timing,
                        0,
                        0,
                        0,
                        perception_ms=perception.perception_ms,
                        element_count=len(perception.elements),
                        metrics=self.metrics.sample(),
                    )
                    session = self.sessions.append_step(
                        session,
                        step_index=step_index,
                        action=action.action.value,
                        thought=action.thought,
                        confidence=action.confidence,
                        result=action.args["summary"],
                        ok=True,
                        screenshot_path=str(observe.path),
                        timings=timings,
                        last_action=action_payload,
                    )
                    _log_step_metrics(
                        session_id=session.session_id,
                        step_index=step_index,
                        task=task,
                        model=model,
                        action_payload=action_payload,
                        ok=True,
                        result=action.args["summary"],
                        timings=timings,
                    )
                    await self._emit({"type": "timing", "step_index": step_index, **timings})
                    session = self.sessions.mark_status(
                        session,
                        "done",
                        summary=action.args["summary"],
                        last_action=action_payload,
                    )
                    await self._emit({"type": "session_done", "summary": action.args["summary"]})
                    return session

                if action.action == ActionName.FAIL:
                    reason = action.args["reason"]
                    timings = _timings(
                        observe,
                        model_timing,
                        0,
                        0,
                        0,
                        perception_ms=perception.perception_ms,
                        element_count=len(perception.elements),
                        metrics=self.metrics.sample(),
                    )
                    session = self.sessions.append_step(
                        session,
                        step_index=step_index,
                        action=action.action.value,
                        thought=action.thought,
                        confidence=action.confidence,
                        result=reason,
                        ok=False,
                        screenshot_path=str(observe.path),
                        timings=timings,
                        last_action=action_payload,
                    )
                    _log_step_metrics(
                        session_id=session.session_id,
                        step_index=step_index,
                        task=task,
                        model=model,
                        action_payload=action_payload,
                        ok=False,
                        result=reason,
                        timings=timings,
                    )
                    await self._emit({"type": "timing", "step_index": step_index, **timings})
                    session = self.sessions.mark_status(session, "failed", summary=reason, last_action=action_payload)
                    await self._emit({"type": "session_failed", "reason": reason})
                    return session

                await control.checkpoint()
                result = execute_action(action, dry_run=dry_run, screenshot=observe, elements=perception.elements)
                await self._emit(
                    {
                        "type": "tool_result",
                        "ok": result.ok,
                        "message": result.message,
                        "recoverable": result.recoverable,
                    }
                )

                settle_ms = await self._settle_after_action(
                    action=action,
                    dry_run=dry_run,
                    action_ok=result.ok,
                    control=control,
                )

                verify = capture_screenshot()
                await self._emit_screenshot(verify)

                timings = _timings(
                    observe,
                    model_timing,
                    result.execute_ms,
                    verify.capture_ms + verify.encode_ms,
                    settle_ms=settle_ms,
                    perception_ms=perception.perception_ms,
                    element_count=len(perception.elements),
                    metrics=self.metrics.sample(),
                )
                session = self.sessions.append_step(
                    session,
                    step_index=step_index,
                    action=action.action.value,
                    thought=action.thought,
                    confidence=action.confidence,
                    result=result.message,
                    ok=result.ok,
                    screenshot_path=str(verify.path),
                    timings=timings,
                    last_action=action_payload,
                )
                _log_step_metrics(
                    session_id=session.session_id,
                    step_index=step_index,
                    task=task,
                    model=model,
                    action_payload=action_payload,
                    ok=result.ok,
                    result=result.message,
                    timings=timings,
                )
                await self._emit({"type": "timing", "step_index": step_index, **timings})

                if not result.ok and result.recoverable:
                    continue

                if not result.ok:
                    session = self.sessions.mark_status(
                        session,
                        "failed",
                        summary=result.message,
                        last_action=action_payload,
                    )
                    await self._emit({"type": "session_failed", "reason": result.message})
                    return session

            reason = f"Reached max_steps={max_steps} without completion."
            session = self.sessions.mark_status(session, "failed", summary=reason)
            await self._emit({"type": "session_failed", "reason": reason})
            return session
        except StopRequested:
            session = self.sessions.mark_status(session, "cancelled", summary="Cancelled by user.")
            await self._emit({"type": "session_cancelled", "reason": "Cancelled by user."})
            return session
        except HTTPError as exc:
            reason = f"Ollama request failed: {exc}"
            session = self.sessions.mark_status(session, "failed", summary=reason)
            await self._emit({"type": "session_failed", "reason": reason})
            return session
        except Exception as exc:
            reason = f"Agent loop failed: {exc}"
            session = self.sessions.mark_status(session, "failed", summary=reason)
            await self._emit({"type": "session_failed", "reason": reason})
            return session

    async def _get_valid_action(
        self,
        *,
        model: str,
        prompt: str,
        screenshot: ScreenshotResult,
        elements: list[Any],
        step_index: int,
    ) -> tuple[PlannerAction, dict[str, int]]:
        planner_screenshot = create_planner_screenshot(screenshot, elements=elements)
        response = await self.ollama.plan_action(
            model,
            prompt,
            planner_screenshot.path,
            stream_callback=self._planner_stream_callback(step_index=step_index, phase="plan"),
        )
        timing = {
            "encode_ms": response.encode_ms,
            "grid_ms": planner_screenshot.grid_ms,
            "ollama_ms": response.ollama_ms,
        }
        try:
            return parse_planner_action(response.raw), timing
        except ValueError as first_error:
            if self.repair_attempts < 1:
                raise

            repair_context = f"Invalid response: {response.raw}\nValidation error: {first_error}"
            repaired = await self.ollama.plan_action(
                model,
                prompt,
                planner_screenshot.path,
                repair_context=repair_context,
                stream_callback=self._planner_stream_callback(step_index=step_index, phase="repair"),
            )
            timing = {
                "encode_ms": response.encode_ms + repaired.encode_ms,
                "grid_ms": planner_screenshot.grid_ms,
                "ollama_ms": response.ollama_ms + repaired.ollama_ms,
            }
            return parse_planner_action(repaired.raw), timing

    def _planner_stream_callback(self, *, step_index: int, phase: str) -> EventEmitter:
        async def emit_stream(chunk: dict[str, Any]) -> None:
            await self._emit(
                {
                    "type": "planner_stream",
                    "step_index": step_index,
                    "phase": phase,
                    "delta": chunk.get("delta", ""),
                    "text": chunk.get("text", ""),
                    "done": bool(chunk.get("done")),
                }
            )

        return emit_stream

    async def _emit_screenshot(self, screenshot: ScreenshotResult) -> None:
        await self._emit(
            {
                "type": "screenshot",
                "path": str(screenshot.path),
                "width": screenshot.width,
                "height": screenshot.height,
                "left": screenshot.left,
                "top": screenshot.top,
                "monitor_width": screenshot.monitor_width,
                "monitor_height": screenshot.monitor_height,
            }
        )

    async def _emit(self, event: dict[str, Any]) -> None:
        result = self.emit(event)
        if inspect.isawaitable(result):
            await result

    async def _settle_after_action(
        self,
        *,
        action: PlannerAction,
        dry_run: bool,
        action_ok: bool,
        control: LoopControl,
    ) -> int:
        delay_ms = _settle_delay_ms(action, self.action_delay_ms, dry_run=dry_run, action_ok=action_ok)
        if delay_ms <= 0:
            return 0

        start = time.perf_counter()
        remaining = delay_ms / 1000
        while remaining > 0:
            await asyncio.sleep(min(0.1, remaining))
            await control.checkpoint()
            remaining = (delay_ms / 1000) - (time.perf_counter() - start)
        return int((time.perf_counter() - start) * 1000)


def _settle_delay_ms(action: PlannerAction, default_delay_ms: int, *, dry_run: bool, action_ok: bool) -> int:
    if dry_run or not action_ok or default_delay_ms <= 0:
        return 0
    if action.action in {ActionName.SCREENSHOT, ActionName.WAIT}:
        return 0
    if action.action in {ActionName.MOVE, ActionName.MOVE_ELEMENT, ActionName.MOVE_TARGET}:
        return min(default_delay_ms, DEFAULT_MOVE_SETTLE_MS)
    return default_delay_ms


def _timings(
    observe: ScreenshotResult,
    model_timing: dict[str, int],
    execute_ms: int,
    verify_ms: int,
    settle_ms: int = 0,
    perception_ms: int = 0,
    element_count: int = 0,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timings: dict[str, Any] = {
        "capture_ms": observe.capture_ms,
        "encode_ms": observe.encode_ms + model_timing.get("encode_ms", 0),
        "grid_ms": model_timing.get("grid_ms", 0),
        "perception_ms": perception_ms,
        "element_count": element_count,
        "ollama_ms": model_timing.get("ollama_ms", 0),
        "execute_ms": execute_ms,
        "settle_ms": settle_ms,
        "verify_ms": verify_ms,
    }
    if metrics:
        timings.update(metrics)
    return timings


def _log_step_metrics(
    *,
    session_id: str,
    step_index: int,
    task: str,
    model: str,
    action_payload: dict[str, Any],
    ok: bool,
    result: str,
    timings: dict[str, Any],
) -> None:
    record = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "step_index": step_index,
        "task": task,
        "model": model,
        "action": action_payload,
        "ok": ok,
        "result": result,
        "timings": timings,
    }
    try:
        append_debug_timing_log(record)
    except Exception:
        pass
