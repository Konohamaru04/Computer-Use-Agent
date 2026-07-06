from __future__ import annotations

import time
from dataclasses import dataclass
from difflib import SequenceMatcher

from computeruse.schemas.actions import ActionName, PlannerAction
from computeruse.schemas.elements import ScreenElement
from computeruse.tools import keyboard, mouse
from computeruse.tools.screen import ScreenshotResult


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    message: str
    execute_ms: int
    recoverable: bool = False


POINTER_ACTIONS = {
    ActionName.CLICK,
    ActionName.DOUBLE_CLICK,
    ActionName.RIGHT_CLICK,
    ActionName.MOVE,
}

OPTIONAL_POINTER_ACTIONS = {
    ActionName.SCROLL,
}

DRAG_POINTER_ACTIONS = {
    ActionName.DRAG,
}

ELEMENT_POINTER_ACTIONS = {
    ActionName.CLICK_ELEMENT,
    ActionName.DOUBLE_CLICK_ELEMENT,
    ActionName.MOVE_ELEMENT,
}

TARGET_POINTER_ACTIONS = {
    ActionName.CLICK_TARGET,
    ActionName.MOVE_TARGET,
}

LONG_NAME_TARGET_ROLES = {
    "dataitem",
    "hyperlink",
    "listitem",
    "menuitem",
    "tabitem",
}


