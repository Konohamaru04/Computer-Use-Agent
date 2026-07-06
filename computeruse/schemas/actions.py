from __future__ import annotations

import json
from enum import Enum
from typing import Any, cast

from pydantic import BaseModel, Field, ValidationError, model_validator


class ActionName(str, Enum):
    SCREENSHOT = "screenshot"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    MOVE = "move"
    SCROLL = "scroll"
    DRAG = "drag"
    CLICK_ELEMENT = "click_element"
    DOUBLE_CLICK_ELEMENT = "double_click_element"
    MOVE_ELEMENT = "move_element"
    CLICK_TARGET = "click_target"
    MOVE_TARGET = "move_target"
    TYPE_TEXT = "type_text"
    PRESS = "press"
    HOTKEY = "hotkey"
    WAIT = "wait"
    DONE = "done"
    FAIL = "fail"


COORDINATE_ACTIONS = {
    ActionName.CLICK,
    ActionName.DOUBLE_CLICK,
    ActionName.RIGHT_CLICK,
    ActionName.MOVE,
}

OPTIONAL_COORDINATE_ACTIONS = {
    ActionName.SCROLL,
}

DRAG_ACTIONS = {
    ActionName.DRAG,
}

ELEMENT_ACTIONS = {
    ActionName.CLICK_ELEMENT,
    ActionName.DOUBLE_CLICK_ELEMENT,
    ActionName.MOVE_ELEMENT,
}

TARGET_ACTIONS = {
    ActionName.CLICK_TARGET,
    ActionName.MOVE_TARGET,
}


class PlannerAction(BaseModel):
    thought: str = Field(default="", max_length=500)
    action: ActionName
    args: dict[str, Any] = Field(default_factory=dict)
    done: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_args_for_action(self) -> "PlannerAction":
        args = dict(self.args or {})

        if self.action in COORDINATE_ACTIONS:
            args["x"] = _non_negative_int(args, "x")
            args["y"] = _non_negative_int(args, "y")

        if self.action in OPTIONAL_COORDINATE_ACTIONS:
            has_x = args.get("x") is not None
            has_y = args.get("y") is not None
            if has_x != has_y:
                raise ValueError(f"{self.action.value} requires both args.x and args.y when either is provided")
            if has_x and has_y:
                args["x"] = _non_negative_int(args, "x")
                args["y"] = _non_negative_int(args, "y")
            clicks = _int_value(args, "clicks")
            if clicks == 0 or clicks < -100 or clicks > 100:
                raise ValueError("scroll args.clicks must be between -100 and 100, excluding 0")
            args["clicks"] = clicks

        if self.action in DRAG_ACTIONS:
            args["start_x"] = _non_negative_int(args, "start_x")
            args["start_y"] = _non_negative_int(args, "start_y")
            args["end_x"] = _non_negative_int(args, "end_x")
            args["end_y"] = _non_negative_int(args, "end_y")
            if args["start_x"] == args["end_x"] and args["start_y"] == args["end_y"]:
                raise ValueError("drag start and end coordinates must be different")
            duration_ms = _optional_int(args, "duration_ms", default=500)
            if duration_ms < 0 or duration_ms > 5000:
                raise ValueError("drag args.duration_ms must be between 0 and 5000")
            args["duration_ms"] = duration_ms

        if self.action in ELEMENT_ACTIONS:
            element_id = args.get("element_id")
            if not isinstance(element_id, str) or not element_id.strip():
                raise ValueError(f"{self.action.value} requires a non-empty string args.element_id")
            args["element_id"] = element_id.strip().upper()

        if self.action in TARGET_ACTIONS:
            query = args.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError(f"{self.action.value} requires a non-empty string args.query")
            if len(query) > 200:
                raise ValueError(f"{self.action.value} args.query is too long")
            args["query"] = query.strip()
            role = args.get("role")
            if role is not None:
                if not isinstance(role, str):
                    raise ValueError(f"{self.action.value} args.role must be a string")
                args["role"] = role.strip()

        if self.action == ActionName.TYPE_TEXT:
            text = args.get("text")
            if not isinstance(text, str) or not text:
                raise ValueError("type_text requires a non-empty string args.text")
            if len(text) > 5000:
                raise ValueError("type_text args.text is too long")

        if self.action == ActionName.PRESS:
            key = args.get("key")
            if not isinstance(key, str) or not key.strip():
                raise ValueError("press requires a non-empty string args.key")
            if len(key) > 64:
                raise ValueError("press args.key is too long")
            args["key"] = key.strip().lower()

        if self.action == ActionName.HOTKEY:
            raw_keys = args.get("keys")
            keys: list[Any]
            if isinstance(raw_keys, str):
                keys = [part.strip() for part in raw_keys.split("+") if part.strip()]
            elif isinstance(raw_keys, list):
                keys = cast(list[Any], raw_keys)
            else:
                raise ValueError("hotkey requires args.keys as a non-empty list")
            if not keys:
                raise ValueError("hotkey requires args.keys as a non-empty list")
            normalized: list[str] = []
            for key in keys:
                if not isinstance(key, str) or not key.strip():
                    raise ValueError("hotkey args.keys must contain strings")
                normalized.append(key.strip().lower())
            if len(normalized) > 6:
                raise ValueError("hotkey supports at most 6 keys")
            args["keys"] = normalized

        if self.action == ActionName.WAIT:
            ms = _non_negative_int(args, "ms")
            if ms < 100 or ms > 10000:
                raise ValueError("wait args.ms must be between 100 and 10000")
            args["ms"] = ms

        if self.action == ActionName.SCREENSHOT:
            args = {}

        if self.action == ActionName.DONE:
            summary = args.get("summary", "Task complete.")
            if not isinstance(summary, str) or not summary.strip():
                raise ValueError("done requires a non-empty args.summary")
            args["summary"] = summary.strip()
            self.done = True
        elif self.done:
            raise ValueError("done=true is only valid with action=done")

        if self.action == ActionName.FAIL:
            reason = args.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("fail requires a non-empty args.reason")
            args["reason"] = reason.strip()

        self.args = args
        return self


def _non_negative_int(args: dict[str, Any], key: str) -> int:
    raw = args.get(key)
    value = _int_value(args, key)
    if isinstance(raw, (int, float)) and raw < 0:
        raise ValueError(f"{key} must be non-negative")
    if isinstance(raw, (int, float)) and 0 < raw < 1:
        raise ValueError(f"{key} must be an absolute pixel coordinate, not a normalized fraction")
    if value < 0:
        raise ValueError(f"{key} must be non-negative")
    return value


def _int_value(args: dict[str, Any], key: str) -> int:
    value = args.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    if 0 < value < 1:
        raise ValueError(f"{key} must be an integer-like value, not a normalized fraction")
    return int(round(value))


def _optional_int(args: dict[str, Any], key: str, *, default: int) -> int:
    value = args.get(key, default)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    return int(round(value))


def extract_json_object(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("model response did not contain a JSON object")
    return text[start : end + 1]


def parse_planner_action(raw: str) -> PlannerAction:
    try:
        data = json.loads(extract_json_object(raw))
    except json.JSONDecodeError as exc:
        raise ValueError(f"model response was not valid JSON: {exc}") from exc

    try:
        return PlannerAction.model_validate(data)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
