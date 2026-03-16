"""Pytest fixtures shared across the Deck Crafter test suite."""

import shutil
import sys
from pathlib import Path

import pytest
import yaml

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from deck_crafter.configuration import ConfigurationLoader  # noqa: E402


@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"value": 42, "data": [1, 2, 3, 4, 5]}


@pytest.fixture
def sample_value():
    """Provide a sample value for tests."""
    return 10


@pytest.fixture
def demo_project_dict(tmp_path: Path) -> dict[str, object]:
    """Provide a compact but fully valid Deck Crafter project configuration."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    repo_root = Path(__file__).resolve().parent.parent
    shutil.copy(repo_root / "resources" / "background.jpg", assets_dir / "background.jpg")
    shutil.copy(repo_root / "resources" / "back_side.jpeg", assets_dir / "back_side.jpeg")

    return {
        "schema_version": 1,
        "layouts": [
            {
                "id": "demo_layout",
                "name": "Demo Layout",
                "front_root": {
                    "type": "container",
                    "id": "front_root",
                    "side": "front",
                    "rect": _rect(0.0, 0.0, 1.0, 1.0),
                    "children": [
                        {
                            "type": "image",
                            "id": "background",
                            "side": "front",
                            "rect": _rect(0.0, 0.0, 1.0, 1.0),
                            "fit": "cover",
                            "crop_anchor": "center",
                            "clip": True,
                        },
                        {
                            "type": "text",
                            "id": "title",
                            "side": "front",
                            "rect": _rect(0.08, 0.08, 0.84, 0.16),
                            "font_size_pt": 18,
                            "font_color": "#ffffff",
                            "align": "center",
                            "wrap": False,
                        },
                        {
                            "type": "text",
                            "id": "body",
                            "side": "front",
                            "rect": _rect(0.08, 0.30, 0.84, 0.50),
                            "font_size_pt": 11,
                            "font_color": "#ffffff",
                            "align": "left",
                            "wrap": True,
                        },
                    ],
                },
                "back_root": {
                    "type": "container",
                    "id": "back_root",
                    "side": "back",
                    "rect": _rect(0.0, 0.0, 1.0, 1.0),
                    "children": [
                        {
                            "type": "image",
                            "id": "back_image",
                            "side": "back",
                            "rect": _rect(0.0, 0.0, 1.0, 1.0),
                            "fit": "cover",
                            "crop_anchor": "center",
                            "clip": True,
                        },
                        {
                            "type": "text",
                            "id": "back_label",
                            "side": "back",
                            "rect": _rect(0.08, 0.72, 0.84, 0.16),
                            "font_size_pt": 14,
                            "font_color": "#ffffff",
                            "align": "center",
                            "wrap": False,
                        },
                    ],
                },
            }
        ],
        "cards": [
            {
                "id": "demo_card",
                "name": "Demo Card",
                "layout_id": "demo_layout",
                "values_front": {
                    "background": {"type": "image", "path": "background.jpg"},
                    "title": {"type": "text", "text": "Demo Title"},
                    "body": {"type": "text", "text": "Line one\\nLine two"},
                },
                "values_back": {
                    "back_image": {"type": "image", "path": "back_side.jpeg"},
                    "back_label": {"type": "text", "text": "Back"},
                },
            }
        ],
        "deck": {
            "id": "demo_deck",
            "name": "Demo Deck",
            "globals": {
                "assets_root": "assets",
                "card_width_mm": 63,
                "card_height_mm": 88,
                "bleed_mm": 3,
                "dpi": 300,
            },
            "output_pdf": "build/demo_deck.pdf",
            "pdf_per_subdeck": False,
            "latex": {"engine": "latexmk", "main_template": "deck.tex.template"},
            "subdecks": [
                {
                    "id": "main",
                    "name": "Main",
                    "cards": [{"card_id": "demo_card", "copies": 1}],
                }
            ],
        },
    }


@pytest.fixture
def demo_project(demo_project_dict: dict[str, object], tmp_path: Path):
    """Provide a parsed in-memory project."""
    return ConfigurationLoader.from_dict(demo_project_dict, base_path=tmp_path)


@pytest.fixture
def demo_config_file(demo_project_dict: dict[str, object], tmp_path: Path) -> Path:
    """Write a demo configuration file to disk and return its path."""
    path = tmp_path / "demo_project.yaml"
    path.write_text(yaml.safe_dump(demo_project_dict, sort_keys=False), encoding="utf-8")
    return path


def _rect(x: float, y: float, width: float, height: float) -> dict[str, object]:
    """Return a relative rectangle mapping used by several fixtures."""
    return {
        "x": {"mode": "relative", "value": x, "ref": "card", "unit": "mm"},
        "y": {"mode": "relative", "value": y, "ref": "card", "unit": "mm"},
        "width": {"mode": "relative", "value": width, "ref": "card", "unit": "mm"},
        "height": {"mode": "relative", "value": height, "ref": "card", "unit": "mm"},
        "anchor": "top_left",
    }
