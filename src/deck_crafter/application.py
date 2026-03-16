"""High-level application helpers used by the CLI and the web interface."""

from __future__ import annotations

from pathlib import Path

from deck_crafter.configuration import ConfigurationLoader
from deck_crafter.decks import DeckProject
from deck_crafter.latex import LatexDeckRenderer
from deck_crafter.layouts import CardSide


def load_project(configuration_file: str | Path) -> DeckProject:
    """Load a project from a YAML configuration file."""
    return ConfigurationLoader.from_file(configuration_file)


def save_project(project: DeckProject, destination: str | Path) -> Path:
    """Save a project to a YAML configuration file."""
    return ConfigurationLoader.dump(project, destination)


def generate_deck(
    configuration_file: str | Path,
    *,
    compile_pdf: bool = True,
) -> list[Path]:
    """Load a project from disk and render it to LaTeX or PDF output."""
    project = load_project(configuration_file)
    renderer = LatexDeckRenderer(template_name=project.deck.latex.main_template)
    return renderer.build(project, compile_pdf=compile_pdf)


def generate_deck_from_project(project: DeckProject, *, compile_pdf: bool = True) -> list[Path]:
    """Render an in-memory project to LaTeX or PDF output."""
    renderer = LatexDeckRenderer(template_name=project.deck.latex.main_template)
    return renderer.build(project, compile_pdf=compile_pdf)


def preview_card(
    project: DeckProject,
    *,
    card_id: str,
    side: str = "front",
    subdeck_id: str | None = None,
) -> dict[str, object]:
    """Build a preview payload for one card side."""
    resolved_side = CardSide.find(side)
    if resolved_side is None:
        raise ValueError(f"Unknown card side: {side!r}")
    renderer = LatexDeckRenderer(template_name=project.deck.latex.main_template)
    return renderer.preview_card(
        project,
        card_id=card_id,
        side=resolved_side,
        subdeck_id=subdeck_id,
    )
