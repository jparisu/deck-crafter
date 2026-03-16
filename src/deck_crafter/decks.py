"""Deck-level models describing render settings and output structure."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from deck_crafter.cards import CardSpec
from deck_crafter.geometry import ResolvedRect
from deck_crafter.layouts import CardLayoutTemplate


@dataclass(slots=True)
class DeckGlobals:
    """Global output settings shared across the rendered deck."""

    assets_root: str = "."
    card_width_mm: float = 63.0
    card_height_mm: float = 88.0
    bleed_mm: float = 3.0
    dpi: int = 300

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeckGlobals:
        """Create deck globals from a mapping payload."""
        return cls(
            assets_root=str(data.get("assets_root", ".")),
            card_width_mm=float(data.get("card_width_mm", 63.0)),
            card_height_mm=float(data.get("card_height_mm", 88.0)),
            bleed_mm=float(data.get("bleed_mm", 3.0)),
            dpi=int(data.get("dpi", 300)),
        )

    def merged_with(self, override: DeckGlobalsOverride | None) -> DeckGlobals:
        """Return a copy of the globals updated by a partial override."""
        if override is None:
            return self
        return DeckGlobals(
            assets_root=self.assets_root if override.assets_root is None else override.assets_root,
            card_width_mm=(
                self.card_width_mm if override.card_width_mm is None else override.card_width_mm
            ),
            card_height_mm=(
                self.card_height_mm if override.card_height_mm is None else override.card_height_mm
            ),
            bleed_mm=self.bleed_mm if override.bleed_mm is None else override.bleed_mm,
            dpi=self.dpi if override.dpi is None else override.dpi,
        )

    def card_rect(self) -> ResolvedRect:
        """Return the full card rectangle in millimetres."""
        return ResolvedRect(0.0, 0.0, self.card_width_mm, self.card_height_mm)

    def assets_directory(self, base_path: Path | None) -> Path:
        """Resolve the configured asset root to an absolute path."""
        candidate = Path(self.assets_root)
        if candidate.is_absolute():
            return candidate
        if base_path is None:
            return (Path.cwd() / candidate).resolve()
        return (base_path / candidate).resolve()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the globals to a plain dictionary."""
        return {
            "assets_root": self.assets_root,
            "card_width_mm": self.card_width_mm,
            "card_height_mm": self.card_height_mm,
            "bleed_mm": self.bleed_mm,
            "dpi": self.dpi,
        }


@dataclass(slots=True)
class DeckGlobalsOverride:
    """Optional override of deck globals used by subdecks."""

    assets_root: str | None = None
    card_width_mm: float | None = None
    card_height_mm: float | None = None
    bleed_mm: float | None = None
    dpi: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeckGlobalsOverride:
        """Create a partial override from a mapping payload."""
        return cls(
            assets_root=None if "assets_root" not in data else str(data["assets_root"]),
            card_width_mm=(None if "card_width_mm" not in data else float(data["card_width_mm"])),
            card_height_mm=(
                None if "card_height_mm" not in data else float(data["card_height_mm"])
            ),
            bleed_mm=None if "bleed_mm" not in data else float(data["bleed_mm"]),
            dpi=None if "dpi" not in data else int(data["dpi"]),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize only the fields explicitly set in the override."""
        payload: dict[str, Any] = {}
        if self.assets_root is not None:
            payload["assets_root"] = self.assets_root
        if self.card_width_mm is not None:
            payload["card_width_mm"] = self.card_width_mm
        if self.card_height_mm is not None:
            payload["card_height_mm"] = self.card_height_mm
        if self.bleed_mm is not None:
            payload["bleed_mm"] = self.bleed_mm
        if self.dpi is not None:
            payload["dpi"] = self.dpi
        return payload


@dataclass(slots=True)
class LatexOptions:
    """Configuration for the LaTeX compilation step."""

    engine: str = "latexmk"
    main_template: str = "deck.tex.template"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LatexOptions:
        """Create LaTeX options from a mapping payload."""
        return cls(
            engine=str(data.get("engine", "latexmk")),
            main_template=str(data.get("main_template", "deck.tex.template")),
        )

    def to_dict(self) -> dict[str, str]:
        """Serialize the options to a plain dictionary."""
        return {
            "engine": self.engine,
            "main_template": self.main_template,
        }


@dataclass(slots=True)
class CardEntry:
    """One card reference inside a subdeck."""

    card_id: str
    copies: int = 1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CardEntry:
        """Create a card entry from a mapping payload."""
        copies = int(data.get("copies", 1))
        if copies < 1:
            raise ValueError("Card copies must be at least 1.")
        return cls(card_id=str(data["card_id"]), copies=copies)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the card entry to a plain dictionary."""
        return {"card_id": self.card_id, "copies": self.copies}


@dataclass(slots=True)
class SubDeckSpec:
    """A logical subset of the deck rendered with optional overrides."""

    id: str
    name: str
    overrides: DeckGlobalsOverride | None = None
    cards: list[CardEntry] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubDeckSpec:
        """Create a subdeck from a mapping payload."""
        raw_overrides = data.get("overrides")
        overrides = None
        if isinstance(raw_overrides, dict):
            overrides = DeckGlobalsOverride.from_dict(raw_overrides)
        raw_cards = data.get("cards", [])
        if not isinstance(raw_cards, list):
            raise TypeError("Subdeck cards must be a list.")
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            overrides=overrides,
            cards=[CardEntry.from_dict(_expect_mapping(card, "card")) for card in raw_cards],
        )

    def expanded_card_ids(self) -> list[str]:
        """Return card ids repeated according to their copy count."""
        output: list[str] = []
        for entry in self.cards:
            output.extend([entry.card_id] * entry.copies)
        return output

    def to_dict(self) -> dict[str, Any]:
        """Serialize the subdeck to a plain dictionary."""
        payload: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "cards": [entry.to_dict() for entry in self.cards],
        }
        if self.overrides is not None:
            payload["overrides"] = self.overrides.to_dict()
        return payload


