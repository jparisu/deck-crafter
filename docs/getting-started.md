# Getting Started

Install the project and generate the example deck:

```bash
python -m pip install -e .
deck-crafter build examples/demo_deck.yaml
```

This produces:

- `examples/generated/demo_deck.tex`
- `examples/generated/demo_deck.pdf`

To start the interactive editor:

```bash
deck-crafter serve examples/demo_deck.yaml
```

Then open `http://127.0.0.1:8765`.

Python usage:

```python
from deck_crafter import generate_deck, load_project

project = load_project("examples/demo_deck.yaml")
outputs = generate_deck("examples/demo_deck.yaml", compile_pdf=False)
print(project.deck.name)
print(outputs)
```
