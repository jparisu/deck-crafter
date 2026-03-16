"""Tests for high-level application helpers."""

from pathlib import Path

from deck_crafter.application import generate_deck, generate_deck_from_project
from deck_crafter.latex import LatexDeckRenderer


def test_generate_deck_returns_tex_output_when_compilation_is_disabled(
    demo_config_file: Path,
) -> None:
    """The application should support LaTeX-only builds."""
    outputs = generate_deck(demo_config_file, compile_pdf=False)

    assert len(outputs) == 1
    assert outputs[0].suffix == ".tex"
    assert outputs[0].exists()


def test_generate_deck_from_project_can_be_tested_without_latex(
    demo_project,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """The build pipeline should allow the compile step to be replaced in tests."""

    def fake_compile(self, tex_path, project, *, subdeck):  # type: ignore[no-untyped-def]
        pdf_path = tex_path.with_suffix(".pdf")
        pdf_path.write_bytes(b"%PDF-1.4\n%fake\n")
        return pdf_path

    monkeypatch.setattr(LatexDeckRenderer, "compile_tex", fake_compile)

    outputs = generate_deck_from_project(demo_project, compile_pdf=True)

    assert len(outputs) == 1
    assert outputs[0].suffix == ".pdf"
    assert outputs[0].read_bytes().startswith(b"%PDF")