def execute_action(
    action: PlannerAction,
    *,
    dry_run: bool = False,
    screenshot: ScreenshotResult | None = None,
    elements: list[ScreenElement] | None = None,
) -> ToolResult:
    if dry_run and action.action in POINTER_ACTIONS:
        mapped = _map_pointer_args(action, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        return ToolResult(
            True,
            (
                f"dry run: skipped {action.action.value}; "
                f"screenshot ({mapped.source_x}, {mapped.source_y}) maps to screen ({mapped.x}, {mapped.y})"
            ),
            0,
        )

    if dry_run and action.action in ELEMENT_POINTER_ACTIONS:
        mapped = _map_element_args(action, elements, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        return ToolResult(
            True,
            (
                f"dry run: skipped {action.action.value} {action.args['element_id']}; "
                f"element click point ({mapped.source_x}, {mapped.source_y}) maps to screen ({mapped.x}, {mapped.y})"
            ),
            0,
        )

    if dry_run and action.action in OPTIONAL_POINTER_ACTIONS:
        mapped = _map_optional_pointer_args(action, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        if mapped is None:
            return ToolResult(
                True,
                f"dry run: skipped {action.action.value} {action.args['clicks']} clicks at current pointer",
                0,
            )
        return ToolResult(
            True,
            (
                f"dry run: skipped {action.action.value} {action.args['clicks']} clicks; "
                f"screenshot ({mapped.source_x}, {mapped.source_y}) maps to screen ({mapped.x}, {mapped.y})"
            ),
            0,
        )

    if dry_run and action.action in DRAG_POINTER_ACTIONS:
        mapped_drag = _map_drag_args(action, screenshot)
        if isinstance(mapped_drag, ToolResult):
            return mapped_drag
        return ToolResult(
            True,
            f"dry run: skipped drag; {_drag_mapping_message(mapped_drag)}",
            0,
        )

    if dry_run and action.action in TARGET_POINTER_ACTIONS:
        mapped = _map_target_args(action, elements, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        return ToolResult(
            True,
            (
                f"dry run: skipped {action.action.value} '{action.args['query']}'; "
                f"{mapped.message}; target click point ({mapped.source_x}, {mapped.source_y}) "
                f"maps to screen ({mapped.x}, {mapped.y})"
            ),
            0,
        )

    if dry_run and action.action not in {ActionName.WAIT, ActionName.SCREENSHOT, ActionName.DONE, ActionName.FAIL}:
        return ToolResult(True, f"dry run: skipped {action.action.value}", 0)

    if action.action == ActionName.CLICK:
        mapped = _map_pointer_args(action, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        result = mouse.click(mapped.x, mapped.y)
        return _with_mapping(result.ok, result.message, result.execute_ms, mapped)
    if action.action == ActionName.DOUBLE_CLICK:
        mapped = _map_pointer_args(action, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        result = mouse.double_click(mapped.x, mapped.y)
        return _with_mapping(result.ok, result.message, result.execute_ms, mapped)
    if action.action == ActionName.RIGHT_CLICK:
        mapped = _map_pointer_args(action, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        result = mouse.right_click(mapped.x, mapped.y)
        return _with_mapping(result.ok, result.message, result.execute_ms, mapped)
    if action.action == ActionName.MOVE:
        mapped = _map_pointer_args(action, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        result = mouse.move(mapped.x, mapped.y)
        return _with_mapping(result.ok, result.message, result.execute_ms, mapped)
    if action.action == ActionName.SCROLL:
        mapped = _map_optional_pointer_args(action, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        if mapped is None:
            result = mouse.scroll(action.args["clicks"])
            return ToolResult(result.ok, result.message, result.execute_ms)
        result = mouse.scroll(action.args["clicks"], mapped.x, mapped.y)
        return _with_mapping(result.ok, result.message, result.execute_ms, mapped)
    if action.action == ActionName.DRAG:
        mapped_drag = _map_drag_args(action, screenshot)
        if isinstance(mapped_drag, ToolResult):
            return mapped_drag
        result = mouse.drag(
            mapped_drag.start.x,
            mapped_drag.start.y,
            mapped_drag.end.x,
            mapped_drag.end.y,
            action.args["duration_ms"],
        )
        message = f"{result.message}; {_drag_mapping_message(mapped_drag)}"
        return ToolResult(result.ok, message, result.execute_ms)
    if action.action == ActionName.CLICK_ELEMENT:
        mapped = _map_element_args(action, elements, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        result = mouse.click(mapped.x, mapped.y)
        return _with_mapping(result.ok, result.message, result.execute_ms, mapped)
    if action.action == ActionName.DOUBLE_CLICK_ELEMENT:
        mapped = _map_element_args(action, elements, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        result = mouse.double_click(mapped.x, mapped.y)
        return _with_mapping(result.ok, result.message, result.execute_ms, mapped)
    if action.action == ActionName.MOVE_ELEMENT:
        mapped = _map_element_args(action, elements, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        result = mouse.move(mapped.x, mapped.y)
        return _with_mapping(result.ok, result.message, result.execute_ms, mapped)
    if action.action == ActionName.CLICK_TARGET:
        mapped = _map_target_args(action, elements, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        result = mouse.click(mapped.x, mapped.y)
        return _with_mapping(result.ok, result.message, result.execute_ms, mapped)
    if action.action == ActionName.MOVE_TARGET:
        mapped = _map_target_args(action, elements, screenshot)
        if isinstance(mapped, ToolResult):
            return mapped
        result = mouse.move(mapped.x, mapped.y)
        return _with_mapping(result.ok, result.message, result.execute_ms, mapped)
    if action.action == ActionName.TYPE_TEXT:
        result = keyboard.type_text(action.args["text"])
        return ToolResult(result.ok, result.message, result.execute_ms)
    if action.action == ActionName.PRESS:
        result = keyboard.press(action.args["key"])
        return ToolResult(result.ok, result.message, result.execute_ms)
    if action.action == ActionName.HOTKEY:
        result = keyboard.hotkey(action.args["keys"])
        return ToolResult(result.ok, result.message, result.execute_ms)
    if action.action == ActionName.WAIT:
        start = time.perf_counter()
        time.sleep(action.args["ms"] / 1000)
        return ToolResult(True, f"waited {action.args['ms']} ms", int((time.perf_counter() - start) * 1000))
    if action.action == ActionName.SCREENSHOT:
        return ToolResult(True, "fresh screenshot requested", 0)
    if action.action == ActionName.DONE:
        return ToolResult(True, action.args["summary"], 0)
    if action.action == ActionName.FAIL:
        return ToolResult(False, action.args["reason"], 0)
    return ToolResult(False, f"unsupported action: {action.action}", 0)


@dataclass(frozen=True)
class MappedPointer:
    ok: bool
    x: int
    y: int
    source_x: int
    source_y: int
    message: str = ""
    execute_ms: int = 0


@dataclass(frozen=True)
class MappedDrag:
    start: MappedPointer
    end: MappedPointer


def _map_pointer_args(action: PlannerAction, screenshot: ScreenshotResult | None) -> MappedPointer | ToolResult:
    source_x = int(action.args["x"])
    source_y = int(action.args["y"])
    return _map_pointer_point(action.action.value, source_x, source_y, screenshot)


def _map_drag_args(action: PlannerAction, screenshot: ScreenshotResult | None) -> MappedDrag | ToolResult:
    start = _map_pointer_point(
        "drag start",
        int(action.args["start_x"]),
        int(action.args["start_y"]),
        screenshot,
    )
    if isinstance(start, ToolResult):
        return start
    end = _map_pointer_point(
        "drag end",
        int(action.args["end_x"]),
        int(action.args["end_y"]),
        screenshot,
    )
    if isinstance(end, ToolResult):
        return end
    return MappedDrag(start=start, end=end)


def _map_optional_pointer_args(
    action: PlannerAction,
    screenshot: ScreenshotResult | None,
) -> MappedPointer | ToolResult | None:
    if "x" not in action.args and "y" not in action.args:
        return None
    source_x = int(action.args["x"])
    source_y = int(action.args["y"])
    return _map_pointer_point(action.action.value, source_x, source_y, screenshot)


def _map_element_args(
    action: PlannerAction,
    elements: list[ScreenElement] | None,
    screenshot: ScreenshotResult | None,
) -> MappedPointer | ToolResult:
    element_id = str(action.args["element_id"]).upper()
    element = _find_element(element_id, elements)
    if element is None:
        known = ", ".join(element.id for element in (elements or [])[:20])
        suffix = f" Known element ids: {known}" if known else " No elements were detected for this screenshot."
        return ToolResult(False, f"{action.action.value} target {element_id} was not found.{suffix}", 0, True)
    return _map_pointer_point(action.action.value, element.click_x, element.click_y, screenshot)


def _map_target_args(
    action: PlannerAction,
    elements: list[ScreenElement] | None,
    screenshot: ScreenshotResult | None,
) -> MappedPointer | ToolResult:
    query = str(action.args["query"])
    role = str(action.args.get("role") or "")
    match = _find_target_element(query, elements, role=role)
    if match.element is None:
        return ToolResult(False, match.message, 0, True)
    mapped = _map_pointer_point(action.action.value, match.element.click_x, match.element.click_y, screenshot)
    if isinstance(mapped, MappedPointer):
        return MappedPointer(
            mapped.ok,
            mapped.x,
            mapped.y,
            mapped.source_x,
            mapped.source_y,
            message=f"{match.message}; score={match.score:.1f}",
        )
    return mapped


@dataclass(frozen=True)
class TargetMatch:
    element: ScreenElement | None
    score: float
    message: str


def _find_element(element_id: str, elements: list[ScreenElement] | None) -> ScreenElement | None:
    for element in elements or []:
        if element.id.upper() == element_id:
            return element
    return None


def _find_target_element(
    query: str,
    elements: list[ScreenElement] | None,
    *,
    role: str = "",
) -> TargetMatch:
    candidates = list(elements or [])
    if not candidates:
        return TargetMatch(None, 0.0, "No visible elements were detected for target matching.")

    scored = sorted(
        ((_target_score(query, element, role=role), element) for element in candidates),
        key=lambda item: item[0],
        reverse=True,
    )
    best_score, best_element = scored[0]
    if best_score >= 55:
        return TargetMatch(best_element, best_score, f"matched {best_element.id}")

    role_only = _role_only_input_match(query, candidates, role=role)
    if role_only.element is not None:
        return role_only

    top_matches = [(score, element) for score, element in scored if score > 0][:5]
    if top_matches:
        top = "; ".join(f"{element.id} {element.role} '{element.name}' score={score:.1f}" for score, element in top_matches)
    else:
        top = "none with textual evidence"
    return TargetMatch(
        None,
        best_score,
        f"No visible target confidently matched query '{query}'. Top candidates: {top}",
    )


def _target_score(query: str, element: ScreenElement, *, role: str = "") -> float:
    query_norm = _normalize(query)
    name_norm = _normalize(element.name)
    role_norm = _normalize(element.role)
    role_hint = _normalize(role)
    haystack = " ".join(part for part in (name_norm, role_norm) if part)
    if not query_norm or not haystack:
        return 0.0
    if role_hint and role_hint not in role_norm:
        return 0.0
    if len(name_norm) > 80 and role_norm not in LONG_NAME_TARGET_ROLES:
        return 0.0
    if role_norm == "text" and len(name_norm) > 80 and len(query_norm) < 15:
        return 0.0

    name_ratio = SequenceMatcher(None, query_norm, name_norm).ratio() if name_norm else 0.0
    haystack_ratio = SequenceMatcher(None, query_norm, haystack).ratio()
    query_tokens = set(query_norm.split())
    haystack_tokens = set(haystack.split())
    overlap_fraction = (len(query_tokens & haystack_tokens) / len(query_tokens)) if query_tokens else 0.0
    substring = bool(name_norm and query_norm in name_norm)
    haystack_substring = query_norm in haystack

    if not substring and overlap_fraction == 0 and name_ratio < 0.72:
        return 0.0

    score = haystack_ratio * 35
    if name_norm:
        score = max(score, name_ratio * 65)
    if substring:
        score += 45
    elif haystack_substring:
        score += 25

    score += 35 * overlap_fraction

    if role_hint:
        score += 20
    if element.name:
        score += 5
    if element.width * element.height > 250_000:
        score -= 15
    return score


def _role_only_input_match(
    query: str,
    elements: list[ScreenElement],
    *,
    role: str,
) -> TargetMatch:
    role_hint = _normalize(role)
    query_tokens = set(_normalize(query).split())
    if role_hint not in {"combobox", "edit"}:
        return TargetMatch(None, 0.0, "")
    if not query_tokens & {"address", "field", "find", "input", "omnibox", "search", "text", "url"}:
        return TargetMatch(None, 0.0, "")

    candidates = [
        element
        for element in elements
        if role_hint in _normalize(element.role)
        and element.width >= 120
        and element.height >= 18
        and len(_normalize(element.name)) <= 100
    ]
    if len(candidates) == 1:
        element = candidates[0]
        return TargetMatch(element, 56.0, f"role-only input match {element.id}")

    top_region = [
        element
        for element in candidates
        if element.y <= 220 and element.width >= 180
    ]
    if len(top_region) == 1:
        element = top_region[0]
        return TargetMatch(element, 56.0, f"role-only top input match {element.id}")

    return TargetMatch(None, 0.0, "")


def _normalize(value: str) -> str:
    return " ".join("".join(char.lower() if char.isalnum() else " " for char in value).split())


def _map_pointer_point(
    action_name: str,
    source_x: int,
    source_y: int,
    screenshot: ScreenshotResult | None,
) -> MappedPointer | ToolResult:
    if screenshot is None:
        return MappedPointer(True, source_x, source_y, source_x, source_y)

    if not (0 <= source_x < screenshot.width and 0 <= source_y < screenshot.height):
        return ToolResult(
            False,
            (
                f"{action_name} coordinate ({source_x}, {source_y}) is outside "
                f"the latest screenshot bounds {screenshot.width}x{screenshot.height}"
            ),
            0,
        )

    mapped_x = screenshot.left + _scale_pixel(source_x, screenshot.width, screenshot.monitor_width)
    mapped_y = screenshot.top + _scale_pixel(source_y, screenshot.height, screenshot.monitor_height)

    return MappedPointer(True, mapped_x, mapped_y, source_x, source_y)


def _scale_pixel(value: int, source_size: int, target_size: int) -> int:
    if source_size <= 1 or target_size <= 1:
        return 0
    scaled = round(value * (target_size / source_size))
    return max(0, min(target_size - 1, scaled))


def _with_mapping(ok: bool, message: str, execute_ms: int, mapped: MappedPointer) -> ToolResult:
    prefix = f"{mapped.message}; " if mapped.message else ""
    if mapped.x == mapped.source_x and mapped.y == mapped.source_y:
        return ToolResult(ok, f"{prefix}{message}; used screenshot coordinates directly", execute_ms)
    return ToolResult(
        ok,
        f"{prefix}{message}; mapped screenshot ({mapped.source_x}, {mapped.source_y}) to screen ({mapped.x}, {mapped.y})",
        execute_ms,
    )


def _drag_mapping_message(mapped: MappedDrag) -> str:
    if (
        mapped.start.x == mapped.start.source_x
        and mapped.start.y == mapped.start.source_y
        and mapped.end.x == mapped.end.source_x
        and mapped.end.y == mapped.end.source_y
    ):
        return "used screenshot coordinates directly"
    return (
        f"mapped screenshot start ({mapped.start.source_x}, {mapped.start.source_y}) "
        f"to screen ({mapped.start.x}, {mapped.start.y}) and screenshot end "
        f"({mapped.end.source_x}, {mapped.end.source_y}) to screen ({mapped.end.x}, {mapped.end.y})"
    )
