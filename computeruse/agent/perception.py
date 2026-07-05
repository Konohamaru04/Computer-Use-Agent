from __future__ import annotations

import time
from importlib import import_module
from dataclasses import dataclass
from typing import Any, cast

from computeruse.schemas.elements import ScreenElement
from computeruse.tools.screen import ScreenshotResult

MAX_SCREEN_ELEMENTS = 80
MAX_UIA_WRAPPERS_PER_ROLE = 80
CLICKABLE_ROLES = {
    "Button",
    "Calendar",
    "CheckBox",
    "ComboBox",
    "DataItem",
    "Edit",
    "Hyperlink",
    "Image",
    "ListItem",
    "MenuItem",
    "RadioButton",
    "ScrollBar",
    "Slider",
    "SplitButton",
    "TabItem",
    "Text",
    "Thumb",
    "TreeItem",
}
UIA_QUERY_ROLES = (
    "Edit",
    "ComboBox",
    "TabItem",
    "ListItem",
    "Hyperlink",
    "MenuItem",
    "Button",
    "CheckBox",
    "RadioButton",
    "SplitButton",
    "DataItem",
    "Image",
    "TreeItem",
    "Calendar",
    "ScrollBar",
    "Slider",
    "Thumb",
)


@dataclass(frozen=True)
class PerceptionResult:
    elements: list[ScreenElement]
    perception_ms: int
    message: str = ""


def collect_screen_elements(screenshot: ScreenshotResult) -> PerceptionResult:
    start = time.perf_counter()
    try:
        elements, hidden_count, error_count = _collect_uia_elements(screenshot)
        suffix = f", filtered {hidden_count} occluded elements" if hidden_count else ""
        if error_count:
            suffix += f", skipped {error_count} UIA errors"
        message = f"{len(elements)} visible UIA elements{suffix}"
    except ModuleNotFoundError as exc:
        elements = []
        message = f"UIA unavailable: {exc.name}"
    except Exception as exc:
        elements = []
        message = f"UIA failed: {exc}"

    return PerceptionResult(
        elements=elements[:MAX_SCREEN_ELEMENTS],
        perception_ms=int((time.perf_counter() - start) * 1000),
        message=message,
    )


def _collect_uia_elements(screenshot: ScreenshotResult) -> tuple[list[ScreenElement], int, int]:
    pywinauto = cast(Any, import_module("pywinauto"))

    wrappers: list[Any] = []
    desktop = pywinauto.Desktop(backend="uia")
    error_count = 0
    try:
        windows = cast(list[Any], desktop.windows(visible_only=True, enabled_only=False))
    except Exception:
        return [], 0, 1

    foreground_root = _foreground_root_handle()
    hidden_count = 0
    for window in windows:
        try:
            if not _wrapper_has_visible_area(window, screenshot):
                hidden_count += 1
                continue
        except Exception:
            error_count += 1
        wrappers.append(window)
        root_handle = _wrapper_root_handle(window)
        include_descendants = root_handle == foreground_root or _is_shell_surface(root_handle)
        if not include_descendants:
            continue
        for role in UIA_QUERY_ROLES:
            try:
                descendants = cast(list[Any], window.descendants(control_type=role))
                wrappers.extend(descendants[:MAX_UIA_WRAPPERS_PER_ROLE])
            except Exception:
                error_count += 1
            continue

    elements: list[ScreenElement] = []
    seen: set[tuple[int, int, int, int, str, str]] = set()

    for wrapper in wrappers:
        try:
            candidate = _wrapper_to_element(wrapper, screenshot)
        except Exception:
            error_count += 1
            continue
        if candidate is None:
            continue
        try:
            visible_at_point = _click_point_hits_wrapper_window(wrapper, screenshot, candidate.click_x, candidate.click_y)
        except Exception:
            error_count += 1
            visible_at_point = True
        if not visible_at_point:
            hidden_count += 1
            continue

        key = (
            candidate.x,
            candidate.y,
            candidate.width,
            candidate.height,
            candidate.name.lower(),
            candidate.role,
        )
        if key in seen:
            continue
        seen.add(key)
        elements.append(candidate)

    elements.sort(key=_element_sort_key)
    visible_elements = [_renumber(element, index + 1) for index, element in enumerate(elements[:MAX_SCREEN_ELEMENTS])]
    return visible_elements, hidden_count, error_count


