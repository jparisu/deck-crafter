# Development

The project is intentionally split into a small number of modules:

- `deck_crafter.geometry`: coordinate and sizing primitives
- `deck_crafter.layouts`: reusable layout templates and node trees
- `deck_crafter.cards`: concrete card values
- `deck_crafter.decks`: deck-level settings and validation
- `deck_crafter.configuration`: YAML loading, includes, and `$ref` resolution
- `deck_crafter.latex`: preview, LaTeX rendering, and PDF compilation
- `deck_crafter.visual_interface`: local browser UI

Useful commands:

```bash
make install-current
make lint
make test
make docs
```

The test suite covers the domain model, configuration loading, LaTeX generation, and the visual interface shell. The PDF compilation step is also testable through a mocked compiler path.

## Tooling

- Ruff for linting and formatting
- Mypy for type checking
- Pytest for testing
- MkDocs for documentation


## Shared utils

This template was generated with shared utils integration enabled. Add the relevant internal dependency in `pyproject.toml` before using it.


## Commands

```bash
make install
make install-current
make format
make lint
make test
make docs
```
