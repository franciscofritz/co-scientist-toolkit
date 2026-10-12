# Block: `drag-reorder`

A kanban-like surface where readers can drag cards between lanes and export the result.

**Group:** interactive · **Default packaging:** `interactive` · **Markdown fields:** `items[].body`

## When To Use

When the section asks the reader to make a small structured decision: triage tickets across columns, prioritise initiatives across quarters, sort options into "yes / maybe / no", or assign roles across a workshop. The "export" button serialises the lane membership back to text so the reader can paste the result into a real artefact.

The block is for *exploration*, not for production task management. Don't use it as a real backlog — its state lives only in the open tab.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the board. |
| `lanes` | array of lane objects | yes | At least two lanes. |
| `lanes[].id` | string | yes | Stable identifier referenced by `items[].lane`. |
| `lanes[].label` | string | yes | Lane header. |
| `lanes[].cap` | integer | no | Display-only cap; the renderer warns when exceeded but allows it. |
| `items` | array of item objects | yes | At least one. |
| `items[].id` | string | yes | Stable identifier. |
| `items[].label` | string | yes | Card title. |
| `items[].body` *(markdown)* | string | no | Renders to `bodyHtml` in the card body. |
| `items[].lane` | string | yes | Initial lane. Must match a `lanes[].id`. |
| `items[].tag` | string | no | Small badge in the corner. |
| `exportFormat` | enum: `markdown`, `yaml`, `text` | no | Default `markdown`. |

## Example

```yaml
- type: drag-reorder
  packaging: interactive
  data:
    title: "Sort the workshop topics"
    lanes:
      - { id: now,   label: "Cover today" }
      - { id: maybe, label: "If time" }
      - { id: skip,  label: "Skip" }
    items:
      - { id: deck-pattern, label: "Single-file deck pattern", lane: now }
      - { id: blocks,       label: "Component block layer",     lane: now }
      - { id: workbook,     label: "Feedback workbooks",        lane: maybe, tag: "long" }
      - { id: catalogue,    label: "Generated catalogue",       lane: skip }
    exportFormat: markdown
```

## Rendering

Lanes render as columns with their labels at the top and a count next to the label (with a warning indicator when `cap` is exceeded). Items render as draggable cards. The block uses native HTML5 drag-and-drop with a small set of pointer-event fallbacks for touch devices. Keyboard support: focused card + space picks up; arrow keys move; space drops.

The "Copy export" button at the bottom serialises the current lane membership in the chosen `exportFormat` and copies to the clipboard.

When `packaging: static`, the block renders the items in their initial lane positions with no drag interaction.
