# Block Protocol

This document is the contract every block in this skill follows. Read it before adding a new block, before changing a renderer, or before composing blocks into a new archetype.

## Why This Layer Exists

Rich HTML reports benefit from reusable visual patterns — TL;DR cards, timelines, callouts, parameter sliders, glossaries, swatches, annotated diffs, and so on. The temptation is to author them as ad-hoc HTML fragments inside Markdown bodies. That collapses content and presentation back into one layer and makes the patterns impossible to restyle, repackage, or reason about.

The block layer keeps each pattern as a typed piece of content (YAML/JSON shape), with one renderer that knows how to turn that content into HTML. Authors stay in structured content. Designers and packagers stay in renderers. Drift between the two is structurally prevented because each block keeps its spec, renderer, and example colocated under a single name.

## File Layout

Every block named `<name>` lives in three colocated files:

```
references/blocks/<name>.md         spec, when-to-use, schema, packaging mode, examples
scripts/blocks/<name>.js            renderer module exporting `mount(root, data)`
assets/blocks/<name>.example.yml    canonical authoring example
```

Add or remove a block by editing all three together. If you change the schema in the `.md`, update the `.js` and `.example.yml` in the same change. This colocation is the main drift defence.

## Source Shape

A block instance lives inside page front matter or a sidecar YAML/JSON file as one entry in a `blocks` list:

```yaml
blocks:
  - type: <block-name>
    id: optional-stable-id          # used for deep links, hash routing, and renderer mount targets
    packaging: static | interactive  # optional override; default is declared by the block type
    data:
      # block-specific fields, defined in references/blocks/<name>.md
```

Required:

- `type` — must match a block name with files under `references/blocks/<type>.md` and `scripts/blocks/<type>.js`. Unknown types fail the build.

Optional but recommended:

- `id` — stable identifier authors can hand-write or the compiler can generate. Surface this as the DOM `id` of the block root so it can anchor deep links and table-of-contents entries.
- `packaging` — overrides the block type's default. See "Packaging Modes" below.
- `data` — block-specific fields. The schema for each is defined in the block's `.md` file. Validate at compile time.

The compiler should reject unknown top-level keys on a block entry so authors get fast feedback when they typo `interactivity` or `payload`.

## Renderer Contract

Every renderer module exports a single `mount` function:

```js
// scripts/blocks/<name>.js
export function mount(root, data) {
  // root: HTMLElement that already exists in the DOM
  // data: the validated `data` object from the YAML source
  // Returns: undefined. Side effects only.
}
```

Rules the contract enforces:

