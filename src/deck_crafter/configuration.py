"""Configuration loading, YAML reference resolution, and project serialization."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import yaml

from deck_crafter.decks import DeckProject
from deck_crafter.utilizing.configuring.YamlHandler import YamlHandler


class ConfigurationLoader:
    """Load and save deck projects from YAML files or dictionaries."""

    @classmethod
    def from_file(cls, configuration_file: str | Path) -> DeckProject:
        """Load a project from a YAML file."""
        normalized_path = Path(configuration_file).expanduser().resolve()
        handler = YamlHandler.from_file(normalized_path)
        combined = handler.combine()
        resolved = cls.resolve_references(combined)
        return DeckProject.from_dict(resolved, base_path=normalized_path.parent)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, base_path: str | Path | None = None) -> DeckProject:
        """Load a project from a dictionary payload."""
        normalized_base = None if base_path is None else Path(base_path).expanduser().resolve()
        source_path = normalized_base
        if normalized_base is not None and normalized_base.is_dir():
            source_path = normalized_base / "__in_memory__.yaml"
        handler = YamlHandler.from_dict(data, source_path=source_path)
        combined = handler.combine()
        resolved = cls.resolve_references(combined)
        return DeckProject.from_dict(resolved, base_path=normalized_base)

    @classmethod
    def dump(cls, project: DeckProject, destination: str | Path) -> Path:
        """Write a project to YAML."""
        normalized_path = Path(destination).expanduser().resolve()
        normalized_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_path.write_text(
            yaml.safe_dump(project.to_dict(), sort_keys=False),
            encoding="utf-8",
        )
        return normalized_path

    @classmethod
    def to_yaml(cls, project: DeckProject) -> str:
        """Serialize a project to YAML text."""
        return yaml.safe_dump(project.to_dict(), sort_keys=False)

    @classmethod
    def resolve_references(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Resolve ``$ref`` mappings inside a raw configuration payload."""
        root = deepcopy(data)

        def resolve_node(node: Any) -> Any:
            if isinstance(node, list):
                return [resolve_node(item) for item in node]
            if isinstance(node, dict):
                if set(node) == {"$ref"}:
                    return resolve_node(deepcopy(cls.lookup_reference(root, str(node["$ref"]))))
                return {key: resolve_node(value) for key, value in node.items()}
            return node

        return cast(dict[str, Any], resolve_node(root))

    @classmethod
    def lookup_reference(cls, data: dict[str, Any], reference: str) -> Any:
        """Resolve one dotted-path reference inside the configuration tree."""
        tokens = [token for token in reference.split(".") if token]
        if not tokens:
            raise ValueError("Reference cannot be empty.")

        current: Any = data
        for index, token in enumerate(tokens):
            if isinstance(current, dict) and token in current:
                current = current[token]
                continue
            if isinstance(current, list):
                current = _find_list_item(current, token)
                continue
            if index == 0:
                current = _find_root_object(data, token)
                continue
            raise KeyError(f"Cannot resolve reference {reference!r} at token {token!r}.")
        return current


def create_default_project() -> DeckProject:
    """Return a small in-memory project used by the visual interface."""
    return ConfigurationLoader.from_dict(
        {
            "schema_version": 1,
            "layouts": [
                {
                    "id": "default_layout",
                    "name": "Default Layout",
                    "front_root": {
                        "type": "container",
                        "id": "front_root",
                        "side": "front",
                        "rect": _full_rect(),
                        "children": [
                            {
                                "type": "color",
                                "id": "background",
                                "side": "front",
                                "rect": _full_rect(),
                                "color": "#f6f1e7",
                            },
                            {
                                "type": "text",
                                "id": "title",
                                "side": "front",
                                "rect": _rect(0.08, 0.08, 0.84, 0.15),
                                "font_size_pt": 18,
                                "font_color": "#222222",
                                "align": "center",
                                "wrap": False,
                            },
                            {
                                "type": "text",
                                "id": "rules",
                                "side": "front",
                                "rect": _rect(0.08, 0.30, 0.84, 0.55),
                                "font_size_pt": 11,
                                "font_color": "#222222",
                                "align": "left",
                                "wrap": True,
                            },
                        ],
                    },
                    "back_root": {
                        "type": "container",
                        "id": "back_root",
                        "side": "back",
                        "rect": _full_rect(),
                        "children": [
                            {
                                "type": "color",
                                "id": "back_background",
                                "side": "back",
                                "rect": _full_rect(),
                                "color": "#1f2933",
                            },
                            {
                                "type": "text",
                                "id": "back_label",
                                "side": "back",
                                "rect": _rect(0.08, 0.72, 0.84, 0.15),
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
                    "id": "default_card",
                    "name": "Default Card",
                    "layout_id": "default_layout",
                    "values_front": {
                        "title": {"type": "text", "text": "Deck Crafter"},
                        "rules": {
                            "type": "text",
                            "text": (
                                "Edit this card in the local web interface, then save it as YAML."
                            ),
                        },
                    },
                    "values_back": {
                        "back_label": {"type": "text", "text": "Default Back"},
                    },
                }
            ],
            "deck": {
                "id": "default_deck",
                "name": "Default Deck",
                "globals": {
                    "assets_root": ".",
                    "card_width_mm": 63,
                    "card_height_mm": 88,
                    "bleed_mm": 3,
                    "dpi": 300,
                },
                "output_pdf": "./build/default_deck.pdf",
                "pdf_per_subdeck": False,
                "latex": {"engine": "latexmk", "main_template": "deck.tex.template"},
                "subdecks": [
                    {
                        "id": "default",
                        "name": "Default",
                        "cards": [{"card_id": "default_card", "copies": 1}],
                    }
                ],
            },
        }
    )


def _find_root_object(data: dict[str, Any], token: str) -> Any:
    """Search top-level lists for an item matching the reference token."""
    for _key, value in data.items():
        if isinstance(value, list):
            try:
                return _find_list_item(value, token)
            except KeyError:
                continue
    raise KeyError(f"Unknown reference root token {token!r}.")


def _find_list_item(items: list[Any], token: str) -> Any:
    """Return the list item whose ``id`` matches the requested token."""
    for item in items:
        if isinstance(item, dict) and str(item.get("id")) == token:
            return item
    raise KeyError(f"Could not find reference target {token!r} in list.")


def _full_rect() -> dict[str, Any]:
    """Return a relative rectangle covering the full card."""
    return _rect(0.0, 0.0, 1.0, 1.0)


def _rect(x: float, y: float, width: float, height: float) -> dict[str, Any]:
    """Return a relative rectangle mapping."""
    return {
        "x": {"mode": "relative", "value": x, "ref": "card", "unit": "mm"},
        "y": {"mode": "relative", "value": y, "ref": "card", "unit": "mm"},
        "width": {"mode": "relative", "value": width, "ref": "card", "unit": "mm"},
        "height": {"mode": "relative", "value": height, "ref": "card", "unit": "mm"},
        "anchor": "top_left",
    }
