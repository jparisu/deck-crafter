# Configuration Format

A project file is a YAML document with these top-level keys:

```yaml
schema_version: 1
layouts: []
cards: []
deck: {}
```

## Layouts

Each layout contains two root containers:

- `front_root`
- `back_root`

Supported node types:

- `container`
- `text`
- `image`
- `color`
- `bleed`

Each node has:

- `id`
- `side`
- `rect`
- `z_index`
- `opacity`
- `rotation_deg`

`rect` uses `x`, `y`, `width`, and `height`. Each measure can be:

- `absolute`: fixed physical size in `mm`, `cm`, `in`, or `pt`
- `relative`: fraction of either the `card` or the `parent`

## Cards

Cards bind actual values to node ids:

```yaml
cards:
  - id: fireball
    layout_id: spell_layout
    values_front:
      title: { type: text, text: "Fireball" }
      art: { type: image, path: "fireball.png" }
```

Supported card value types:

- `text`
- `image`
- `color`

## Deck

The `deck` section defines:

- global card size and asset root
- output PDF path
- LaTeX engine
- optional subdecks with card copies

## Includes and References

Two reuse features are supported:

- `yaml-file`: merge another YAML file into the current one
- `$ref`: copy another subtree from the same combined configuration

Example:

```yaml
back_root:
  $ref: demo_layout.front_root
```
