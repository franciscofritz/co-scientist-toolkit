# Pattern: `toc`

A sidebar table of contents with optional multi-level depth, search, and keyboard navigation.

## When To Use

Any deliverable longer than a single short article. The TOC is the primary navigation affordance — readers should be able to skim, jump, search, and orient themselves without scrolling the entire document.

## Options

| Option | Type | Default | Notes |
|---|---|---|---|
| `enabled` | boolean | `true` | Set `false` to opt out without removing the pattern entry. |
| `depth` | integer (2–4) | `4` | Maximum heading depth included in the tree. The reader controls visibility at runtime via the **Show levels** footer toggle. The pattern auto-assigns ids to h3/h4 elements that don't have one. |
| `search` | boolean | `true` | Show a filter input above the list. Auto-focuses when the TOC opens. Filtering also auto-expands parent nodes of any match. |
| `shortcut` | string | `"t"` | Single character that toggles the TOC between *hidden* and *expanded*. Modifier keys are not allowed; the shortcut is ignored while focus is in an input or contenteditable. Pass `""` to disable. |
| `icon` | string | book-open SVG | Override the inline SVG used in the sidebar header and floating launcher. Must be valid `<svg>...</svg>` markup. |
| `initialExpansion` | string | `"collapsed"` | Initial state of the **Show levels** toggle. `collapsed` = only h2 visible. `depth-3` = h2 + h3. `expanded` = all levels. The reader can change this at runtime; the choice persists in `localStorage`. |

## Manifest Example

```js
patterns: {
  toc: {
    enabled: true,
    depth: 3,
    search: true,
    shortcut: 't',
  },
}
```

## Behaviour

The sidebar has three states tracked on `body[data-toc-state]`:

- `expanded` — full sidebar visible. On wide viewports the page reserves left padding for it; on narrow viewports it slides in from the left.
- `rail` — sidebar shrinks to a 3rem rail with just the icon. The collapse button toggles between rail and expanded; the close button hides entirely.
- `hidden` — sidebar not visible. A floating launcher (book-open icon, top-left) reopens it.

Each state persists in `localStorage` so the reader's preference carries across reloads.

The list is a **tree** — h2 entries with chevrons that expand or collapse their h3/h4 children. By default all chevrons start collapsed (only top-level entries visible); the **Show levels** footer toggle gives the reader three runtime options:

- **Top only** — h2 entries only. Hides every chevron's contents.
- **+ subsections** — h2 + h3 visible. h4 entries remain hidden under per-h3 chevrons.
- **All** — every level visible.

When the reader filters via the search box, parents of any matching node auto-expand so matches are reachable in the rendered tree.

A **Back to top** button sits at the bottom of the sidebar above the **Show levels** toggle. It scrolls to absolute 0 and clears the URL hash.

Section ids come from existing `section[id]` elements in the rendered DOM. h3/h4 elements without ids get one assigned of the form `<section-id>-<slug>`.

The current section highlights as the reader scrolls (IntersectionObserver, rootMargin tuned so the header band counts as "active").

### Keyboard

All keys below operate from inside the search box (the cursor naturally lands there when the sidebar opens). The pattern is a tree-style navigator, so the conventions match what readers expect from any tree view.

- `T` (configurable) anywhere on the page toggles the sidebar between *hidden* and *expanded*. Focus moves to the search box on open.
- `↑` / `↓` move the keyboard-nav highlight through visible entries.
- `→` on a collapsed parent expands it; on an already-expanded parent jumps to its first child; on a leaf does nothing.
- `←` on an expanded parent collapses it; on a leaf or collapsed parent jumps to its parent.
- `Home` / `End` jump to the first / last visible entry.
- `Enter` navigates to the highlighted section.
- `Esc` clears the search if anything is typed; otherwise hides the sidebar entirely. Esc anywhere on the page (outside an input) also hides the sidebar.

## Public API

The pattern exposes a small object on `window.__pageToc` so other code can integrate:

```js
window.__pageToc.open();           // -> expanded
window.__pageToc.close();          // -> hidden
window.__pageToc.toggle();         // hidden <-> expanded
window.__pageToc.setState('rail'); // expanded | rail | hidden
window.__pageToc.setExpansionMode('collapsed'); // collapsed | depth-3 | expanded
```

## Edge Cases

- If the page has no `section[id]` elements, the pattern silently no-ops.
- If `depth > 2` and a section has h3/h4 elements missing ids, the pattern assigns them. Pre-existing ids are respected.
- The launcher button is only visible on narrow viewports where the sidebar is hidden.
- When the TOC opens via shortcut, search auto-focuses and selects so the next keystroke replaces existing filter text.

## Why A Pattern, Not A Block

The TOC operates on the rendered DOM (reads section ids and headings), owns a global keyboard shortcut, and renders chrome (sidebar, search overlay, launcher button) outside the document body. Each of those is a smell that pushes a feature out of the block layer and into the pattern layer. See [`_protocol.md`](_protocol.md) for the full distinction.
