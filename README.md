# Deck Crafter

`deck-crafter` builds printable card decks from YAML configuration files. It provides:

- A reusable Python package for layouts, cards, decks, and configuration loading
- A LaTeX-based PDF generator for deck output
- A local browser UI to edit projects, preview cards, save YAML, and generate PDFs

## Installation

From a local checkout:

```bash
python -m pip install .
```

For development:

```bash
python -m pip install -e ".[dev]"
pre-commit install
```

To compile PDFs, install a LaTeX engine. `deck-crafter` supports `latexmk`, `pdflatex`, and `tectonic`. The repository examples use `latexmk`.

## Quick Start

Build the bundled example configuration:

```bash
deck-crafter build examples/demo_deck.yaml
```

Render only the intermediate LaTeX file:

```bash
deck-crafter build examples/demo_deck.yaml --tex-only
```

Start the local visual editor:

```bash
deck-crafter serve examples/demo_deck.yaml --port 8765
```

Then open `http://127.0.0.1:8765`.

## Configuration Model

A project file contains four sections:

- `schema_version`: configuration schema version
- `layouts`: reusable card templates composed from nested layout nodes
- `cards`: concrete values bound to layout node ids
- `deck`: output settings, LaTeX engine configuration, and subdeck membership

Relative rectangles are resolved against either the card or the parent container. Cards store content separately from layouts, so one template can drive many card instances.

## Example

The repository ships with:

- [`examples/demo_deck.yaml`](/home/jparisu/projects/devs/deck-crafter/examples/demo_deck.yaml)
- Generated example output under [`examples/generated`](/home/jparisu/projects/devs/deck-crafter/examples/generated)

## Development

Useful commands:

```bash
make install-current
make lint
make test
make docs
```

## License

Licensed under the Apache 2.0 License.
