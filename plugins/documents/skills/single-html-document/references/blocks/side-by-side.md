# Block: `side-by-side`

Two or three equal-weight panels for comparing parallel options.

**Group:** comparison · **Default packaging:** `static` · **Markdown fields:** `panels[].body`

## When To Use

When the section evaluates two or three parallel approaches and the reader needs to weigh them at the same time. Examples: option A vs option B for a build decision; "what we tried" vs "what worked"; React vs plain HTML for a use case.

Use this block instead of `before-after` when there's no temporal direction (neither side is "earlier" or "later"). Use it instead of a comparison table when each option benefits from a paragraph of prose, not a row of cells.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the comparison. |
| `panels` | array of 2–3 panel objects | yes | Two or three panels render as columns; more than three should use `contact-sheet` instead. |
| `panels[].label` | string | yes | Eyebrow label. |
| `panels[].title` | string | no | Heading inside the panel. |
| `panels[].body` *(markdown)* | string | yes | Renders to `bodyHtml`. |
| `panels[].tag` | string | no | Optional pill (e.g. "recommended"). |
| `panels[].accent` | enum: `info`, `success`, `warning`, `danger`, `neutral` | no | Tints the panel's left rail. Default `neutral`. |

## Example

```yaml
- type: side-by-side
  data:
    title: "Direct inline vs Blob-backed payload"
    panels:
      - label: "Direct inline"
        title: "Best for narrative reports"
        body: "All assets inlined as Base64 inside the HTML. Simple. Fast to author. Files stay small for narrative content."
        accent: info
      - label: "Blob-backed payload"
        title: "Best for binary-heavy reports"
        body: "Attachments embedded as data records, materialised as `Blob` URLs only when needed. Keeps the DOM clean even with many large downloads."
        accent: success
        tag: "recommended for media"
```

## Rendering

Equal-width columns separated by a thin divider, each with the label as a small caps eyebrow, the title in bold, the body flowing below, and an optional tag pill in the corner. Accent tints the left rail. On narrow viewports the layout collapses to vertical stacking with the rail switching to a top border.
