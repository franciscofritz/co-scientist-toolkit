# Block: `toggle-deps`

A grouped toggle list with dependency and conflict checking and a "copy diff" export.

**Group:** interactive · **Default packaging:** `interactive` · **Markdown fields:** `toggles[].description`

## When To Use

When the section presents a configurable system — feature flags, opt-in modules, build-time options, audit checks — and readers should be able to explore which combinations make sense. The block warns when a toggle is on but its dependency is off, or when two conflicting toggles are both on.

The "copy diff" button exports the current toggle state as YAML so readers can paste the result into a real config file.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the toggles. |
| `groups` | array of `{id, label}` | no | Optional named groups. Toggles with a matching `group` id render under the group header. |
| `toggles` | array of toggle objects | yes | At least one. |
| `toggles[].id` | string | yes | Stable identifier referenced by dependencies and conflicts. |
| `toggles[].label` | string | yes | Display label. |
| `toggles[].default` | boolean | no | Initial state. Default `false`. |
| `toggles[].group` | string | no | Group id. |
| `toggles[].description` *(markdown)* | string | no | Renders to `descriptionHtml` beneath the label. |
| `toggles[].dependencies` | array of toggle ids | no | This toggle requires all of these to be on. |
| `toggles[].conflicts` | array of toggle ids | no | This toggle conflicts with any of these being on. |

## Example

```yaml
- type: toggle-deps
  packaging: interactive
  data:
    title: "Build options"
    groups:
      - { id: assets,   label: "Assets" }
      - { id: delivery, label: "Delivery" }
    toggles:
      - id: inlineImages
        group: assets
        label: "Inline images as Base64"
        default: true
        description: "Required for offline `file://` delivery."
      - id: gzipPayload
        group: assets
        label: "Compress text payloads with gzip"
        default: false
        dependencies: ["inlineImages"]
        description: "Best with text-heavy reports. Requires inline images for the bootstrap to work."
      - id: cdnAssets
        group: delivery
        label: "Pull fonts from a CDN"
        default: false
        conflicts: ["inlineImages"]
        description: "Faster initial paint but breaks offline delivery."
```

## Rendering

A list of toggles, grouped under their `groups` headers if any. Each toggle has a switch, a label, an inline description, and (when applicable) a coloured warning indicating the unmet dependency or active conflict. The "copy diff" button at the bottom serialises the toggle state to YAML and copies to the clipboard.

When `packaging: static`, the block renders the toggles in their default state, with descriptions but without the switch interactivity.
