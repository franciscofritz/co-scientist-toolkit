# Page Pattern Protocol

The block layer governs *content* — typed pieces of structured authoring, each rendered the same way every time. The pattern layer governs *page features* — table of contents, global search, keyboard shortcuts, breadcrumbs, footnotes, and other affordances that operate at the level of the whole document rather than at any single block.

Read this if you are adding a new pattern, extending an existing one, or deciding whether a feature belongs in the block layer or the pattern layer.

## Why A Separate Layer

Blocks are content. They have data, they have a renderer, they appear inside the document body. Patterns are page chrome. They have a behaviour, they wire onto `document` or `window`, they listen for keyboard shortcuts, they show overlays, they read the rendered DOM. Forcing them into the block layer pushes whole-document behaviour into per-block renderers, which is the wrong shape.

A separate layer also gives the build a clear tree-shake target: the manifest declares which patterns the deliverable opts into; the build inlines only those patterns; pages that don't need search don't pay for it.

## File Layout

Every pattern named `<name>` lives in three colocated files:

```
references/patterns/<name>.md          spec, options, when-to-use, examples
scripts/patterns/<name>.js             init({ options }) module
references/patterns/<name>.example.yml configuration example                (optional)
```

The shape mirrors blocks for consistency, with the example file optional for patterns whose configuration is too small to merit one.

## Manifest Shape

A manifest opts into patterns under a top-level `patterns` field:

```js
const manifest = {
  // ...title, sections, etc...
  patterns: {
    toc: {
      enabled: true,
      depth: 3,         // include h2 and h3 in the TOC
      search: true,     // show search box inside the TOC
    },
    'global-search': {
      enabled: true,
      shortcut: '/',
      altShortcut: '\\\\',
    },
    'keyboard-help': {
      enabled: true,
    },
  },
};
```

Patterns not listed are simply not included. Patterns listed with `enabled: false` are also excluded — useful for templates that declare the canonical option set with feature flags.

## Init Contract

Every pattern's JS module exports a single `init` function:

```js
// scripts/patterns/<name>.js
export function init(options) {
  // options: the pattern's config object from the manifest's `patterns` map
  // Returns: undefined. Side effects only (event listeners, DOM mutation).
}
```

Rules the contract enforces:

- **Idempotent.** `init` may be called once. Patterns that need teardown (rare) should not be re-init-able without explicit opt-in.
- **DOMContentLoaded-aware.** The pattern is responsible for waiting for `DOMContentLoaded` if it needs to read the rendered DOM. The build's pattern bootstrap calls `init` after the block bootstrap so blocks have already mounted.
- **Pure vanilla.** No framework imports, no runtime fetch, no global state shared across patterns. Patterns may register on `window` if they want to expose a public API (e.g. `window.__pageToc.open()`), but they must namespace under `__page<Name>`.
- **Self-contained styling.** Required CSS lives in the pattern module (injected via a `<style>` element) so the pattern works in any host that adopts it.
- **Shortcut-safe.** Keyboard shortcuts must respect editable contexts: ignore the shortcut when focus is in an `<input>`, `<textarea>`, or `[contenteditable]` element unless the user explicitly asks otherwise.
- **No race with other patterns.** Patterns do not directly call into each other. If `toc` and `global-search` both need to open an overlay, they coordinate through DOM state (e.g. `body[data-overlay-open]`) and Esc handling, not by importing from each other.

## Build Pipeline

`scripts/build-block-sample.mjs` walks the manifest's `patterns` map, loads each enabled pattern's module, concatenates them after the block bootstrap, and writes a small invocation block that calls `init(options)` for each enabled pattern. The DOM scaffolding each pattern needs (the TOC sidebar, the search overlay, the keyboard-help dialog) is injected by the pattern itself; manifests don't author it.

## When To Add A Pattern Vs. Extend One

Add a new pattern when:

- The feature needs whole-page state (search index, scroll position, current focus).
- The feature owns a keyboard shortcut.
- The feature has its own visible overlay or sidebar.

Extend an existing pattern when:

- The feature is an option on the same UI surface (e.g. multi-level TOC vs. flat TOC is one pattern, two options).
- The feature shares state with an existing pattern (e.g. "jump to section" can live inside the TOC, not in its own pattern).

## Anti-Patterns

- **Wiring directly to `document.body` from inside a block renderer.** Patterns own the page chrome; blocks own their own DOM subtree. A renderer that reaches up to `document.body` is leaking out of its scope and probably wants to be a pattern.
- **Patterns that read block payloads.** Patterns work on the rendered DOM, not on the original manifest data. If a pattern needs structured info (e.g. section ids), expose it via DOM attributes, not by re-parsing the manifest at runtime.
- **Per-pattern keyboard listeners that don't gate on editable focus.** The user typing into a `<textarea>` should not trigger the TOC.
- **Patterns that hard-fail when their target DOM doesn't exist.** A pattern targeting `<h2>` when the page has none should no-op silently, not throw.

## Relationship To Other Layers

- **Page contract** (`page-contract.md`) describes the page-level invariants every deliverable honours. Patterns are *how* some of those invariants ship — for example, the contract requires section navigation; the `toc` pattern is the implementation.
- **Block protocol** (`blocks/_protocol.md`) describes block-level rendering. Patterns and blocks coexist on the same page but never share modules.
- **Architecture** (`architecture.md`) describes the build pipeline. Patterns flow through that pipeline as additional inlined modules.
