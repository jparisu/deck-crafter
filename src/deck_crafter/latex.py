"""Preview generation, LaTeX rendering, and PDF compilation helpers."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from string import Template

from deck_crafter.cards import CardSpec, ColorValue, ImageValue, TextValue
from deck_crafter.decks import DeckGlobals, DeckProject, SubDeckSpec
from deck_crafter.geometry import ResolvedRect
from deck_crafter.layouts import (
    BleedLayout,
    CardSide,
    ColorLayout,
    ContainerLayout,
    ImageLayout,
    LayoutNode,
    TextLayout,
)


@dataclass(slots=True)
class PreviewNode:
    """Resolved layout node used by the web UI preview and tests."""

    id: str
    node_type: str
    side: str
    rect: ResolvedRect
    z_index: int
    opacity: float
    text: str | None = None
    image_path: str | None = None
    color: str | None = None
    meta: dict[str, str] | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize the preview node for JSON responses."""
        payload: dict[str, object] = {
            "id": self.id,
            "node_type": self.node_type,
            "side": self.side,
            "rect": self.rect.to_dict(),
            "z_index": self.z_index,
            "opacity": self.opacity,
        }
        if self.text is not None:
            payload["text"] = self.text
        if self.image_path is not None:
            payload["image_path"] = self.image_path
        if self.color is not None:
            payload["color"] = self.color
        if self.meta is not None:
            payload["meta"] = self.meta
        return payload


