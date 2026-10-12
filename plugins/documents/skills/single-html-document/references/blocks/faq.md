# Block: `faq`

A list of question/answer pairs as native disclosure widgets.

**Group:** scaffolding · **Default packaging:** `static` · **Markdown fields:** `answer`

## When To Use

When the section has anticipated questions a reader will ask, and you don't want to derail the main narrative with sub-headings for each one. FAQs work well at the end of explainer pages, near the top of dossiers, in onboarding documents, and as appendix material on workshop reports.

Use real questions readers actually ask. Don't write FAQs as marketing copy — they read worse than the body text and lose trust.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `eyebrow` | string | no | Override the default "FAQ" label. |
| `title` | string | no | Section title above the list. |
| `defaultOpen` | enum: `none`, `first`, `all` | no | Whether questions start expanded. Default `none`. |
| `items` | array of `{question, answer (markdown)}` | yes | At least one item. `answer` renders to `answerHtml`. |

## Example

```yaml
- type: faq
  data:
    title: "Common questions"
    items:
      - question: "Why not just generate one big HTML file directly?"
        answer: |
          Because authoring inside one giant HTML blob is brittle — you can't
          diff it, restyle it, or reuse content. The skill's whole position is
          that single-file is a **delivery format**, not an authoring format.
      - question: "What about MHTML or Web Bundles?"
        answer: |
          Web Bundles had their navigation implementation removed from Chromium
          in 2023; MHTML is a niche capture format. Plain `.html` is the only
          format that opens reliably across modern browsers from disk.
```

## Rendering

Native `<details>`/`<summary>` elements, one per item. Markers are restyled as plus/minus icons that rotate when expanded. The block has no JavaScript — disclosure behaviour is the browser's. This means it works identically in static and printed contexts.

When `defaultOpen` is `all` and the FAQ has more than ~10 items, consider rendering as a regular list with explicit headings instead.
