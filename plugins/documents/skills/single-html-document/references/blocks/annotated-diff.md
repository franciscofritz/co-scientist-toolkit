# Block: `annotated-diff`

A diff view with margin notes, severity tags, and jump links.

**Group:** interactive · **Default packaging:** `interactive` · **Markdown fields:** `notes[].body`

## When To Use

When the section reviews a code or content change and the reviewer's notes matter as much as the diff itself: code-review summaries, design-doc revisions, contract redlines, or post-mortem write-ups that explain a fix. Pairs naturally with `severity-tag` (which defines the vocabulary used in `notes[].severity`).

For raw diff display without commentary, just use a `<pre>` code block. Use `annotated-diff` when the value comes from the *annotations*, not just the diff.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the diff. |
| `path` | string | no | File path or label shown in the diff header. |
| `language` | string | no | Hint for syntax styling. The renderer does not perform highlighting; the compiler may. |
| `lines` | array of line objects | yes | Each line carries its kind and text. |
| `lines[].kind` | enum: `context`, `add`, `remove`, `change` | yes | Drives gutter colour. |
| `lines[].content` | string | yes | The line text (without leading +/-/space). |
| `lines[].oldNumber` | integer | no | Pre-change line number. Omit on `add` lines. |
| `lines[].newNumber` | integer | no | Post-change line number. Omit on `remove` lines. |
| `notes` | array of note objects | no | Margin notes that anchor to a range of lines. |
| `notes[].onLines` | `[start, end]` integers | yes | One-based indexes into `lines`, inclusive. |
| `notes[].severity` | string | no | Tag name. Should match a `severity-tag` defined elsewhere in the document. Used for the visual treatment. |
| `notes[].body` *(markdown)* | string | yes | Renders to `bodyHtml`. |
| `jumpLinks` | array of `{label, atLine}` | no | Generates a small toolbar above the diff for jumping to specific lines. |

## Example

```yaml
- type: annotated-diff
  packaging: interactive
  data:
    title: "Token validator change"
    path: "src/auth/validator.ts"
    language: typescript
    lines:
      - { kind: context, oldNumber: 12, newNumber: 12, content: "export async function validate(token: string) {" }
      - { kind: remove,  oldNumber: 13,                content: "  const jwks = await fetch(JWKS_URL).then((r) => r.json());" }
      - { kind: add,                    newNumber: 13, content: "  const jwks = await getJwks();  // cached, rotation-aware" }
      - { kind: context, oldNumber: 14, newNumber: 14, content: "  return verify(token, jwks);" }
      - { kind: context, oldNumber: 15, newNumber: 15, content: "}" }
    notes:
      - onLines: [2, 3]
        severity: P1
        body: |
          The previous version refetched the JWKS on every request. The new helper
          caches and respects rotation; see `getJwks` in `src/auth/jwks.ts`.
    jumpLinks:
      - { label: "Top of fix", atLine: 2 }
```

## Rendering

Three columns: line numbers, gutter (with kind glyph), content. Rows for `add` are tinted green; `remove` red; `change` amber; `context` neutral. Notes render as cards anchored to the right of their line range with a coloured rail matching their severity. Jump links render as a small button bar above the diff; clicking a link scrolls the corresponding line into view and briefly highlights it.

When `packaging: static`, jump links degrade to anchor links pointing at line ids, and notes render inline beneath their line range without the side anchor.
