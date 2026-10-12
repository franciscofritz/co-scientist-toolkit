# Block: `swatches`

A grid of design tokens — colours, spacings, type scales — with click-to-copy values.

**Group:** comparison · **Default packaging:** `interactive` · **Markdown fields:** `swatches[].description`

## When To Use

When the section needs to enumerate design tokens for review or reuse: brand colours and their usage rules, severity tag colours, the institutional theme palette, a committee briefing's palette extract, or a deck's accent colours. Pairs naturally with the `composed-blocks` archetype's handbook deliverable.

The block defaults to `interactive` because click-to-copy is its main value. With `packaging: static` the swatches still render correctly but the copy interaction is removed.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the grid. |
| `kind` | enum: `color`, `space`, `radius`, `typescale`, `custom` | no | Default `color`. Drives the swatch shape. |
| `swatches` | array of swatch objects | yes | At least one. |
| `swatches[].name` | string | yes | The token name, e.g. `--accent-primary`. Becomes the displayed label. |
| `swatches[].value` | string | yes | The token value (CSS colour, dimension, etc.). Click-to-copied. |
| `swatches[].label` | string | no | Display label override. |
| `swatches[].role` | string | no | Short usage note (e.g. "primary CTA"). |
| `swatches[].description` *(markdown)* | string | no | Longer description. Renders to `descriptionHtml`. |
| `copyValue` | enum: `value`, `name`, `var` | no | Default `value`. `var` copies `var(<name>)`. |

## Example

```yaml
- type: swatches
  packaging: interactive
  data:
    title: "Institutional palette"
    kind: color
    copyValue: var
    swatches:
      - { name: "--ox-blue",    value: "#002147", role: "primary brand" }
      - { name: "--ox-stone",   value: "#f5f1eb", role: "page background" }
      - { name: "--ox-deep",    value: "#0f3d5e", role: "headings" }
      - { name: "--ox-accent",  value: "#ee6c4d", role: "callout accents" }
```

## Rendering

A responsive grid with one cell per swatch. For `kind: color`, the cell shows a coloured tile with the value laid over a contrasting strip. For `kind: space` and `kind: radius`, the cell visualises the dimension. For `kind: typescale`, the cell displays sample text at the size. For `kind: custom`, the cell falls back to a value chip.

When `packaging: interactive`, each cell becomes a button that copies the configured value to the clipboard and flashes a "Copied" confirmation. The renderer uses `navigator.clipboard.writeText`; falls back to a hidden `textarea + select + execCommand('copy')` for older browsers and offline `file://` contexts where the Clipboard API may be restricted.
