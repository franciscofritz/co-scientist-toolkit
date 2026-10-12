# Page Contract

The block protocol governs individual blocks. The page contract governs how the document containing them behaves. Every deliverable produced by this skill must honour these rules — they're below the level of design choice and should be inherited by every archetype, manifest, and sample.

## Why This Exists

Blocks can be perfectly designed in isolation and still produce an unreadable page if the page chrome is sloppy: text spilling beyond the viewport, sideways scrolling on mobile, no way to navigate to a section, edge labels in diagrams unreadable on top of crossing lines. Those problems aren't block bugs — they're contract violations. Codify the contract once so every renderer and every page shell inherits it.

## Required Properties

### 1. Section navigation by default

Any deliverable longer than a single short article must expose a sidebar table of contents. The TOC sticks to the viewport on wide screens and is reachable from a button on narrow screens. Each section gets a stable id; clicking a TOC entry jumps with smooth scroll and updates the URL hash.

This means: a deliverable behaves like a multi-page site without actually being one. Readers can ⌘-F across all sections and they can deep-link to a specific section by URL.

The TOC is implemented as a page pattern (`scripts/patterns/toc.js`), not by the build shell directly. Manifests opt in via the `patterns` field. Pattern options include depth (h2 only, or h2+h3, or h2+h3+h4), in-TOC search, and a single-key shortcut (default `T`). See [`patterns/toc.md`](patterns/toc.md).

Long deliverables should also opt into the global search pattern (`/` opens a fuzzy search overlay) and the keyboard-help pattern (`?` lists active shortcuts). See [`patterns/_protocol.md`](patterns/_protocol.md) for the full pattern layer.

### 2. No horizontal scroll at the page level, ever

The body element has `overflow-x: clip`. The page shell has `max-width: 100%` and `min-width: 0`. Every flex and grid child in the shell has `min-width: 0` so that overflowing content forces wrapping rather than expanding the parent.

Blocks default to **reflow over horizontal scroll**. Code blocks (`tabbed-code`, `annotated-diff`, the optional `code` field on `before-after`) wrap long lines by default using `white-space: pre-wrap` plus `overflow-wrap: anywhere`. This is deliberate: vertical scroll is normal browser behaviour; horizontal scroll inside a block is friction.

When the author or reader genuinely needs the no-wrap form (preserving alignment in indented YAML, ASCII art, terminal output where each line should stay on its own line), the block exposes a small **No wrap / Wrap** toggle. Clicking switches the block to `white-space: pre` plus `overflow-x: auto` *inside the block*. The page itself still never scrolls sideways. State is per-block instance and not persisted; the next block instance still starts in the wrap default.

When a block has content that intrinsically cannot wrap (a wide image, a fixed-aspect diagram), it sets `overflow-x: auto` on a contained element from the start. The shell never compromises.

### 3. No text overflow inside any block

Every block container inherits `overflow-wrap: anywhere` and `min-width: 0`. Renderers should not need to opt in. When a long URL, an unbreakable identifier, or a wide piece of inline content would otherwise overflow, the page shell forces it to wrap.

If a renderer adds its own flex or grid layout, the renderer is responsible for setting `min-width: 0` on its children. This is documented in the protocol as part of the renderer contract.

### 4. No diagram edge crosses an unreadable label

Any block that draws edges (flowchart, module-map, mind-map, concept-map) must:

- Use orthogonal or otherwise predictable routing — bezier curves are allowed only when the path geometry guarantees no overlap with other content.
- Stagger edges that share a gutter so multiple edges in the same column don't stack.
- Place labels on path segments where they don't cross perpendicular paths.
- Back labels with a halo (a `<rect>` sized to the text bounding box, filled in the page background colour) so they remain readable when an unrelated path passes behind them.
- Place arrowheads on the target side, sized so they remain visible at small zoom levels.

The shared edge-routing helper in `scripts/blocks/_edges.js` (added when the next graph block lands) implements all of the above. Use it from any new block that draws edges instead of reimplementing routing per block.

### 5. Print-readable

Every page should be printable from the browser without losing structure. The TOC may collapse or hide in print; section headings must remain visible; section anchors must work as cross-references; interactive blocks degrade to their static form (the renderer's `packaging: static` representation).

### 6. Offline-safe

All page-level resources (fonts, icons, scripts, images) must be inlined. The page contract inherits this from the architecture rules and the audit script enforces it. No CDN, no external fonts, no remote stylesheets.

## What The Build Shell Provides

The shell that `build-block-sample.mjs` emits implements the contract automatically:

- `body { overflow-x: clip }`
- The page-shell container with `min-width: 0` cascading down through its descendants
- A sidebar TOC generated from `<h2>` headings inside `section.sample-section[id]`
- Smooth-scroll behaviour on hash navigation
- Print stylesheet that hides the TOC and lets sections flow naturally
- Hooks for renderers that need to opt out (e.g. a deliberately-wide code listing) by adding `data-allow-overflow` to the block root; the shell respects that flag.

If you build a different shell (your own React app, a hand-written HTML page) the same rules apply. Use the shell's CSS as a starting reference; the rules are not optional.

## What Authors Have To Do

Almost nothing. Author the manifest with `id` on every section that should appear in the TOC and you're done. The shell emits everything else.

If a section deliberately should not appear in the TOC, omit `id` (or pass `tocHidden: true` on the section). If a section should have a TOC label different from its `<h2>` text, add `tocLabel: "Short label"` on the section.

## Verifying The Contract

Run the audit script after packaging. The standard audit catches the offline-safe violations. For the layout-and-overflow rules, open the deliverable on a narrow viewport (~360px) and verify:

- No horizontal scrollbar appears on the body.
- Every block fits its width or scrolls only inside itself.
- Long words and URLs wrap.
- The TOC remains reachable.
- Diagram labels remain legible.

These checks are not yet automated; they're a manual checklist for now.
