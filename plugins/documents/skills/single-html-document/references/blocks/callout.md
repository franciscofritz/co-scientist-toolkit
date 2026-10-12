# Block: `callout`

A toned panel that flags a piece of prose with a severity, intent, or category.

**Group:** scaffolding · **Default packaging:** `static` · **Markdown fields:** `body`

## When To Use

Lift a sentence or short paragraph out of the body when it carries unusual weight: a recommendation, a constraint, a warning, a key decision, or a note that changes how the surrounding text should be read. Callouts are louder than emphasis but quieter than a section heading.

Don't stack callouts back-to-back as a substitute for a list — that's what the `tldr.points` field or a regular bullet list is for. One callout per idea.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `tone` | enum: `info`, `success`, `warning`, `danger`, `key`, `neutral` | yes | Drives colour and default icon. |
| `title` | string | no | Short headline. |
| `body` *(markdown)* | string | yes | One sentence or short paragraph. Renders to `bodyHtml`. |
| `icon` | string | no | Single character or short string used as the icon glyph. Defaults are tone-specific. |

## Example

```yaml
- type: callout
  data:
    tone: warning
    title: "Don't fight the release-age gate"
    body: "When `npm install foo@latest` resolves to an older version than expected, that's the seven-day buffer working — investigate the package, don't override the gate."
```

## Rendering

A bordered panel with a tone-coloured left rail, a small icon, the title in bold, and the body as flowing text. The renderer keeps icons as inline glyphs (no font/CDN dependency). Tones map to a fixed palette that respects the host theme's CSS custom properties when present.

## Tone Map

| Tone | Default icon | Use for |
|---|---|---|
| `info` | i | Neutral commentary, definitions, links to related material. |
| `success` | ✓ | Confirmed outcome, recommendation, working pattern. |
| `warning` | ! | Footgun, caveat, deferred decision. |
| `danger` | ✗ | Don't do this; this breaks something. |
| `key` | ★ | The single most important point in the section. |
| `neutral` | • | Generic emphasis when no tone fits. |