@dataclass(slots=True)
class DeckSpec:
    """Full deck settings including output path and per-subdeck structure."""

    id: str
    name: str
    globals: DeckGlobals
    output_pdf: str
    pdf_per_subdeck: bool = False
    latex: LatexOptions = field(default_factory=LatexOptions)
    subdecks: list[SubDeckSpec] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeckSpec:
        """Create a deck specification from a mapping payload."""
        raw_subdecks = data.get("subdecks", [])
        if not isinstance(raw_subdecks, list):
            raise TypeError("Deck subdecks must be a list.")
        raw_latex = data.get("latex", {})
        if not isinstance(raw_latex, dict):
            raise TypeError("Deck latex configuration must be a mapping.")
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            globals=DeckGlobals.from_dict(_expect_mapping(data.get("globals"), "globals")),
            output_pdf=str(data.get("output_pdf", "./build/deck.pdf")),
            pdf_per_subdeck=bool(data.get("pdf_per_subdeck", False)),
            latex=LatexOptions.from_dict(raw_latex),
            subdecks=[
                SubDeckSpec.from_dict(_expect_mapping(subdeck, "subdeck"))
                for subdeck in raw_subdecks
            ],
        )

    def materialized_subdecks(self, cards: dict[str, CardSpec]) -> list[SubDeckSpec]:
        """Return the deck subdecks, creating a default one when absent."""
        if self.subdecks:
            return self.subdecks
        return [
            SubDeckSpec(
                id=f"{self.id}_default",
                name=f"{self.name} Default",
                cards=[CardEntry(card_id=card_id, copies=1) for card_id in cards],
            )
        ]

    def output_path(self, *, base_path: Path | None, subdeck: SubDeckSpec | None = None) -> Path:
        """Resolve the target PDF path for one output artifact."""
        candidate = Path(self.output_pdf)
        if not candidate.is_absolute():
            candidate = ((base_path or Path.cwd()) / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if subdeck is None or not self.pdf_per_subdeck:
            return candidate
        return candidate.with_name(f"{candidate.stem}_{subdeck.id}{candidate.suffix}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the deck specification to a plain dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "globals": self.globals.to_dict(),
            "output_pdf": self.output_pdf,
            "pdf_per_subdeck": self.pdf_per_subdeck,
            "latex": self.latex.to_dict(),
            "subdecks": [subdeck.to_dict() for subdeck in self.subdecks],
        }


@dataclass(slots=True)
class DeckProject:
    """Top-level project composed of layouts, cards, and one deck spec."""

    schema_version: int
    layouts: dict[str, CardLayoutTemplate]
    cards: dict[str, CardSpec]
    deck: DeckSpec
    base_path: Path | None = None

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        base_path: Path | None = None,
    ) -> DeckProject:
        """Create a project from a mapping payload."""
        raw_layouts = data.get("layouts", [])
        raw_cards = data.get("cards", [])
        if not isinstance(raw_layouts, list):
            raise TypeError("Project layouts must be a list.")
        if not isinstance(raw_cards, list):
            raise TypeError("Project cards must be a list.")
        layouts = [
            CardLayoutTemplate.from_dict(_expect_mapping(layout, "layout"))
            for layout in raw_layouts
        ]
        cards = [CardSpec.from_dict(_expect_mapping(card, "card")) for card in raw_cards]
        project = cls(
            schema_version=int(data.get("schema_version", 1)),
            layouts={layout.id: layout for layout in layouts},
            cards={card.id: card for card in cards},
            deck=DeckSpec.from_dict(_expect_mapping(data.get("deck"), "deck")),
            base_path=base_path.resolve() if base_path is not None else None,
        )
        project.validate()
        return project

    def validate(self) -> None:
        """Validate cross-references inside the project."""
        for card in self.cards.values():
            if card.layout_id not in self.layouts:
                raise ValueError(f"Card {card.id!r} references unknown layout {card.layout_id!r}.")
        for subdeck in self.deck.materialized_subdecks(self.cards):
            for entry in subdeck.cards:
                if entry.card_id not in self.cards:
                    raise ValueError(
                        f"Subdeck {subdeck.id!r} references unknown card {entry.card_id!r}."
                    )

    def get_layout(self, layout_id: str) -> CardLayoutTemplate:
        """Return one registered card layout by id."""
        return self.layouts[layout_id]

    def get_card(self, card_id: str) -> CardSpec:
        """Return one registered card by id."""
        return self.cards[card_id]

    def globals_for_subdeck(self, subdeck: SubDeckSpec | None) -> DeckGlobals:
        """Return the effective deck globals for one subdeck."""
        if subdeck is None:
            return self.deck.globals
        return self.deck.globals.merged_with(subdeck.overrides)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the project to a plain dictionary."""
        return {
            "schema_version": self.schema_version,
            "layouts": [layout.to_dict() for layout in self.layouts.values()],
            "cards": [card.to_dict() for card in self.cards.values()],
            "deck": self.deck.to_dict(),
        }


def _expect_mapping(value: object, key: str) -> dict[str, Any]:
    """Validate that a nested deck field is represented as a mapping."""
    if not isinstance(value, dict):
        raise TypeError(f"Expected '{key}' to be a mapping, got {type(value).__name__}.")
    return value