def _wrapper_to_element(wrapper: Any, screenshot: ScreenshotResult) -> ScreenElement | None:
    rect = wrapper.rectangle()
    left = int(rect.left)
    top = int(rect.top)
    right = int(rect.right)
    bottom = int(rect.bottom)
    if right <= left or bottom <= top:
        return None

    x1 = _screen_to_screenshot_x(left, screenshot)
    y1 = _screen_to_screenshot_y(top, screenshot)
    x2 = _screen_to_screenshot_x(right, screenshot)
    y2 = _screen_to_screenshot_y(bottom, screenshot)
    clipped_left = max(0, min(screenshot.width - 1, min(x1, x2)))
    clipped_top = max(0, min(screenshot.height - 1, min(y1, y2)))
    clipped_right = max(0, min(screenshot.width, max(x1, x2)))
    clipped_bottom = max(0, min(screenshot.height, max(y1, y2)))
    width = clipped_right - clipped_left
    height = clipped_bottom - clipped_top
    if width < 8 or height < 8:
        return None
    if width * height > screenshot.width * screenshot.height * 0.35:
        return None

    role = _role(wrapper)
    name = _name(wrapper)
    if role not in CLICKABLE_ROLES and not name:
        return None

    click_x, click_y = _click_point(wrapper, screenshot, clipped_left, clipped_top, width, height)
    if not (0 <= click_x < screenshot.width and 0 <= click_y < screenshot.height):
        return None

    return ScreenElement(
        id="E0",
        source="uia",
        role=role,
        name=name,
        x=clipped_left,
        y=clipped_top,
        width=width,
        height=height,
        click_x=click_x,
        click_y=click_y,
    )


def _name(wrapper: Any) -> str:
    for getter in (
        lambda: wrapper.element_info.name,
        lambda: wrapper.window_text(),
    ):
        try:
            value = getter()
            if isinstance(value, str):
                return value.strip()
        except Exception:
            continue
    return ""


def _role(wrapper: Any) -> str:
    try:
        control_type = wrapper.element_info.control_type
        if control_type:
            return str(control_type)
    except Exception:
        pass
    try:
        friendly = wrapper.friendly_class_name()
        if friendly:
            return str(friendly)
    except Exception:
        pass
    return "Control"


def _click_point(
    wrapper: Any,
    screenshot: ScreenshotResult,
    fallback_left: int,
    fallback_top: int,
    fallback_width: int,
    fallback_height: int,
) -> tuple[int, int]:
    return (
        fallback_left + fallback_width // 2,
        fallback_top + fallback_height // 2,
    )


def _screen_to_screenshot_x(screen_x: int, screenshot: ScreenshotResult) -> int:
    return round((screen_x - screenshot.left) * (screenshot.width / max(1, screenshot.monitor_width)))


def _screen_to_screenshot_y(screen_y: int, screenshot: ScreenshotResult) -> int:
    return round((screen_y - screenshot.top) * (screenshot.height / max(1, screenshot.monitor_height)))


def _screenshot_to_screen_x(image_x: int, screenshot: ScreenshotResult) -> int:
    return screenshot.left + round(image_x * (screenshot.monitor_width / max(1, screenshot.width)))


def _screenshot_to_screen_y(image_y: int, screenshot: ScreenshotResult) -> int:
    return screenshot.top + round(image_y * (screenshot.monitor_height / max(1, screenshot.height)))


