"""Layout templates describing where card elements should be placed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from deck_crafter.geometry import Measure, Rect, ResolvedRect
from deck_crafter.utilizing.colors import Color
from deck_crafter.utilizing.structuring.GenericEnumRegistry import GenericEnumRegistry


class CardSide(GenericEnumRegistry):
    """Logical side of a card."""

    FRONT = "front"
    BACK = "back"


@dataclass(slots=True)
class LayoutNode:
    """Base layout node shared by all renderable card elements."""

    id: str
    rect: Rect
    side: CardSide
    z_index: int = 0
    opacity: float = 1.0
    rotation_deg: float = 0.0

    @property
    def node_type(self) -> str:
        """Return the serializable node type name."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LayoutNode:
        """Create a layout node by dispatching on its declared type."""
        node_type = str(data.get("type", "")).lower()
        factory_map: dict[str, type[LayoutNode]] = {
            "image": ImageLayout,
            "text": TextLayout,
            "color": ColorLayout,
            "container": ContainerLayout,
            "bleed": BleedLayout,
        }
        try:
            factory = factory_map[node_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported layout node type: {node_type!r}") from exc
        return factory._from_dict(data)

    @classmethod
    def _common_kwargs(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Extract the fields shared by all node types."""
        return {
            "id": str(data["id"]),
            "rect": Rect.from_dict(_expect_mapping(data.get("rect"), "rect")),
            "side": CardSide.find(str(data.get("side", CardSide.FRONT.value))),
            "z_index": int(data.get("z_index", 0)),
            "opacity": float(data.get("opacity", 1.0)),
            "rotation_deg": float(data.get("rotation_deg", 0.0)),
        }

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> LayoutNode:
        """Construct one concrete node type from a mapping payload."""
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node to a plain dictionary."""
        return {
            "type": self.node_type,
            "id": self.id,
            "side": self.side.value,
            "rect": _rect_to_dict(self.rect),
            "z_index": self.z_index,
            "opacity": self.opacity,
            "rotation_deg": self.rotation_deg,
        }


@dataclass(slots=True)
class ImageLayout(LayoutNode):
    """Layout for an image rendered inside a card rectangle."""

    fit: str = "cover"
    crop_anchor: str = "center"
    clip: bool = True

    @property
    def node_type(self) -> str:
        """Return the serializable node type name."""
        return "image"

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> ImageLayout:
        """Build an image node from configuration data."""
        return cls(
            **cls._common_kwargs(data),
            fit=str(data.get("fit", "cover")),
            crop_anchor=str(data.get("crop_anchor", "center")),
            clip=bool(data.get("clip", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the image node to a plain dictionary."""
        payload = LayoutNode.to_dict(self)
        payload.update(
            {
                "fit": self.fit,
                "crop_anchor": self.crop_anchor,
                "clip": self.clip,
            }
        )
        return payload


@dataclass(slots=True)
class TextLayout(LayoutNode):
    """Layout for a text block rendered on a card."""

    font_family: str = "Helvetica"
    font_size_pt: float = 12.0
    font_color: Color = field(default_factory=lambda: Color("black"))
    align: str = "left"
    wrap: bool = True
    line_height: float = 1.2

    @property
    def node_type(self) -> str:
        """Return the serializable node type name."""
        return "text"

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> TextLayout:
        """Build a text node from configuration data."""
        return cls(
            **cls._common_kwargs(data),
            font_family=str(data.get("font_family", "Helvetica")),
            font_size_pt=float(data.get("font_size_pt", 12.0)),
            font_color=Color.from_value(data.get("font_color", "black")),
            align=str(data.get("align", "left")),
            wrap=bool(data.get("wrap", True)),
            line_height=float(data.get("line_height", 1.2)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the text node to a plain dictionary."""
        payload = LayoutNode.to_dict(self)
        payload.update(
            {
                "font_family": self.font_family,
                "font_size_pt": self.font_size_pt,
                "font_color": str(self.font_color),
                "align": self.align,
                "wrap": self.wrap,
                "line_height": self.line_height,
            }
        )
        return payload


@dataclass(slots=True)
class ColorLayout(LayoutNode):
    """Layout for a solid color rectangle."""

    color: Color = field(default_factory=lambda: Color("white"))

    @property
    def node_type(self) -> str:
        """Return the serializable node type name."""
        return "color"

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> ColorLayout:
        """Build a color node from configuration data."""
        return cls(
            **cls._common_kwargs(data),
            color=Color.from_value(data.get("color", "white")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the color node to a plain dictionary."""
        payload = LayoutNode.to_dict(self)
        payload["color"] = str(self.color)
        return payload


@dataclass(slots=True)
class ContainerLayout(LayoutNode):
    """Layout grouping children relative to a shared rectangle."""

    children: list[LayoutNode] = field(default_factory=list)
    padding_left: Measure = field(default_factory=Measure)
    padding_top: Measure = field(default_factory=Measure)
    padding_right: Measure = field(default_factory=Measure)
    padding_bottom: Measure = field(default_factory=Measure)

    @property
    def node_type(self) -> str:
        """Return the serializable node type name."""
        return "container"

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> ContainerLayout:
        """Build a container node from configuration data."""
        children = [
            LayoutNode.from_dict(child)
            for child in _expect_sequence_of_mappings(data.get("children", []), "children")
        ]
        return cls(
            **cls._common_kwargs(data),
            children=children,
            padding_left=_measure_from_data(data, "padding_left"),
            padding_top=_measure_from_data(data, "padding_top"),
            padding_right=_measure_from_data(data, "padding_right"),
            padding_bottom=_measure_from_data(data, "padding_bottom"),
        )

    def content_rect(self, resolved_rect: ResolvedRect, *, card_rect: ResolvedRect) -> ResolvedRect:
        """Return the rectangle available to the container children."""
        return resolved_rect.inset(
            self.padding_left.resolve(card_size=card_rect.width, parent_size=resolved_rect.width),
            self.padding_top.resolve(card_size=card_rect.height, parent_size=resolved_rect.height),
            self.padding_right.resolve(card_size=card_rect.width, parent_size=resolved_rect.width),
            self.padding_bottom.resolve(
                card_size=card_rect.height, parent_size=resolved_rect.height
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the container node to a plain dictionary."""
        payload = LayoutNode.to_dict(self)
        payload.update(
            {
                "children": [child.to_dict() for child in self.children],
                "padding_left": _measure_to_dict(self.padding_left),
                "padding_top": _measure_to_dict(self.padding_top),
                "padding_right": _measure_to_dict(self.padding_right),
                "padding_bottom": _measure_to_dict(self.padding_bottom),
            }
        )
        return payload


@dataclass(slots=True)
class BleedLayout(LayoutNode):
    """Layout instructing the renderer to draw a bleed or cut guide."""

    bleed_mm: float | None = None
    stroke_color: Color = field(default_factory=lambda: Color("black"))
    stroke_width_pt: float = 0.4

    @property
    def node_type(self) -> str:
        """Return the serializable node type name."""
        return "bleed"

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> BleedLayout:
        """Build a bleed node from configuration data."""
        raw_bleed = data.get("bleed_mm")
        return cls(
            **cls._common_kwargs(data),
            bleed_mm=None if raw_bleed is None else float(raw_bleed),
            stroke_color=Color.from_value(data.get("stroke_color", "black")),
            stroke_width_pt=float(data.get("stroke_width_pt", 0.4)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the bleed node to a plain dictionary."""
        payload = LayoutNode.to_dict(self)
        payload.update(
            {
                "bleed_mm": self.bleed_mm,
                "stroke_color": str(self.stroke_color),
                "stroke_width_pt": self.stroke_width_pt,
            }
        )
        return payload


@dataclass(slots=True)
class CardLayoutTemplate:
    """A full card template with one root layout per side."""

    id: str
    name: str
    front_root: ContainerLayout
    back_root: ContainerLayout

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CardLayoutTemplate:
        """Create a card template from a mapping payload."""
        front_root = LayoutNode.from_dict(_expect_mapping(data.get("front_root"), "front_root"))
        back_root = LayoutNode.from_dict(_expect_mapping(data.get("back_root"), "back_root"))
        if not isinstance(front_root, ContainerLayout):
            raise TypeError("front_root must be a container layout.")
        if not isinstance(back_root, ContainerLayout):
            raise TypeError("back_root must be a container layout.")
        template = cls(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            front_root=front_root,
            back_root=back_root,
        )
        template._ensure_unique_ids()
        return template

    def root_for_side(self, side: CardSide) -> ContainerLayout:
        """Return the root layout for the selected card side."""
        return self.front_root if side is CardSide.FRONT else self.back_root

    def find_node(self, side: CardSide, node_id: str) -> LayoutNode | None:
        """Find a node by identifier on one side of the card."""
        for node in self.iter_nodes(side):
            if node.id == node_id:
                return node
        return None

    def iter_nodes(self, side: CardSide) -> list[LayoutNode]:
        """Flatten all nodes on one side of the template."""
        nodes: list[LayoutNode] = []

        def visit(node: LayoutNode) -> None:
            nodes.append(node)
            if isinstance(node, ContainerLayout):
                for child in node.children:
                    visit(child)

        visit(self.root_for_side(side))
        return nodes

    def to_dict(self) -> dict[str, Any]:
        """Serialize the template to a plain dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "front_root": self.front_root.to_dict(),
            "back_root": self.back_root.to_dict(),
        }

    def _ensure_unique_ids(self) -> None:
        """Validate that node ids are unique per side."""
        for side in (CardSide.FRONT, CardSide.BACK):
            seen: set[str] = set()
            for node in self.iter_nodes(side):
                if node.id in seen:
                    raise ValueError(f"Duplicate node id {node.id!r} in layout {self.id!r}.")
                seen.add(node.id)


def _measure_from_data(data: dict[str, Any], key: str) -> Measure:
    """Parse a padding measure from a node mapping."""
    raw_value = data.get(key, {"mode": "absolute", "value": 0.0, "unit": "mm", "ref": "parent"})
    if not isinstance(raw_value, dict):
        raise TypeError(f"Expected '{key}' to be a mapping, got {type(raw_value).__name__}.")
    return Measure.from_dict(raw_value)


def _rect_to_dict(rect: Rect) -> dict[str, Any]:
    """Serialize a rectangle into its dictionary representation."""
    return {
        "x": _measure_to_dict(rect.x),
        "y": _measure_to_dict(rect.y),
        "width": _measure_to_dict(rect.width),
        "height": _measure_to_dict(rect.height),
        "anchor": rect.anchor,
    }


def _measure_to_dict(measure: Any) -> dict[str, Any]:
    """Serialize a measure into its dictionary representation."""
    return {
        "mode": measure.mode.value,
        "value": measure.value,
        "unit": measure.unit,
        "ref": measure.ref.value,
    }


def _expect_mapping(value: object, key: str) -> dict[str, Any]:
    """Validate that a nested layout field is represented as a mapping."""
    if not isinstance(value, dict):
        raise TypeError(f"Expected '{key}' to be a mapping, got {type(value).__name__}.")
    return value


def _expect_sequence_of_mappings(value: object, key: str) -> list[dict[str, Any]]:
    """Validate that a nested layout field is a list of mappings."""
    if not isinstance(value, list):
        raise TypeError(f"Expected '{key}' to be a list, got {type(value).__name__}.")
    output: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise TypeError(f"Expected all items in '{key}' to be mappings.")
        output.append(item)
    return output
