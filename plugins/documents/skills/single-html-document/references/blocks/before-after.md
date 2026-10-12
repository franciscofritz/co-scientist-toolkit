# Block: `before-after`

A two-panel comparison showing how something changed.

**Group:** scaffolding · **Default packaging:** `static` · **Markdown fields:** `before.body`, `after.body`

## When To Use

When the value of a section comes from showing the change explicitly — code refactors, prose rewrites, design tweaks, decision reversals, policy updates, before-and-after metrics. Pairs naturally with annotated diffs and side-by-side comparisons; use `before-after` when the framing is temporal (was → now) and `side-by-side` when it's "two valid options".

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `axis` | enum: `horizontal`, `vertical` | no | Default `horizontal` (panels side by side). `vertical` stacks them. |
| `before` | object | yes | The earlier state. |
| `after` | object | yes | The later state. |
| `before.label` / `after.label` | string | no | Override the default "Before" / "After" headings. |
| `before.body` *(markdown)* / `after.body` *(markdown)* | string | yes | Renders to `bodyHtml`. |
| `before.code` / `after.code` | object: `{language, source}` | no | Optional code block alongside the body. |

## Example

```yaml
- type: before-after
  data:
    before:
      label: "Before"
      body: "Generated HTML inline; no schema; long files; no way to reuse the pattern."
      code:
        language: yaml
        source: |
          - type: callout
            html: "<div class='warn'>Don't override the gate</div>"
    after:
      label: "After"
      body: "Typed block, clear schema, renderer separate, packaging mode declared."
      code:
        language: yaml
        source: |
          - type: callout
            data:
              tone: warning
              title: "Don't override the gate"
              body: "Investigate the package first."
```

## Rendering

Two panels with subtle separation. Each panel has its label as a small caps eyebrow, its prose body, and an optional code block underneath. On narrow viewports the layout collapses to vertical regardless of `axis`.

## Comparison To Other Blocks

- Use `side-by-side` for two valid alternatives (no temporal direction).
- Use `annotated-diff` when the change is line-level and you want margin notes.
- Use `before-after` when the framing is "this used to be X, now it's Y".
