# App Interface

The CLI exposes two main subcommands.

## Build

Generate `.pdf` output:

```bash
deck-crafter build examples/demo_deck.yaml
```

Generate only the `.tex` file:

```bash
deck-crafter build examples/demo_deck.yaml --tex-only
```

## Serve

Start the local editor:

```bash
deck-crafter serve examples/demo_deck.yaml --host 127.0.0.1 --port 8765
```

If no configuration file is passed, the editor starts with a default in-memory project.
