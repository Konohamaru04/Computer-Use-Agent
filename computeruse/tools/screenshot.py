from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias, cast

from computeruse.config import CURRENT_SCREENSHOT_PATH, PLANNER_SCREENSHOT_PATH, ensure_runtime_dirs
from computeruse.schemas.elements import ScreenElement
from computeruse.tools.dpi import ensure_process_dpi_awareness
from computeruse.tools.screen import ScreenshotResult

ensure_process_dpi_awareness()

from PIL import Image, ImageDraw, ImageFont

PlannerFont: TypeAlias = ImageFont.ImageFont | ImageFont.FreeTypeFont

GRID_FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("C:/Windows/Fonts/segoeuib.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)

RULER_LEFT = 104
RULER_TOP = 64


@dataclass(frozen=True)
class PlannerScreenshot:
    path: Path
    grid_ms: int
    minor_step: int
    major_step: int


def capture_screenshot(path: Path = CURRENT_SCREENSHOT_PATH, monitor_index: int = 1) -> ScreenshotResult:
    ensure_process_dpi_awareness()
    ensure_runtime_dirs()
    capture_start = time.perf_counter()
    import mss

    with cast(Any, mss.mss()) as sct:
        monitors = cast(list[dict[str, int]], sct.monitors)
        if monitor_index >= len(monitors):
            monitor_index = 1 if len(monitors) > 1 else 0
        monitor = monitors[monitor_index]
        shot = sct.grab(monitor)
    capture_ms = int((time.perf_counter() - capture_start) * 1000)

    encode_start = time.perf_counter()
    image = Image.frombytes("RGB", shot.size, shot.rgb)
    image.save(path, format="PNG")
    encode_ms = int((time.perf_counter() - encode_start) * 1000)

    return ScreenshotResult(
        path=path,
        width=shot.width,
        height=shot.height,
        left=int(monitor["left"]),
        top=int(monitor["top"]),
        monitor_width=int(monitor["width"]),
        monitor_height=int(monitor["height"]),
        capture_ms=capture_ms,
        encode_ms=encode_ms,
    )


def create_planner_screenshot(
    screenshot: ScreenshotResult,
    output_path: Path = PLANNER_SCREENSHOT_PATH,
    elements: Sequence[ScreenElement] | None = None,
) -> PlannerScreenshot:
    ensure_runtime_dirs()
    start = time.perf_counter()

    with Image.open(screenshot.path) as base:
        screenshot_image = base.convert("RGBA")

    width, height = screenshot_image.size
    minor_step, major_step = _grid_steps(width, height)
    planner_size = (width + RULER_LEFT, height + RULER_TOP)
    content_origin = (RULER_LEFT, RULER_TOP)
    image = Image.new("RGBA", planner_size, (20, 22, 22, 255))
    image.alpha_composite(screenshot_image, content_origin)
    overlay = Image.new("RGBA", planner_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    minor_color = (0, 190, 255, 28)
    major_color = (255, 230, 0, 62)
    border_color = (255, 230, 0, 185)
    ruler_fill = (0, 0, 0, 232)
    tick_color = (255, 230, 0, 210)

    draw.rectangle([(0, 0), (planner_size[0], RULER_TOP - 1)], fill=ruler_fill)
    draw.rectangle([(0, 0), (RULER_LEFT - 1, planner_size[1])], fill=ruler_fill)

    for x in range(0, width, minor_step):
        planner_x = RULER_LEFT + x
        color = major_color if x % major_step == 0 else minor_color
        line_width = 2 if x % major_step == 0 else 1
        draw.line([(planner_x, RULER_TOP), (planner_x, RULER_TOP + height)], fill=color, width=line_width)
        if x % major_step == 0:
            draw.line([(planner_x, RULER_TOP - 12), (planner_x, RULER_TOP + 12)], fill=tick_color, width=2)

    for y in range(0, height, minor_step):
        planner_y = RULER_TOP + y
        color = major_color if y % major_step == 0 else minor_color
        line_width = 2 if y % major_step == 0 else 1
        draw.line([(RULER_LEFT, planner_y), (RULER_LEFT + width, planner_y)], fill=color, width=line_width)
        if y % major_step == 0:
            draw.line([(RULER_LEFT - 12, planner_y), (RULER_LEFT + 12, planner_y)], fill=tick_color, width=2)

    draw.rectangle(
        [(RULER_LEFT, RULER_TOP), (RULER_LEFT + width - 1, RULER_TOP + height - 1)],
        outline=border_color,
        width=2,
    )
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)
    font = _load_grid_font(width, height)
    label_margin = 6
    _, label_height = _label_size(draw, font, "x=0000")
    top_label_y = max(4, (RULER_TOP - label_height) // 2 - 2)

    for x in range(0, width, major_step):
        label = f"x={x}"
        _draw_label(draw, font, RULER_LEFT + x + label_margin, top_label_y, label, planner_size)

    for y in range(0, height, major_step):
        label = f"y={y}"
        _draw_label(
            draw,
            font,
            label_margin,
            RULER_TOP + y - (label_height // 2),
            label,
            planner_size,
        )

    if elements:
        _draw_element_markers(draw, width, height, planner_size, elements)

    image.convert("RGB").save(output_path, format="PNG")
    return PlannerScreenshot(
        path=output_path,
        grid_ms=int((time.perf_counter() - start) * 1000),
        minor_step=minor_step,
        major_step=major_step,
    )


def _grid_steps(width: int, height: int) -> tuple[int, int]:
    longest = max(width, height)
    if longest >= 2400:
        return 100, 250
    if longest >= 1200:
        return 100, 200
    return 50, 100


def _load_grid_font(width: int, height: int) -> PlannerFont:
    font_size = max(18, min(46, min(width, height) // 40))
    for font_path in GRID_FONT_CANDIDATES:
        if font_path.exists():
            return ImageFont.truetype(str(font_path), font_size)
    try:
        return ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        return ImageFont.load_default()


def _load_element_font(width: int, height: int) -> PlannerFont:
    font_size = max(14, min(22, min(width, height) // 55))
    for font_path in GRID_FONT_CANDIDATES:
        if font_path.exists():
            return ImageFont.truetype(str(font_path), font_size)
    try:
        return ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        return ImageFont.load_default()


def _label_size(draw: ImageDraw.ImageDraw, font: PlannerFont, text: str) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    return int(right - left), int(bottom - top)


def _draw_label(
    draw: ImageDraw.ImageDraw,
    font: PlannerFont,
    x: int,
    y: int,
    text: str,
    image_size: tuple[int, int],
) -> None:
    text_width, text_height = _label_size(draw, font, text)
    pad_x = 8
    pad_y = 5
    image_width, image_height = image_size
    x = max(0, min(x, max(0, image_width - text_width - (pad_x * 2) - 2)))
    y = max(0, min(y, max(0, image_height - text_height - (pad_y * 2) - 2)))
    left, top, right, bottom = draw.textbbox((x, y), text, font=font, stroke_width=2)
    draw.rectangle(
        [(left - pad_x, top - pad_y), (right + pad_x, bottom + pad_y)],
        fill=(0, 0, 0, 225),
        outline=(255, 230, 0, 230),
        width=2,
    )
    draw.text(
        (x, y),
        text,
        fill=(255, 255, 255, 255),
        font=font,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
    )


def _draw_element_markers(
    draw: ImageDraw.ImageDraw,
    screenshot_width: int,
    screenshot_height: int,
    planner_size: tuple[int, int],
    elements: Sequence[ScreenElement],
) -> None:
    font = _load_element_font(screenshot_width, screenshot_height)
    for element in elements[:80]:
        left = RULER_LEFT + element.x
        top = RULER_TOP + element.y
        right = RULER_LEFT + element.x + element.width
        bottom = RULER_TOP + element.y + element.height
        if right <= RULER_LEFT or bottom <= RULER_TOP:
            continue
        if left >= RULER_LEFT + screenshot_width or top >= RULER_TOP + screenshot_height:
            continue

        outline = (0, 255, 170, 190)
        draw.rectangle(
            [(max(RULER_LEFT, left), max(RULER_TOP, top)), (min(RULER_LEFT + screenshot_width - 1, right), min(RULER_TOP + screenshot_height - 1, bottom))],
            outline=outline,
            width=2,
        )
        _draw_element_label(draw, font, left, top, element.id, planner_size)


def _draw_element_label(
    draw: ImageDraw.ImageDraw,
    font: PlannerFont,
    x: int,
    y: int,
    text: str,
    image_size: tuple[int, int],
) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font, stroke_width=1)
    text_width = right - left
    text_height = bottom - top
    pad_x = 5
    pad_y = 3
    image_width, image_height = image_size
    label_x = max(RULER_LEFT, min(x, max(RULER_LEFT, image_width - text_width - (pad_x * 2) - 2)))
    label_y = max(RULER_TOP, min(y, max(RULER_TOP, image_height - text_height - (pad_y * 2) - 2)))
    left, top, right, bottom = draw.textbbox((label_x, label_y), text, font=font, stroke_width=1)
    draw.rectangle(
        [(left - pad_x, top - pad_y), (right + pad_x, bottom + pad_y)],
        fill=(0, 0, 0, 215),
        outline=(0, 255, 170, 230),
        width=1,
    )
    draw.text(
        (label_x, label_y),
        text,
        fill=(255, 255, 255, 255),
        font=font,
        stroke_width=1,
        stroke_fill=(0, 0, 0, 255),
    )
