# Deck Crafter

`deck-crafter` turns YAML configuration into printable card-deck PDFs.

It includes three main pieces:

- A Python domain model for layouts, cards, decks, and configuration files
- A LaTeX renderer that writes `.tex` and compiles `.pdf`
- A local browser UI for interactive editing and preview

## Main workflow

1. Create or edit a YAML project file.
2. Define one or more reusable card layouts.
3. Bind card-specific values to layout node ids.
4. Run `deck-crafter build` to produce the deck PDF.

## Documentation Map

- [Installation](installation.md)
- [Getting Started](getting-started.md)
- [Visual Interface](visual-interface.md)
- [App Interface](app-interface.md)
- [Configuration Format](configuration-format.md)
- [API Reference](api/index.md)
