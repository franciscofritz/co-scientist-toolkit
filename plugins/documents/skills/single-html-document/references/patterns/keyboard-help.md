# Pattern: `keyboard-help`

A `?` overlay that lists every keyboard shortcut active on the current page.

## When To Use

Any deliverable that opts into other keyboard-driven patterns (TOC, global search, future patterns). The help overlay is the discoverability path for a power-user reader who wonders "what shortcuts does this page have?".

## Options

| Option | Type | Default | Notes |
|---|---|---|---|
| `enabled` | boolean | `true` | Set `false` to opt out. |
| `shortcut` | string | `"?"` | Single character that opens the help overlay. |
| `entries` | array | `[]` | Manually-declared entries the manifest wants to show. The pattern also registers entries on its own (for `?`) and accepts entries from other patterns at runtime. |

Each entry in `entries` is an object with `keys` (display string) and `label`:

```js
{ keys: 'T',   label: 'Open contents' },
{ keys: '/',   label: 'Search the page' },
{ keys: 'Esc', label: 'Close any open overlay' },
```

For multi-key combos, separate keys with ` + ` (e.g. `keys: 'Cmd + K'`).

## Manifest Example

```js
patterns: {
  'keyboard-help': {
    enabled: true,
    entries: [
      { keys: 'T',   label: 'Open contents' },
      { keys: '/',   label: 'Search the page' },
      { keys: '\\\\',  label: 'Search the page (alt)' },
      { keys: 'Esc', label: 'Close any open overlay' },
    ],
  },
}
```

## Behaviour

- `?` opens or closes the overlay.
- `Esc` closes it.
- Click outside the panel closes it.
- The shortcut is ignored while focus is in an input or contenteditable.

## Public API

```js
window.__pageKeyboardHelp.open();
window.__pageKeyboardHelp.close();
window.__pageKeyboardHelp.toggle();
window.__pageKeyboardHelp.register({ keys: 'X', label: 'Custom action' });
```

`register` is the integration point for other patterns: instead of duplicating shortcut documentation in the manifest, a pattern can register its own help entries when it initialises. The keyboard-help overlay shows the union of manifest-declared and runtime-registered entries.
