# Block: `contact-sheet`

A grid of variants — sizes, states, intents, languages — shown together for review.

**Group:** comparison · **Default packaging:** `static` · **Markdown fields:** `cells[].caption`

## When To Use

When the section's value is *seeing all the variants at once*: every button size and state in a design system, every callout tone in this skill, every layout option in a deck pattern, every model output for a single prompt. Pairs naturally with the `composed-blocks` archetype's handbook deliverable.

For a 2- or 3-column comparison of full prose blocks, use `side-by-side`. Use `contact-sheet` when there are 4+ variants and each fits in a small cell.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the grid. |
| `columns` | integer | no | Hint for grid columns. Default 4 on wide viewports. |
| `cellMinWidth` | string | no | CSS min width per cell (e.g. `"10rem"`). Default `"12rem"`. |
| `cells` | array of cell objects | yes | At least two cells. |
| `cells[].label` | string | yes | Primary label inside the cell. |
| `cells[].sublabel` | string | no | Smaller secondary label. |
| `cells[].caption` *(markdown)* | string | no | Footer caption. Renders to `captionHtml`. |
| `cells[].html` | string | no | Raw HTML content for the cell body. The compiler may sanitise. Mutually exclusive with `svg`. |
| `cells[].svg` | string | no | SVG markup for the cell body. Mutually exclusive with `html`. |
| `cells[].tag` | string | no | Small badge in the corner. |
| `cells[].group` | string | no | Optional group key; cells with the same group share a section header. |

## Example

```yaml
- type: contact-sheet
  data:
    title: "Callout tones"
    columns: 3
    cells:
      - label: "info"
        sublabel: "tone"
        html: '<div class="cs-cell-callout cs-cell-callout--info">Neutral commentary</div>'
      - label: "success"
        sublabel: "tone"
        html: '<div class="cs-cell-callout cs-cell-callout--success">Working pattern</div>'
      - label: "warning"
        sublabel: "tone"
        html: '<div class="cs-cell-callout cs-cell-callout--warning">Caveat or footgun</div>'
      - label: "danger"
        sublabel: "tone"
        html: '<div class="cs-cell-callout cs-cell-callout--danger">Don’t do this</div>'
      - label: "key"
        sublabel: "tone"
        html: '<div class="cs-cell-callout cs-cell-callout--key">Most important point</div>'
      - label: "neutral"
        sublabel: "tone"
        html: '<div class="cs-cell-callout cs-cell-callout--neutral">Generic emphasis</div>'
```

## Rendering

A responsive CSS grid with auto-flow. Each cell has a small caps label, optional sublabel, the body (HTML or SVG), and an optional caption. Cells in the same `group` are visually clustered with a small group header above their range.
