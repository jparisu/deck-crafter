"""Top-level package for Deck Crafter."""

from deck_crafter._version import __version__
from deck_crafter.application import generate_deck, generate_deck_from_project, load_project
from deck_crafter.visual_interface import serve_visual_interface

__all__ = [
    "__version__",
    "generate_deck",
    "generate_deck_from_project",
    "load_project",
    "serve_visual_interface",
]
