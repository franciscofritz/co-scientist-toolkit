# Block: `tldr`

A condensed summary panel that tells a reader the punchline before the body of a section.

**Group:** scaffolding · **Default packaging:** `static` · **Markdown fields:** `body`

## When To Use

Open any long-form section with a TL;DR when readers might need to leave with just the punchline. Especially valuable in committee briefings, research syntheses, dossiers, and explainer pages where decision-makers skim. Don't use it as a bullet list — that's the `callout` block. Use TL;DR for one or two sentences plus optional supporting points.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `eyebrow` | string | no | Override the default "TL;DR" label. |
| `title` | string | no | Short headline above the body. |
| `body` *(markdown)* | string | yes | One or two sentences. Renders to `bodyHtml`. |
| `points` | array of string *(markdown)* | no | Optional supporting bullets. Each renders to HTML. |

## Example

```yaml
- type: tldr
  data:
    title: "Build the site first, package it second."
    body: "Treating single-file HTML as a delivery format keeps content, styling, and scripts separate during authoring. The packaging step collapses a working site into one file at the end."
    points:
      - "Author in Markdown plus YAML."
      - "Compile to JSON before the renderer touches it."
      - "Inline only at packaging time."
```

## Rendering

A small panel with a coloured left rail or accent background, the eyebrow as a small caps label, the optional title in bold, the body as a paragraph, and points as a tight list. The renderer does not invent additional structure; it renders exactly the fields supplied.
