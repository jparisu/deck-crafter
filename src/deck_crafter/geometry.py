"""Geometry primitives used by layouts, cards, previews, and LaTeX rendering."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from deck_crafter.utilizing.structuring.GenericEnumRegistry import GenericEnumRegistry


class MeasureMode(GenericEnumRegistry):
    """How a measure should be interpreted during resolution."""

    ABSOLUTE = "absolute"
    RELATIVE = "relative"


class ReferenceFrame(GenericEnumRegistry):
    """Coordinate frame used by relative measures."""

    CARD = "card"
    PARENT = "parent"


@dataclass(slots=True)
class ResolvedRect:
    """Concrete rectangle expressed in millimetres."""

    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        """Return the x-coordinate of the right edge."""
        return self.x + self.width

    @property
    def bottom(self) -> float:
        """Return the y-coordinate of the bottom edge."""
        return self.y + self.height

    def inset(self, left: float, top: float, right: float, bottom: float) -> ResolvedRect:
        """Return a rectangle reduced by the provided padding values."""
        return ResolvedRect(
            x=self.x + left,
            y=self.y + top,
            width=max(self.width - left - right, 0.0),
            height=max(self.height - top - bottom, 0.0),
        )

    def to_dict(self) -> dict[str, float]:
        """Serialize the rectangle for JSON responses and YAML exports."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(slots=True)
class Measure:
    """A position or size value that can be absolute or relative."""

    mode: MeasureMode = MeasureMode.RELATIVE
    value: float = 0.0
    unit: str = "mm"
    ref: ReferenceFrame = ReferenceFrame.PARENT

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Measure:
        """Create a measure from a mapping payload."""
        mode = MeasureMode.find(str(data.get("mode", MeasureMode.RELATIVE.value)))
        ref = ReferenceFrame.find(str(data.get("ref", ReferenceFrame.PARENT.value)))
        if mode is None or ref is None:
            raise ValueError("Measure mode and reference frame must resolve to known values.")
        raw_value = cast(float | int | str, data.get("value", 0.0))
        return cls(
            mode=mode,
            value=float(raw_value),
            unit=str(data.get("unit", "mm")),
            ref=ref,
        )

    def resolve(self, *, card_size: float, parent_size: float) -> float:
        """Resolve the measure to millimetres."""
        if self.mode is MeasureMode.RELATIVE:
            reference_size = card_size if self.ref is ReferenceFrame.CARD else parent_size
            return reference_size * float(self.value)
        return _absolute_to_mm(float(self.value), self.unit)


@dataclass(slots=True)
class Rect:
    """Rectangle specification used by layout nodes before resolution."""

    x: Measure
    y: Measure
    width: Measure
    height: Measure
    anchor: str = "top_left"

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Rect:
        """Create a rectangle from a mapping payload."""
        return cls(
            x=Measure.from_dict(_expect_mapping(data.get("x"), "x")),
            y=Measure.from_dict(_expect_mapping(data.get("y"), "y")),
            width=Measure.from_dict(_expect_mapping(data.get("width"), "width")),
            height=Measure.from_dict(_expect_mapping(data.get("height"), "height")),
            anchor=str(data.get("anchor", "top_left")),
        )

    def resolve(self, *, card_rect: ResolvedRect, parent_rect: ResolvedRect) -> ResolvedRect:
        """Resolve the rectangle to absolute millimetre coordinates."""
        width = self.width.resolve(card_size=card_rect.width, parent_size=parent_rect.width)
        height = self.height.resolve(card_size=card_rect.height, parent_size=parent_rect.height)
        anchor_x = self.x.resolve(card_size=card_rect.width, parent_size=parent_rect.width)
        anchor_y = self.y.resolve(card_size=card_rect.height, parent_size=parent_rect.height)
        local_x, local_y = _anchor_to_top_left(anchor_x, anchor_y, width, height, self.anchor)
        return ResolvedRect(
            x=parent_rect.x + local_x,
            y=parent_rect.y + local_y,
            width=width,
            height=height,
        )


def _absolute_to_mm(value: float, unit: str) -> float:
    """Convert an absolute measure into millimetres."""
    normalized_unit = unit.lower()
    if normalized_unit == "mm":
        return value
    if normalized_unit == "cm":
        return value * 10.0
    if normalized_unit == "in":
        return value * 25.4
    if normalized_unit == "pt":
        return value * 0.352777778
    raise ValueError(f"Unsupported absolute unit: {unit!r}")


def _anchor_to_top_left(
    x: float, y: float, width: float, height: float, anchor: str
) -> tuple[float, float]:
    """Translate an anchor point into a top-left origin."""
    normalized = anchor.lower()
    if normalized == "top_left":
        return x, y
    if normalized == "top_center":
        return x - (width / 2.0), y
    if normalized == "top_right":
        return x - width, y
    if normalized == "center_left":
        return x, y - (height / 2.0)
    if normalized == "center":
        return x - (width / 2.0), y - (height / 2.0)
    if normalized == "center_right":
        return x - width, y - (height / 2.0)
    if normalized == "bottom_left":
        return x, y - height
    if normalized == "bottom_center":
        return x - (width / 2.0), y - height
    if normalized == "bottom_right":
        return x - width, y - height
    raise ValueError(f"Unsupported anchor: {anchor!r}")


def _expect_mapping(value: object, key: str) -> dict[str, object]:
    """Validate that a nested geometry field is represented as a mapping."""
    if not isinstance(value, dict):
        raise TypeError(f"Expected '{key}' to be a mapping, got {type(value).__name__}.")
    return value
