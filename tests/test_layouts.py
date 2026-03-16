"""Tests for layout template parsing and traversal."""

from deck_crafter.geometry import ResolvedRect
from deck_crafter.layouts import CardLayoutTemplate, CardSide, ContainerLayout


def test_card_layout_template_parses_nested_nodes(demo_project_dict: dict[str, object]) -> None:
    """Layout templates should parse nested node trees and allow lookup by id."""
    layout = CardLayoutTemplate.from_dict(demo_project_dict["layouts"][0])  # type: ignore[index]

    assert isinstance(layout.front_root, ContainerLayout)
    assert layout.find_node(CardSide.FRONT, "title") is not None
    assert [node.id for node in layout.iter_nodes(CardSide.BACK)] == [
        "back_root",
        "back_image",
        "back_label",
    ]


def test_container_content_rect_applies_padding() -> None:
    """Container padding should shrink the child content rectangle."""
    container = ContainerLayout._from_dict(
        {
            "type": "container",
            "id": "root",
            "side": "front",
            "rect": {
                "x": {"mode": "relative", "value": 0.0, "ref": "card", "unit": "mm"},
                "y": {"mode": "relative", "value": 0.0, "ref": "card", "unit": "mm"},
                "width": {"mode": "relative", "value": 1.0, "ref": "card", "unit": "mm"},
                "height": {"mode": "relative", "value": 1.0, "ref": "card", "unit": "mm"},
                "anchor": "top_left",
            },
            "padding_left": {"mode": "absolute", "value": 2, "ref": "parent", "unit": "mm"},
            "padding_top": {"mode": "absolute", "value": 3, "ref": "parent", "unit": "mm"},
            "padding_right": {"mode": "absolute", "value": 4, "ref": "parent", "unit": "mm"},
            "padding_bottom": {"mode": "absolute", "value": 5, "ref": "parent", "unit": "mm"},
            "children": [],
        }
    )

    assert container.content_rect(
        ResolvedRect(0.0, 0.0, 63.0, 88.0),
        card_rect=ResolvedRect(0.0, 0.0, 63.0, 88.0),
    ) == ResolvedRect(2.0, 3.0, 57.0, 80.0)