def _click_point_hits_wrapper_window(
    wrapper: Any,
    screenshot: ScreenshotResult,
    image_x: int,
    image_y: int,
) -> bool:
    wrapper_root = _wrapper_root_handle(wrapper)
    if not wrapper_root:
        return True

    hit_root = _root_window_from_point(
        _screenshot_to_screen_x(image_x, screenshot),
        _screenshot_to_screen_y(image_y, screenshot),
    )
    if not hit_root:
        return True
    return hit_root == wrapper_root


def _wrapper_has_visible_area(wrapper: Any, screenshot: ScreenshotResult) -> bool:
    wrapper_root = _wrapper_root_handle(wrapper)
    if not wrapper_root:
        return True

    rect = wrapper.rectangle()
    left = max(int(rect.left), screenshot.left)
    top = max(int(rect.top), screenshot.top)
    right = min(int(rect.right), screenshot.left + screenshot.monitor_width)
    bottom = min(int(rect.bottom), screenshot.top + screenshot.monitor_height)
    if right <= left or bottom <= top:
        return False

    sample_points = (
        ((left + right) // 2, (top + bottom) // 2),
        (left + max(1, (right - left) // 4), top + max(1, (bottom - top) // 4)),
        (right - max(1, (right - left) // 4), top + max(1, (bottom - top) // 4)),
        (left + max(1, (right - left) // 4), bottom - max(1, (bottom - top) // 4)),
        (right - max(1, (right - left) // 4), bottom - max(1, (bottom - top) // 4)),
    )
    for screen_x, screen_y in sample_points:
        if _root_window_from_point(screen_x, screen_y) == wrapper_root:
            return True
    return False


def _wrapper_root_handle(wrapper: Any) -> int:
    for getter in (
        lambda: wrapper.top_level_parent().handle,
        lambda: wrapper.handle,
        lambda: wrapper.element_info.handle,
    ):
        try:
            handle = _handle_to_int(getter())
            if handle:
                return _root_window_from_handle(handle)
        except Exception:
            continue
    return 0


def _foreground_root_handle() -> int:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.argtypes = []
        user32.GetForegroundWindow.restype = wintypes.HWND
        return _root_window_from_handle(_handle_to_int(user32.GetForegroundWindow()))
    except Exception:
        return 0


def _is_shell_surface(handle: int) -> bool:
    class_name = _window_class_name(handle)
    return class_name in {"Progman", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "WorkerW"}


def _window_class_name(handle: int) -> str:
    if not handle:
        return ""
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetClassNameW.restype = ctypes.c_int
        buffer = ctypes.create_unicode_buffer(256)
        length = user32.GetClassNameW(handle, buffer, len(buffer))
        return buffer.value[:length]
    except Exception:
        return ""


def _root_window_from_point(screen_x: int, screen_y: int) -> int:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        user32.WindowFromPoint.restype = wintypes.HWND
        point = wintypes.POINT(screen_x, screen_y)
        return _root_window_from_handle(_handle_to_int(user32.WindowFromPoint(point)))
    except Exception:
        return 0


def _root_window_from_handle(handle: int) -> int:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetAncestor.restype = wintypes.HWND
        root = _handle_to_int(user32.GetAncestor(handle, 2))
        return root or handle
    except Exception:
        return handle


def _handle_to_int(handle: Any) -> int:
    if handle is None:
        return 0
    if isinstance(handle, int):
        return handle
    value = getattr(handle, "value", handle)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _element_sort_key(element: ScreenElement) -> tuple[int, int, int, int, int]:
    named_penalty = 0 if element.name else 1
    role_penalty = 0 if element.role in CLICKABLE_ROLES else 1
    return (role_penalty, named_penalty, element.y, element.x, element.area)


def _renumber(element: ScreenElement, index: int) -> ScreenElement:
    return ScreenElement(
        id=f"E{index}",
        source=element.source,
        role=element.role,
        name=element.name,
        x=element.x,
        y=element.y,
        width=element.width,
        height=element.height,
        click_x=element.click_x,
        click_y=element.click_y,
    )
