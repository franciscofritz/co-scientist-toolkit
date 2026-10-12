# Block: `tabbed-code`

A tabbed view of the same example expressed in different forms (languages, runtimes, package managers, configurations).

**Group:** comparison · **Default packaging:** `interactive` · **Markdown fields:** none

## When To Use

When the section needs to show the same idea in two or three forms — `npm` vs `pnpm` vs `bun` install commands, the same algorithm in Python and TypeScript, the same config in YAML and JSON — and the reader should be able to switch between them quickly without losing position.

For unrelated code samples, don't use tabs — use sequential code blocks. Tabs imply *equivalent variants*. Mismatched samples in tabs confuse readers.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the tabbed view. |
| `default` | integer or string | no | Index or label of the initially-selected tab. Default `0`. |
| `tabs` | array of tab objects | yes | At least two tabs. |
| `tabs[].label` | string | yes | Tab label. Should be short. |
| `tabs[].language` | string | no | Used as a `data-language` attribute and shown in the tab corner. |
| `tabs[].source` | string | yes | Code body. |
| `tabs[].caption` | string | no | One-line caption shown below the code. |

## Example

```yaml
- type: tabbed-code
  packaging: interactive
  data:
    title: "Install commands"
    default: 0
    tabs:
      - label: "npm"
        language: bash
        source: |
          npm install gray-matter fast-glob
          npm install -D vite-plugin-singlefile
      - label: "pnpm"
        language: bash
        source: |
          pnpm add gray-matter fast-glob
          pnpm add -D vite-plugin-singlefile
      - label: "bun"
        language: bash
        source: |
          bun add gray-matter fast-glob
          bun add -d vite-plugin-singlefile
```

## Rendering

Tab buttons across the top, code panel below. Buttons are real `<button>` elements with `role="tab"` and proper `aria-selected` / `aria-controls` wiring. Keyboard support: left/right arrow keys move between tabs, Home/End jump to first/last.

When `packaging: static`, tabs render as sequential headed blocks (label as a small heading above each code snippet). The interactive switcher is only injected in the `interactive` mode.
