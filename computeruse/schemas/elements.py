from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScreenElement:
    id: str
    source: str
    role: str
    name: str
    x: int
    y: int
    width: int
    height: int
    click_x: int
    click_y: int

    @property
    def area(self) -> int:
        return self.width * self.height

    def prompt_line(self) -> str:
        label = self.name.strip().replace("\n", " ")
        if len(label) > 70:
            label = label[:67] + "..."
        name_part = f' name="{label}"' if label else ""
        return (
            f"- {self.id}: source={self.source} role={self.role}{name_part} "
            f"bounds=({self.x},{self.y},{self.width},{self.height}) "
            f"click=({self.click_x},{self.click_y})"
        )
