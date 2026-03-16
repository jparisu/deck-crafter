# Visual Interface

Run the local editor with:

```bash
deck-crafter serve examples/demo_deck.yaml
```

The browser UI supports:

- Loading an existing YAML file
- Saving the current project back to YAML
- Selecting a card and side for preview
- Adding text, image, and color nodes
- Editing rectangle values and bound card content
- Generating the PDF deck from the current in-memory project

The editor is intentionally local-first. It serves one HTML page from Python's standard library HTTP server and writes standard YAML files to disk.
