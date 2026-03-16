"""Tests for deck-level models and cross-reference validation."""

import pytest

from deck_crafter.decks import DeckGlobals, DeckGlobalsOverride, DeckProject, DeckSpec


def test_deck_globals_merge_preserves_unspecified_fields() -> None:
    """Subdeck overrides should only replace explicitly provided fields."""
    merged = DeckGlobals(
        assets_root="assets",
        card_width_mm=63.0,
        card_height_mm=88.0,
        bleed_mm=3.0,
        dpi=300,
    ).merged_with(DeckGlobalsOverride(card_height_mm=120.0))

    assert merged.assets_root == "assets"
    assert merged.card_width_mm == 63.0
    assert merged.card_height_mm == 120.0


def test_deck_spec_creates_default_subdeck_when_missing() -> None:
    """Decks without subdecks should still materialize a render group."""
    deck = DeckSpec.from_dict(
        {
            "id": "deck",
            "globals": {"assets_root": ".", "card_width_mm": 63, "card_height_mm": 88},
            "output_pdf": "build/deck.pdf",
        }
    )

    subdecks = deck.materialized_subdecks({"card_a": object()})  # type: ignore[arg-type]

    assert len(subdecks) == 1
    assert subdecks[0].cards[0].card_id == "card_a"


def test_project_validation_rejects_unknown_card_references(
    demo_project_dict: dict[str, object],
    tmp_path,
) -> None:
    """Projects should fail validation when subdecks reference unknown cards."""
    bad_project = dict(demo_project_dict)
    bad_project["deck"] = dict(demo_project_dict["deck"])  # type: ignore[index]
    bad_project["deck"]["subdecks"] = [  # type: ignore[index]
        {"id": "main", "name": "Main", "cards": [{"card_id": "missing", "copies": 1}]}
    ]

    with pytest.raises(ValueError, match="unknown card"):
        DeckProject.from_dict(bad_project, base_path=tmp_path)
