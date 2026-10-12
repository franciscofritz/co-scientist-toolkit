# Block: `inline-svg`

A wrapper for embedding an SVG figure with caption and optional source attribution.

**Group:** diagram · **Default packaging:** `static` · **Markdown fields:** `caption`, `attribution`

## When To Use

When a section needs a hand-authored or generated SVG illustration: a conceptual diagram, a labelled architecture view, a custom chart that doesn't fit any standard chart block, or an embedded icon larger than typical inline use. The block ensures the SVG sits in a captioned figure container with consistent spacing across the report.

For a full chart block (bars, lines, donuts), use a chart block instead — `inline-svg` is for one-off illustration where you control the SVG source.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `svg` | string | yes | The SVG markup. Must be a `<svg>...</svg>` element. The compiler may sanitise scripts and external references. |
| `caption` *(markdown)* | string | no | Renders to `captionHtml` beneath the figure. |
| `attribution` *(markdown)* | string | no | Renders to `attributionHtml` as smaller text after the caption. |
| `align` | enum: `center`, `start`, `end`, `full` | no | Default `center`. `full` stretches the SVG container to the full content width. |
| `maxHeight` | string | no | CSS height (e.g. `"24rem"`) constraining the figure. |
| `frame` | boolean | no | Add a subtle border around the figure. Default `false`. |

## Example

```yaml
- type: inline-svg
  data:
    align: center
    maxHeight: "20rem"
    frame: true
    svg: |
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
        <rect x="10" y="20" width="60" height="60" rx="6" fill="#1f5679"/>
        <rect x="130" y="20" width="60" height="60" rx="6" fill="#2e6e40"/>
        <path d="M 70 50 L 130 50" stroke="#333" stroke-width="2" fill="none"/>
      </svg>
    caption: "Two-stage build: **author** ➜ **package**."
    attribution: "Source: this report's architecture diagram."
```

## Rendering

A `<figure>` element with the SVG centered (or aligned per `align`), a `<figcaption>` for the caption, and a smaller `<small>` block for the attribution. The renderer does not parse or modify the SVG — it inserts it as-is. The compiler is responsible for any sanitisation.

## Sanitisation Notes

The compiler should strip `<script>` elements and `on*` attributes from author-supplied SVG. External references (`<image href="https://...">`, `<use href="https://...">`) should be flagged and removed for offline-safe delivery. This is a compile-time concern; the renderer assumes the SVG is already safe.
