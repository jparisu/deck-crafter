"""Tests for geometry primitives and measure resolution."""

from deck_crafter.geometry import Measure, MeasureMode, Rect, ReferenceFrame, ResolvedRect


def test_measure_resolves_relative_and_absolute_values() -> None:
    """Relative and absolute measures should resolve to millimetres."""
    relative = Measure(mode=MeasureMode.RELATIVE, value=0.5, ref=ReferenceFrame.CARD)
    absolute = Measure(mode=MeasureMode.ABSOLUTE, value=1.0, unit="cm")

    assert relative.resolve(card_size=80.0, parent_size=20.0) == 40.0
    assert absolute.resolve(card_size=80.0, parent_size=20.0) == 10.0


def test_rect_resolves_anchor_coordinates() -> None:
    """Rectangles should convert anchor coordinates to top-left coordinates."""
    rect = Rect.from_dict(
        {
            "x": {"mode": "relative", "value": 0.5, "ref": "parent", "unit": "mm"},
            "y": {"mode": "relative", "value": 0.5, "ref": "parent", "unit": "mm"},
            "width": {"mode": "absolute", "value": 20, "ref": "parent", "unit": "mm"},
            "height": {"mode": "absolute", "value": 10, "ref": "parent", "unit": "mm"},
            "anchor": "center",
        }
    )

    resolved = rect.resolve(
        card_rect=ResolvedRect(0.0, 0.0, 63.0, 88.0),
        parent_rect=ResolvedRect(10.0, 20.0, 100.0, 80.0),
    )

    assert resolved == ResolvedRect(x=50.0, y=55.0, width=20.0, height=10.0)


def test_resolved_rect_inset_never_goes_negative() -> None:
    """Insets should clamp widths and heights at zero."""
    rect = ResolvedRect(0.0, 0.0, 5.0, 5.0)

    assert rect.inset(3.0, 3.0, 3.0, 3.0) == ResolvedRect(3.0, 3.0, 0.0, 0.0)
