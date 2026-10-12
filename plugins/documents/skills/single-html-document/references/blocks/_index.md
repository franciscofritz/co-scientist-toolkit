# Block Index

A catalogue of every block defined in this skill. Read [`_protocol.md`](_protocol.md) first if you have not seen the contract every block follows.

## Scaffolding

Static-mode blocks for opening, flagging, and structuring prose.

| Block | Purpose | Markdown fields |
|---|---|---|
| [`tldr`](tldr.md) | Section punchline panel. | `body`, `points` |
| [`callout`](callout.md) | Tone-coloured emphasis panel. | `body` |
| [`faq`](faq.md) | Disclosure-widget question and answer list. | `answer` |
| [`before-after`](before-after.md) | Two-panel temporal comparison. | `before.body`, `after.body` |
| [`glossary`](glossary.md) | Term and definition catalogue with cross-references. | `definition` |

## Diagram

Visual structure blocks. Mostly static; flowchart adds click-reveal node details.

| Block | Purpose | Default packaging |
|---|---|---|
| [`timeline`](timeline.md) | Vertical chronology with status, tags, and follow-up checklists. | `static` |
| [`flowchart`](flowchart.md) | Node-and-edge process diagram with click-reveal details. | `interactive` |
| [`module-map`](module-map.md) | Boxes-and-arrows architecture view across columns. | `static` |
| [`mind-map`](mind-map.md) | Hierarchical outline laid out spatially, central root with branches. | `static` |
| [`concept-map`](concept-map.md) | Network of nodes with labelled edges, no central root. | `static` |
| [`inline-svg`](inline-svg.md) | Captioned SVG figure with attribution. | `static` |

## Comparison and Tokens

Side-by-side, design-system, and token blocks. Two are interactive (swatches copy on click; tabbed-code switches tabs).

| Block | Purpose | Default packaging |
|---|---|---|
| [`side-by-side`](side-by-side.md) | Equal-weight panels for parallel options. | `static` |
| [`contact-sheet`](contact-sheet.md) | Variant grid for design-system review. | `static` |
| [`swatches`](swatches.md) | Click-to-copy design tokens. | `interactive` |
| [`severity-tag`](severity-tag.md) | Tag-vocabulary catalogue that emits reusable `.tag-<name>` rules. | `static` |
| [`tabbed-code`](tabbed-code.md) | Accessible tabbed view of equivalent code samples. | `interactive` |

## Interactive

Reader-driven blocks. All default to `interactive`; all degrade gracefully with `packaging: static`.

| Block | Purpose |
|---|---|
| [`slider`](slider.md) | Live parameter controls that recompute outputs from authored expressions. |
| [`toggle-deps`](toggle-deps.md) | Grouped feature flags with dependency and conflict warnings, plus YAML export. |
| [`drag-reorder`](drag-reorder.md) | Kanban-style drag and drop with markdown/yaml/text export. |
| [`live-template`](live-template.md) | Template with editable variables that renders live. |
| [`annotated-diff`](annotated-diff.md) | Diff view with margin notes (severity-tagged) and jump links. |

## Custom Escape Hatch

The generic [`custom`](_protocol.md#custom-escape-hatch) block accepts inline `html`, `css`, and `js`. Use sparingly. The audit script flags concentrations.

## Adding A Block

See [`_protocol.md`](_protocol.md#adding-a-new-block) for the step-by-step.
