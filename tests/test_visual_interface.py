"""Tests for the local visual interface module."""

from pathlib import Path

from deck_crafter.visual_interface import VisualInterfaceServer, _index_html


def test_visual_interface_server_loads_the_requested_project(
    demo_config_file: Path,
) -> None:
    """The visual interface server should load the configured project on startup."""
    server = VisualInterfaceServer(host="127.0.0.1", port=8765, configuration_file=demo_config_file)

    assert server.configuration_file == demo_config_file.resolve()
    assert server.project.deck.id == "demo_deck"


def test_index_html_exposes_editor_controls() -> None:
    """The served HTML shell should contain the expected editor controls."""
    html = _index_html()

    assert "Deck Crafter" in html
    assert "Generate PDF" in html
    assert "Project YAML" in html