class LatexDeckRenderer:
    """Render projects to previews, LaTeX documents, and compiled PDF files."""

    def __init__(self, template_name: str = "deck.tex.template") -> None:
        """Store the default LaTeX template used when rendering documents."""
        self.template_name = template_name

    def preview_card(
        self,
        project: DeckProject,
        *,
        card_id: str,
        side: CardSide,
        subdeck_id: str | None = None,
    ) -> dict[str, object]:
        """Build a preview model for one card side."""
        card = project.get_card(card_id)
        subdeck = self._select_subdeck(project, card_id=card_id, subdeck_id=subdeck_id)
        deck_globals = project.globals_for_subdeck(subdeck)
        nodes = self._resolve_preview_nodes(
            project=project,
            card=card,
            side=side,
            deck_globals=deck_globals,
        )
        return {
            "card_id": card.id,
            "card_name": card.name,
            "layout_id": card.layout_id,
            "side": side.value,
            "card_rect": deck_globals.card_rect().to_dict(),
            "nodes": [node.to_dict() for node in nodes],
        }

    def build(self, project: DeckProject, *, compile_pdf: bool = True) -> list[Path]:
        """Render one project to LaTeX and optionally compile it to PDF."""
        outputs: list[Path] = []
        subdecks = project.deck.materialized_subdecks(project.cards)
        if project.deck.pdf_per_subdeck:
            for subdeck in subdecks:
                tex_path = self.write_tex(project, subdeck=subdeck)
                if compile_pdf:
                    outputs.append(self.compile_tex(tex_path, project, subdeck=subdeck))
                else:
                    outputs.append(tex_path)
            return outputs

        self._validate_single_document_sizes(project, subdecks)
        tex_path = self.write_tex(project, subdeck=None)
        if compile_pdf:
            outputs.append(self.compile_tex(tex_path, project, subdeck=None))
        else:
            outputs.append(tex_path)
        return outputs

    def write_tex(self, project: DeckProject, *, subdeck: SubDeckSpec | None) -> Path:
        """Write the rendered LaTeX document to the project build directory."""
        deck_globals = project.globals_for_subdeck(subdeck)
        tex_text = self.render_tex(project, deck_globals=deck_globals, subdeck=subdeck)
        output_pdf_path = project.deck.output_path(base_path=project.base_path, subdeck=subdeck)
        build_dir = output_pdf_path.parent
        build_dir.mkdir(parents=True, exist_ok=True)
        tex_name = output_pdf_path.with_suffix(".tex").name
        tex_path = build_dir / tex_name
        tex_path.write_text(tex_text, encoding="utf-8")
        return tex_path

    def render_tex(
        self,
        project: DeckProject,
        *,
        deck_globals: DeckGlobals,
        subdeck: SubDeckSpec | None,
    ) -> str:
        """Render a deck or subdeck to a full LaTeX document string."""
        pages: list[str] = []
        subdecks = (
            [subdeck] if subdeck is not None else project.deck.materialized_subdecks(project.cards)
        )
        for current_subdeck in subdecks:
            current_globals = project.globals_for_subdeck(current_subdeck)
            for card in self._expanded_cards(project, current_subdeck):
                pages.append(
                    self._render_card_side_page(project, card, CardSide.FRONT, current_globals)
                )
                pages.append(
                    self._render_card_side_page(project, card, CardSide.BACK, current_globals)
                )

        template = self._load_template(project.deck.latex.main_template or self.template_name)
        return template.substitute(
            title=_latex_escape(project.deck.name),
            card_width_mm=f"{deck_globals.card_width_mm:.3f}",
            card_height_mm=f"{deck_globals.card_height_mm:.3f}",
            pages="\n\\newpage\n".join(pages),
        )

    def _validate_single_document_sizes(
        self,
        project: DeckProject,
        subdecks: list[SubDeckSpec],
    ) -> None:
        """Ensure a shared PDF uses a single page size across all subdecks."""
        expected = project.deck.globals
        for subdeck in subdecks:
            current = project.globals_for_subdeck(subdeck)
            if (
                current.card_width_mm != expected.card_width_mm
                or current.card_height_mm != expected.card_height_mm
            ):
                raise ValueError(
                    "Decks rendered into one PDF must share card dimensions or enable "
                    "'pdf_per_subdeck'."
                )

    def compile_tex(
        self,
        tex_path: Path,
        project: DeckProject,
        *,
        subdeck: SubDeckSpec | None,
    ) -> Path:
        """Compile a LaTeX document into a PDF using the configured engine."""
        engine = project.deck.latex.engine.lower()
        output_pdf_path = project.deck.output_path(base_path=project.base_path, subdeck=subdeck)
        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

        if engine == "latexmk":
            self._run_command(
                [
                    "latexmk",
                    "-pdf",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-file-line-error",
                    f"-output-directory={tex_path.parent}",
                    str(tex_path),
                ],
                cwd=tex_path.parent,
            )
        elif engine == "tectonic":
            self._run_command(
                [
                    "tectonic",
                    "--outdir",
                    str(tex_path.parent),
                    str(tex_path),
                ],
                cwd=tex_path.parent,
            )
        elif engine == "pdflatex":
            self._run_command(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    f"-output-directory={tex_path.parent}",
                    str(tex_path),
                ],
                cwd=tex_path.parent,
            )
        else:
            raise ValueError(f"Unsupported LaTeX engine: {project.deck.latex.engine!r}")

        compiled_pdf = tex_path.with_suffix(".pdf")
        if not compiled_pdf.exists():
            raise FileNotFoundError(f"Expected compiled PDF at {compiled_pdf}.")
        if compiled_pdf != output_pdf_path:
            shutil.copyfile(compiled_pdf, output_pdf_path)
        return output_pdf_path

    def _expanded_cards(self, project: DeckProject, subdeck: SubDeckSpec) -> list[CardSpec]:
        """Return the concrete cards that belong to one subdeck."""
        cards: list[CardSpec] = []
        for entry in subdeck.cards:
            cards.extend([project.get_card(entry.card_id)] * entry.copies)
        return cards

    def _select_subdeck(
        self,
        project: DeckProject,
        *,
        card_id: str,
        subdeck_id: str | None,
    ) -> SubDeckSpec | None:
        """Return the subdeck selected for preview, if any."""
        subdecks = project.deck.materialized_subdecks(project.cards)
        if subdeck_id is not None:
            for subdeck in subdecks:
                if subdeck.id == subdeck_id:
                    return subdeck
            raise KeyError(f"Unknown subdeck id {subdeck_id!r}.")
        for subdeck in subdecks:
            if card_id in subdeck.expanded_card_ids():
                return subdeck
        return subdecks[0] if subdecks else None

    def _resolve_preview_nodes(
        self,
        *,
        project: DeckProject,
        card: CardSpec,
        side: CardSide,
        deck_globals: DeckGlobals,
    ) -> list[PreviewNode]:
        """Resolve one card side into preview nodes."""
        layout = project.get_layout(card.layout_id)
        root = layout.root_for_side(side)
        card_rect = deck_globals.card_rect()
        output: list[PreviewNode] = []
        self._visit_layout_node(
            node=root,
            parent_rect=card_rect,
            card_rect=card_rect,
            card=card,
            side=side,
            deck_globals=deck_globals,
            base_path=project.base_path,
            output=output,
        )
        return sorted(output, key=lambda node: (node.z_index, node.id))

    def _visit_layout_node(
        self,
        *,
        node: LayoutNode,
        parent_rect: ResolvedRect,
        card_rect: ResolvedRect,
        card: CardSpec,
        side: CardSide,
        deck_globals: DeckGlobals,
        base_path: Path | None,
        output: list[PreviewNode],
    ) -> None:
        """Recursively resolve one layout node and append preview nodes."""
        resolved_rect = node.rect.resolve(card_rect=card_rect, parent_rect=parent_rect)
        if isinstance(node, ContainerLayout):
            content_rect = node.content_rect(resolved_rect, card_rect=card_rect)
            for child in node.children:
                self._visit_layout_node(
                    node=child,
                    parent_rect=content_rect,
                    card_rect=card_rect,
                    card=card,
                    side=side,
                    deck_globals=deck_globals,
                    base_path=base_path,
                    output=output,
                )
            return

        preview = PreviewNode(
            id=node.id,
            node_type=node.node_type,
            side=side.value,
            rect=resolved_rect,
            z_index=node.z_index,
            opacity=node.opacity,
        )
        bound_value = card.get_value(side, node.id)
        if isinstance(node, TextLayout):
            preview.text = bound_value.text if isinstance(bound_value, TextValue) else ""
            preview.color = str(node.font_color)
            preview.meta = {
                "align": node.align,
                "font_size_pt": str(node.font_size_pt),
                "font_family": node.font_family,
            }
        elif isinstance(node, ImageLayout):
            if isinstance(bound_value, ImageValue):
                preview.image_path = str(
                    self._resolve_asset_path(
                        bound_value.path, deck_globals=deck_globals, base_path=base_path
                    )
                )
            preview.meta = {"fit": node.fit, "clip": str(node.clip).lower()}
        elif isinstance(node, ColorLayout):
            if isinstance(bound_value, ColorValue):
                preview.color = str(bound_value.color)
            else:
                preview.color = str(node.color)
        elif isinstance(node, BleedLayout):
            preview.color = str(node.stroke_color)
            preview.meta = {
                "bleed_mm": str(
                    node.bleed_mm if node.bleed_mm is not None else deck_globals.bleed_mm
                ),
                "stroke_width_pt": str(node.stroke_width_pt),
            }
        output.append(preview)

    def _render_card_side_page(
        self,
        project: DeckProject,
        card: CardSpec,
        side: CardSide,
        deck_globals: DeckGlobals,
    ) -> str:
        """Render one card side page as TikZ commands."""
        preview_nodes = self._resolve_preview_nodes(
            project=project,
            card=card,
            side=side,
            deck_globals=deck_globals,
        )
        commands: list[str] = [
            f"% Card {card.id} ({side.value})",
            "\\thispagestyle{empty}",
            "\\noindent",
            "\\begin{tikzpicture}[x=1mm,y=1mm]",
        ]
        for node in preview_nodes:
            commands.extend(self._preview_node_to_latex(node, deck_globals.card_height_mm))
        commands.append("\\end{tikzpicture}")
        return "\n".join(commands)

    def _preview_node_to_latex(self, node: PreviewNode, card_height_mm: float) -> list[str]:
        """Render one preview node into TikZ commands."""
        top_y = card_height_mm - node.rect.y
        if node.node_type == "color" and node.color is not None:
            return [
                (
                    "\\fill[fill="
                    f"{_latex_color(node.color)}, opacity={node.opacity}] "
                    f"({node.rect.x:.3f},{top_y:.3f}) rectangle "
                    f"+({node.rect.width:.3f},{-node.rect.height:.3f});"
                )
            ]
        if node.node_type == "bleed" and node.color is not None:
            meta = node.meta or {"stroke_width_pt": "0.4"}
            return [
                (
                    "\\draw[draw="
                    f"{_latex_color(node.color)}, line width={meta['stroke_width_pt']}pt, "
                    f"opacity={node.opacity}] "
                    f"({node.rect.x:.3f},{top_y:.3f}) rectangle "
                    f"+({node.rect.width:.3f},{-node.rect.height:.3f});"
                )
            ]
        if node.node_type == "image" and node.image_path is not None:
            include_options = [
                f"width={node.rect.width:.3f}mm",
                f"height={node.rect.height:.3f}mm",
            ]
            if node.meta and node.meta.get("fit") == "contain":
                include_options.append("keepaspectratio")
            image_command = (
                "\\node[anchor=north west, inner sep=0, outer sep=0, opacity="
                f"{node.opacity}] at ({node.rect.x:.3f},{top_y:.3f}) "
                "{\\includegraphics["
                + ",".join(include_options)
                + "]{\\detokenize{"
                + node.image_path
                + "}}};"
            )
            if node.meta and node.meta.get("clip") == "true":
                return [
                    "\\begin{scope}",
                    (
                        f"\\clip ({node.rect.x:.3f},{top_y:.3f}) rectangle "
                        f"+({node.rect.width:.3f},{-node.rect.height:.3f});"
                    ),
                    image_command,
                    "\\end{scope}",
                ]
            return [image_command]
        if node.node_type == "text":
            align = (
                "justify"
                if node.meta and node.meta.get("align") == "justify"
                else (node.meta.get("align", "left") if node.meta else "left")
            )
            line_height = 1.2
            text = _latex_escape(node.text or "").replace("\n", "\\\\")
            text_meta = node.meta or {"font_size_pt": "12"}
            text_color = _latex_color(node.color or "black")
            font_size = text_meta["font_size_pt"]
            line_spacing = float(font_size) * line_height
            return [
                (
                    "\\node[anchor=north west, inner sep=0, outer sep=0, text width="
                    f"{node.rect.width:.3f}mm, align={align}, text={text_color}, "
                    f"opacity={node.opacity}] at ({node.rect.x:.3f},{top_y:.3f}) "
                    "{\\fontsize{"
                    f"{font_size}"
                    "}{"
                    f"{line_spacing:.3f}"
                    "}\\selectfont "
                    f"{text}"
                    "};"
                )
            ]
        return []

    def _resolve_asset_path(
        self,
        relative_path: str,
        *,
        deck_globals: DeckGlobals,
        base_path: Path | None,
    ) -> Path:
        """Resolve a card asset path against the configured asset root."""
        candidate = Path(relative_path)
        if candidate.is_absolute():
            return candidate.resolve()
        return (deck_globals.assets_directory(base_path) / candidate).resolve()

    def _load_template(self, template_name: str) -> Template:
        """Load the LaTeX document template bundled with the package."""
        template_path = Path(__file__).with_name("templates") / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Unknown LaTeX template: {template_name}")
        return Template(template_path.read_text(encoding="utf-8"))

    def _run_command(self, command: list[str], *, cwd: Path) -> None:
        """Run one external compilation command."""
        if shutil.which(command[0]) is None:
            raise FileNotFoundError(f"Required command not found on PATH: {command[0]}")
        subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def _latex_escape(text: str) -> str:
    """Escape plain text for inclusion in LaTeX documents."""
    replacements = {
        "\\": "\\textbackslash{}",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
    }
    output = text
    for source, target in replacements.items():
        output = output.replace(source, target)
    return output


def _latex_color(color: str) -> str:
    """Convert a color token to an xcolor-compatible expression."""
    if color.startswith("#") and len(color) >= 7:
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)
        return f"{{rgb,255:red,{red};green,{green};blue,{blue}}}"
    return color
