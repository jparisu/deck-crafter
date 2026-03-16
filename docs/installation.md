# Installation

## Install from a local checkout

```bash
python -m pip install .
```

## Development install

```bash
python -m pip install -e ".[dev]"
pre-commit install
```

## LaTeX engine

PDF generation requires one of these commands to be available on `PATH`:

- `latexmk`
- `pdflatex`
- `tectonic`

The default configuration uses `latexmk`.
