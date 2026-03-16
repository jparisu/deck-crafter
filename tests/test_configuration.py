"""Tests for YAML loading, reference resolution, and project dumping."""

from pathlib import Path

from deck_crafter.configuration import ConfigurationLoader


def test_configuration_loader_resolves_local_references(
    demo_project_dict: dict[str, object],
    tmp_path: Path,
) -> None:
    """The loader should expand ``$ref`` nodes before parsing the project."""
    project_dict = dict(demo_project_dict)
    layout = dict(project_dict["layouts"][0])  # type: ignore[index]
    layout["back_root"] = {"$ref": "demo_layout.front_root"}
    project_dict["layouts"] = [layout]

    project = ConfigurationLoader.from_dict(project_dict, base_path=tmp_path)

    assert project.layouts["demo_layout"].back_root.children[0].id == "background"


def test_configuration_loader_supports_yaml_file_includes(tmp_path: Path) -> None:
    """The loader should combine YAML files through the shared YamlHandler."""
    included = tmp_path / "included.yaml"
    included.write_text(
        (
            "layouts: []\n"
            "cards: []\n"
            "deck:\n"
            "  id: deck\n"
            "  globals:\n"
            "    assets_root: .\n"
            "    card_width_mm: 63\n"
            "    card_height_mm: 88\n"
            "  output_pdf: build/deck.pdf\n"
        ),
        encoding="utf-8",
    )
    root = tmp_path / "root.yaml"
    root.write_text("schema_version: 1\nyaml-file: included.yaml\n", encoding="utf-8")

    project = ConfigurationLoader.from_file(root)

    assert project.deck.id == "deck"


def test_configuration_loader_dump_round_trips(
    demo_project,
    tmp_path: Path,
) -> None:
    """Dumping a project should persist a YAML file that can be loaded again."""
    output = tmp_path / "saved.yaml"
    ConfigurationLoader.dump(demo_project, output)

    reloaded = ConfigurationLoader.from_file(output)

    assert reloaded.deck.name == demo_project.deck.name