- **Pure vanilla JS.** No React, no Vue, no framework imports. The renderer must run identically whether the host site is a Vite/React app, a static HTML page, or the packaged single-file deliverable.
- **Idempotent.** Calling `mount(root, data)` twice on the same root should produce the same DOM. Renderers may clear `root.innerHTML` on entry.
- **Self-contained styling.** Required CSS lives next to the renderer (either as a `style` element written into the document head on first call, or scoped via the block's own class names). Do not depend on a global stylesheet provided by the host site.
- **No network at runtime.** Renderers may not `fetch()` or `import()` anything. All data they need arrives in `data`.
- **No global state.** Renderers may cache lazily-initialised CSS or shared helpers in module scope, but must not leak block-instance state across mounts.

These rules are what make the block layer work uniformly across packaging modes. Breaking any of them tends to break `file://` delivery, which is the whole point of the skill.

## Packaging Modes

Each block declares a default packaging mode, and each instance can override it.

### `static` (compile-time render)

The renderer is invoked at build time. Its DOM output is serialised into the generated HTML. The renderer JS is **not** shipped to the browser.

Use for blocks whose final state is deterministic at build time: TL;DR boxes, callouts, FAQs, timelines without click-reveal, glossaries, swatches, severity tags, side-by-side comparisons, contact sheets, module maps, inline SVGs, before/after panels, annotated diffs without jump links.

Build-time invocation pattern:

```js
import { JSDOM } from 'jsdom';
import { mount } from '../scripts/blocks/<name>.js';

const dom = new JSDOM('<div></div>');
const root = dom.window.document.querySelector('div');
mount.call({ document: dom.window.document }, root, data);
const html = root.outerHTML;
```

Static blocks should still write their CSS once per document (the compiler is responsible for deduping `<style>` tags emitted by static blocks).

### `interactive` (client hydration)

The renderer ships to the browser as a small inlined module. The block root contains a placeholder plus a `<script type="application/json">` payload with the validated `data`. On `DOMContentLoaded`, a tiny bootstrap finds every block of that type, reads the payload, and calls `mount(root, data)`.

Use for blocks whose value depends on user interaction at view time: parameter sliders, toggle groups with dependency warnings, drag-to-reorder with text export, live template editor, click-reveal flowchart, tabbed code variants, drawer-based glossary lookups.

The bootstrap is shared (`scripts/blocks/_bootstrap.js`); individual renderers do not register listeners directly. Renderers receive a fully constructed root and the parsed `data` and write the interactive DOM beneath it.

### When to override

The default mode is set by the block's nature, but instances can override it:

```yaml
- type: timeline
  packaging: interactive   # default is static; opt in to click-reveal annotations
  data: { … }
```

Document the supported overrides in the block's `.md` file. Don't accept overrides the renderer can't actually honour.

## Custom Escape Hatch

Some blocks are one-offs that don't merit a permanent type. For these, use the generic `custom` block:

```yaml
- type: custom
  id: my-one-off
  data:
    html: |
      <p>Arbitrary inline HTML.</p>
    css: |
      #my-one-off { background: var(--surface); }
    js: |
      // Optional. Receives `root` and `data` as locals.
      root.querySelector('p').addEventListener('click', () => alert('hi'));
```

Rules:

- Use sparingly. If you find yourself writing the same `custom` block twice, promote it to a real block type.
- The `audit-single-html.mjs` script counts `custom` block usage and warns above a threshold.
- `css` is optional. If present, it is scoped by prefixing rules with the block's `id`.
- `js` is optional. It runs once after mount with `root` (the block root element) and `data` bound as locals.
- `custom` blocks always package as `interactive` if `js` is present, otherwise as `static`. They do not accept a `packaging` override.

## Markdown In Block Fields

Block schemas may declare fields whose authored value is Markdown (e.g. a callout body, an FAQ answer, a glossary definition). The compiler renders these fields to HTML before passing them to the renderer.

Convention: a field whose authored value is Markdown is named `<base>` in the YAML and arrives at the renderer as `<base>Html`. Example:

```yaml
# author writes
blocks:
  - type: callout
    data:
      title: "Recommended path"
      body: "Build the **normal site** first, then [package it](#packaging)."
```

```js
// renderer receives
mount(root, {
  title: "Recommended path",
  bodyHtml: "Build the <strong>normal site</strong> first, then <a href=\"#packaging\">package it</a>.",
});
```

Supply these manifest fields directly in their `...Html` form. The build script
`scripts/build-block-sample.mjs` has no Markdown compiler, and a field written as `body` in an
example YAML is dropped without a warning.

This keeps Markdown parsing in the compiler, off the runtime, and out of every renderer. The block's `.md` file documents which fields are Markdown by listing them with the `(markdown)` suffix in the schema table.

## Validation

The content compiler validates each block in two passes:

1. **Shape pass** — rejects unknown `type`, unknown top-level keys, missing required fields, bad `packaging` value.
2. **Schema pass** — runs the per-block schema (defined in the `.md` and shipped as a JSON Schema or TypeScript type next to the renderer). Reports the first failing field with line context.

Validation failures should fail the build, not silently degrade. Authors fix typos faster when the compiler is strict.

## Adding A New Block

When you need a pattern that doesn't exist yet:

1. Decide if it's actually new. Check `references/blocks/` for an existing block that fits.
2. Pick the simplest packaging mode that works. Prefer `static` unless interaction is intrinsic.
3. Write `references/blocks/<name>.md` first — schema, packaging mode, when-to-use, two examples.
4. Write the canonical `assets/blocks/<name>.example.yml`.
5. Implement `scripts/blocks/<name>.js` and verify by mounting against the example in a scratch HTML file.
6. Add the block to `references/blocks/_index.md` so it appears in the catalogue.
7. If the block belongs to a recognised group (scaffolding, diagram, comparison, interactive), note that in its `.md` so the `composed-blocks` archetype can group it correctly.

## Anti-Patterns

Things that look reasonable but break the layer:

- **Renderers that import React.** Locks the block to a React host; breaks static packaging and the static HTML path.
- **CSS in a global stylesheet.** Means the block can't be lifted into a different site. Keep CSS with the renderer.
- **Data fetched at runtime.** Breaks `file://`. All block data arrives in `data`.
- **Authors writing HTML inside `data.body`.** Defeats the point of the block layer. If you need rich body content, define the structured fields the renderer needs (e.g. `items: [{ label, body }]`), not raw HTML strings. Reserve raw HTML for the `custom` escape hatch.
- **Markdown-formatted strings inside YAML.** If a field is supposed to render as Markdown (e.g. a callout body), document this clearly in the block's `.md`, run the compiler's Markdown step on it before passing to the renderer, and never make the renderer parse Markdown itself.
- **Two blocks claiming the same DOM `id`.** The compiler must deduplicate or fail loudly.

## Quality Invariants Every Renderer Honours

These are page-contract obligations every block inherits. They are non-negotiable:

- **No text overflow.** Set `min-width: 0` on every flex/grid child you create. The page shell sets `overflow-wrap: anywhere` globally; renderers should not undo that.
- **No horizontal scroll spilling to the page.** If a block legitimately needs horizontal scrolling (wide tables, long code), set `overflow-x: auto` on the *contained* element, never on the block root that affects parent layout.
- **No diagram edge crosses an unreadable label.** Any block that draws SVG edges must use orthogonal routing (or guarantee bezier paths don't cross), stagger edges that share a gutter, place labels on segments where they don't cross other paths, and back labels with a halo rect sized to the text bbox.
- **Idempotent.** `mount(root, data)` called twice on the same root must produce the same DOM. The renderer may clear `root.innerHTML` on entry.
- **Print-readable.** Static-mode renderings should print cleanly. Interactive renderers degrade to their static representation in print where possible.

These rules are codified in [`../page-contract.md`](../page-contract.md). Read that document if you're authoring a shell or extending a renderer.

## Relationship To Existing Skill Layers

- **Content model** (`content-model.md`) defines the page-level schema. Blocks slot into the `blocks:` array on a page.
- **Archetypes** (`archetype-recipes.md`, `design-options.md`) describe whole-document patterns. The new `composed-blocks` archetype is the one whose deliverable IS a sampler of blocks; other archetypes use blocks as ingredients.
- **Packaging** (`architecture.md`) governs how the finished site collapses into one HTML file. Blocks are designed to honour every packaging mode in that document.
- **Audit** (`scripts/audit-single-html.mjs`) checks the packaged output. It will be extended to count `custom` block usage and to verify that interactive block bootstraps were inlined.

The block layer doesn't replace any existing reference; it adds the missing middle layer between page schema and rendered HTML.
