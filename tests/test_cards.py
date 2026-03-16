"""Tests for card values and card specs."""

from deck_crafter.cards import CardSpec, CardValue, ColorValue, ImageValue, TextValue
from deck_crafter.layouts import CardSide


def test_card_value_dispatch_supports_all_registered_types() -> None:
    """Card values should dispatch to the correct concrete classes."""
    assert isinstance(CardValue.from_dict({"type": "text", "text": "hello"}), TextValue)
    assert isinstance(CardValue.from_dict({"type": "image", "path": "asset.png"}), ImageValue)
    assert isinstance(CardValue.from_dict({"type": "color", "color": "#ffffff"}), ColorValue)


def test_card_spec_returns_values_per_side(demo_project_dict: dict[str, object]) -> None:
    """Cards should expose side-specific values through the convenience helpers."""
    card = CardSpec.from_dict(demo_project_dict["cards"][0])  # type: ignore[index]

    assert isinstance(card.get_value(CardSide.FRONT, "title"), TextValue)
    assert isinstance(card.get_value(CardSide.BACK, "back_image"), ImageValue)
    assert card.get_value(CardSide.FRONT, "missing") is None
