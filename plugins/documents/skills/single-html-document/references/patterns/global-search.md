# Pattern: `global-search`

A keyboard-first overlay that searches all visible text in the page and lets the reader jump to a match.

## When To Use

For deliverables long enough that the TOC alone isn't sufficient — long handbooks, research syntheses, dossiers, anything where the reader will think "where did they say *X*?". The pattern makes that recall friction-free: hit `/`, type, jump.

## Options

| Option | Type | Default | Notes |
|---|---|---|---|
| `enabled` | boolean | `true` | Set `false` to opt out. |
| `shortcut` | string | `"/"` | Primary single-character shortcut. |
| `altShortcut` | string | `"\\"` | Optional secondary shortcut. Set `""` to disable. |
| `showLauncher` | boolean | `true` | Show a floating search button (bottom-right, beside the back-to-top circle). Set `false` for keyboard-only access. |

## Manifest Example

```js
patterns: {
  'global-search': {
    enabled: true,
    shortcut: '/',
    altShortcut: '\\',
  },
}
```

## Behaviour

- Opens on shortcut from anywhere on the page (ignored when focus is in an input or contenteditable).
- Index built lazily from `section[id]` elements on first open. Each section becomes a search unit (heading + body text).
- Matches ranked: title hits first, body hits second. Top 30 results shown.
- Match terms get inline `<mark>` highlights in both title and excerpt.
- Keyboard:
  - `↑` / `↓` move through results.
  - `Enter` jumps to the highlighted result.
  - `Esc` closes the overlay.
  - Click outside the panel also closes.
- Jumping to a match scrolls smoothly and briefly flashes the target section so the reader can find their place.

## Public API

```js
window.__pageSearch.open();
window.__pageSearch.close();
window.__pageSearch.toggle();
```

## Why Section-Level And Not Token-Level

Block-level or paragraph-level indexing would give finer-grained results, but it would also require either a build-time index or a much heavier runtime. Section-level matches are good enough for navigation in a single document; the reader who finds the right section can then use the browser's native ⌘-F to find the exact paragraph.

If a future deliverable wants paragraph-level results, that's a different pattern (`global-search-fine` or similar) that builds an index in the compiler and ships it as JSON. The current pattern stays simple.

## Coordination With Other Patterns

- The TOC pattern owns the `T` shortcut; this pattern owns `/` and `\`. They never collide.
- Both honour `Esc` to close.
- Both ignore shortcuts while focus is in an editable element.
- The launcher button sits at `bottom-right`, offset by the back-to-top circle so they don't stack.
