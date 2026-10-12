# Icons

Blocks reference icons by name (`icon: "shield-alert"`). The build pipeline resolves the name to a Lucide-style SVG and inlines only the icons actually used into the packaged output. Authors get a wide selection without paying for icons they don't reference.

## Why By Name, Not By SVG

When authors paste raw SVG into block data, three things tend to go wrong: the SVGs drift visually because each is hand-drawn, semantic intent gets lost (the author chose the icon for a reason — the next reader can't tell why), and the same icon ends up redrawn five different ways across a deliverable.

By-name references fix all three: the icon is whatever Lucide says `shield-alert` is, the *name* documents intent, and identical references emit identical SVG.

## How To Use An Icon In A Block

Any block whose schema declares an `icon` field accepts a name from the catalogue. Examples:

```yaml
- type: callout
  data:
    tone: warning
    icon: shield-alert            # ← name, not SVG
    title: "Compliance reminder"
    body: "Tokens must rotate every 90 days."
```

The build pipeline sees `icon: "shield-alert"`, looks up the SVG in `scripts/icons.mjs`, and writes the result back as `iconHtml` so the renderer receives ready-to-mount markup. Renderers also fall back to a runtime lookup via `window.__blocksIcon('name')` when authored HTML in the page references icons directly.

If an icon name is not in the catalogue, the build logs a warning and the renderer falls back to either the explicit `icon` glyph or the block's tone default. No silent drop.

## Catalogue

The current catalogue lives in [`../scripts/icons.mjs`](../scripts/icons.mjs). It covers a curated set of common icons grouped by purpose:

- **Status / severity** — `info`, `check`, `check-circle`, `x`, `x-circle`, `alert-triangle`, `alert-octagon`, `shield-alert`, `shield-check`, `star`, `key`, `lightbulb`, `zap`
- **Direction** — `arrow-up`, `arrow-down`, `arrow-left`, `arrow-right`, `chevron-up`, `chevron-down`, `chevron-left`, `chevron-right`
- **Documents** — `file-text`, `file-check`, `file-warning`, `clipboard-list`, `scroll-text`, `book-open`
- **People** — `user`, `users`
- **Time** — `calendar`, `calendar-days`, `clock`
- **Communication** — `message-circle`, `mail`
- **Tech** — `code`, `terminal`, `database`, `server`, `git-branch`, `package`, `layers`, `box`, `network`
- **Actions** — `download`, `upload`, `link`, `external-link`, `search`, `copy`, `edit`, `trash`, `plus`, `minus`, `eye`, `eye-off`
- **Concepts** — `target`, `bar-chart-2`, `trending-up`, `trending-down`

Run `node -e "import('${CLAUDE_SKILL_DIR}/scripts/icons.mjs').then(m => console.log(m.ICON_NAMES.join(\\"\\n\\")))"` to dump the canonical list.

## Adding More Icons

The catalogue is intentionally small at the start so you only carry what's used. To add an icon:

1. Find it on [Lucide](https://lucide.dev/icons). Lucide is under the ISC licence, and the icons it derived from Feather under MIT; the notice is in `LICENSE-lucide` in this skill's folder.
2. Open the source SVG (any of `src/icons/<name>.svg` in the Lucide repo, or copy from the icon page).
3. Append a new entry to `scripts/icons.mjs` using the same `svg('<path .../>')` helper. Only the inner body — the helper wraps the standard Lucide root attributes.
4. Reference the name from a manifest, rebuild, verify.

Stay close to Lucide's naming convention so search remains discoverable.

## How The Tree-Shake Works

The build script:

1. Walks every block's `data` recursively, looking for any string-valued field whose key is `icon` or ends in `Icon`.
2. Resolves each name against the catalogue. Misses log a warning.
3. Writes the resolved SVG back as `iconHtml` (or `<key>Html`) so renderers receive HTML-ready content.
4. Builds an inline runtime that exposes `window.__blocksIcon(name)` over a small dictionary containing **only the names referenced in this manifest**.
5. Inlines the runtime into the packaged HTML.

If the manifest references zero icons, the icon runtime is omitted entirely. This keeps the packaged file lean for icon-free deliverables.

## Renderer Convention

Renderers that support icons follow a small contract:

- The schema field is `icon` (string, optional).
- The compiler writes `iconHtml` when the name resolves.
- The renderer prefers `iconHtml` if present, falls back to `window.__blocksIcon(data.icon)` for runtime-set values, falls back to the renderer's default glyph if neither.
- The icon's outer SVG inherits its colour via `currentColor` and is sized through CSS — never via inline `width`/`height` attributes set by the renderer (those would override the catalogue's defaults).

Currently `callout` honours this. `timeline`, `glossary`, `severity-tag`, and `module-map` are good candidates to extend in subsequent passes; their schemas already have spaces where an icon would fit naturally (event status, term type, tag tone, module kind).

## Compatibility With React Hosts

When the host site is a Vite/React app, it can use `lucide-react` for icons in its own components and reference the same names from manifests. The build script's catalogue and the React imports stay aligned because they share the Lucide source convention.
