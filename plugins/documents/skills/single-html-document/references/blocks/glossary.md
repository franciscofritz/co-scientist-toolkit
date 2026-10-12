# Block: `glossary`

A list of terms with definitions, optionally with cross-references and aliases.

**Group:** scaffolding · **Default packaging:** `static` · **Markdown fields:** `definition`

## When To Use

When the document uses jargon, acronyms, or domain-specific terms that not every reader will know. Glossaries belong near the top of long documents (so readers can orient) or in the appendix (for occasional lookup). Use a glossary block, not a sequence of definition paragraphs, when there are more than three terms — it gives them stable structure for skimming.

The block supports a margin layout for documents wide enough to host it (Thariq's "glossary in margin" pattern), and a stacked layout for narrower contexts.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the list. Default "Glossary". |
| `layout` | enum: `stacked`, `two-column`, `margin` | no | Default `stacked`. `margin` requires the host page to leave space. |
| `terms` | array of `{term, definition (markdown), aliases?, related?}` | yes | At least one term. |
| `terms[].term` | string | yes | The term itself. Becomes the heading. |
| `terms[].definition` *(markdown)* | string | yes | Renders to `definitionHtml`. |
| `terms[].aliases` | array of string | no | Synonyms or alternate spellings, shown as small tags. |
| `terms[].related` | array of string | no | Other glossary term IDs to link to. The compiler resolves these. |

## Example

```yaml
- type: glossary
  data:
    title: "Terms used in this report"
    layout: stacked
    terms:
      - term: "Single-file HTML"
        definition: |
          A complete website (text, styles, scripts, media) collapsed into one
          `.html` file that opens directly in a modern browser.
        aliases: ["self-contained HTML", "portable HTML"]
        related: ["packaging mode"]
      - term: "Packaging mode"
        definition: |
          Build-time strategy for collapsing assets into the deliverable. The
          three named modes are **direct inline**, **Blob-backed payload**, and
          **compressed bootstrap**.
        aliases: ["delivery mode"]
```

## Rendering

Stacked layout: each term as a heading row with the term and aliases, definition flowing below. Two-column layout: term on the left, definition on the right (best for short definitions). Margin layout: terms float in the margin of the host content; the compiler injects anchor links from term occurrences in the body.

The renderer assigns a stable id of the form `glossary-<slugified-term>` to each term so cross-references and `related` links resolve.
