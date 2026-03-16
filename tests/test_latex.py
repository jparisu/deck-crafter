"""Tests for preview generation and LaTeX document rendering."""

from deck_crafter.latex import LatexDeckRenderer
from deck_crafter.layouts import CardSide


def test_preview_card_resolves_text_and_images(demo_project) -> None:
    """Preview models should expose resolved rectangles and bound values."""
    renderer = LatexDeckRenderer()

    preview = renderer.preview_card(demo_project, card_id="demo_card", side=CardSide.FRONT)

    assert preview["card_id"] == "demo_card"
    nodes = preview["nodes"]
    assert any(node["node_type"] == "image" for node in nodes)  # type: ignore[index]
    assert any(node.get("text") == "Demo Title" for node in nodes)  # type: ignore[union-attr]


def test_render_tex_contains_expected_latex_fragments(demo_project) -> None:
    """The rendered document should contain text, images, and page markup."""
    renderer = LatexDeckRenderer()

    tex = renderer.render_tex(
        demo_project,
        deck_globals=demo_project.deck.globals,
        subdeck=demo_project.deck.subdecks[0],
    )

    assert "\\documentclass{article}" in tex
    assert "\\includegraphics" in tex
    assert "Demo Title" in tex
    assert "\\newpage" in tex
