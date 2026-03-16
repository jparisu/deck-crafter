"""Card instances linking template layouts with concrete values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from deck_crafter.layouts import CardSide
from deck_crafter.utilizing.colors import Color


@dataclass(slots=True)
class CardValue:
    """Base card value bound to one layout node id."""

    @property
    def value_type(self) -> str:
        """Return the serializable value type name."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CardValue:
        """Create a card value by dispatching on its declared type."""
        value_type = str(data.get("type", "")).lower()
        factory_map: dict[str, type[CardValue]] = {
            "text": TextValue,
            "image": ImageValue,
            "color": ColorValue,
        }
        try:
            factory = factory_map[value_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported card value type: {value_type!r}") from exc
        return factory._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> CardValue:
        """Construct one concrete value type from a mapping payload."""
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        """Serialize the value to a plain dictionary."""
        raise NotImplementedError


@dataclass(slots=True)
class TextValue(CardValue):
    """Card value containing rendered text."""

    text: str

    @property
    def value_type(self) -> str:
        """Return the serializable value type name."""
        return "text"

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> TextValue:
        """Build a text value from configuration data."""
        return cls(text=str(data.get("text", "")))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the text value to a plain dictionary."""
        return {"type": self.value_type, "text": self.text}


@dataclass(slots=True)
class ImageValue(CardValue):
    """Card value pointing to an image file."""

    path: str

    @property
    def value_type(self) -> str:
        """Return the serializable value type name."""
        return "image"

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> ImageValue:
        """Build an image value from configuration data."""
        return cls(path=str(data.get("path", "")))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the image value to a plain dictionary."""
        return {"type": self.value_type, "path": self.path}


@dataclass(slots=True)
class ColorValue(CardValue):
    """Card value overriding a color token."""

    color: Color

    @property
    def value_type(self) -> str:
        """Return the serializable value type name."""
        return "color"

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> ColorValue:
        """Build a color value from configuration data."""
        return cls(color=Color.from_value(data.get("color", "white")))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the color value to a plain dictionary."""
        return {"type": self.value_type, "color": str(self.color)}


@dataclass(slots=True)
class CardSpec:
    """Concrete card data used to render a template into output pages."""

    id: str
    name: str
    layout_id: str
    values_front: dict[str, CardValue]
    values_back: dict[str, CardValue]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CardSpec:
        """Create a card from a mapping payload."""
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            layout_id=str(data["layout_id"]),
            values_front=_value_mapping(data.get("values_front", {}), "values_front"),
            values_back=_value_mapping(data.get("values_back", {}), "values_back"),
        )

    def values_for_side(self, side: CardSide) -> dict[str, CardValue]:
        """Return the node values corresponding to one card side."""
        return self.values_front if side is CardSide.FRONT else self.values_back

    def get_value(self, side: CardSide, node_id: str) -> CardValue | None:
        """Return the value bound to one node id on a given side."""
        return self.values_for_side(side).get(node_id)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the card to a plain dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "layout_id": self.layout_id,
            "values_front": {key: value.to_dict() for key, value in self.values_front.items()},
            "values_back": {key: value.to_dict() for key, value in self.values_back.items()},
        }


def _value_mapping(value: object, key: str) -> dict[str, CardValue]:
    """Validate and parse a mapping of node ids to card values."""
    if not isinstance(value, dict):
        raise TypeError(f"Expected '{key}' to be a mapping, got {type(value).__name__}.")
    output: dict[str, CardValue] = {}
    for node_id, payload in value.items():
        if not isinstance(payload, dict):
            raise TypeError(f"Expected card value for '{node_id}' to be a mapping.")
        output[str(node_id)] = CardValue.from_dict(payload)
    return output
