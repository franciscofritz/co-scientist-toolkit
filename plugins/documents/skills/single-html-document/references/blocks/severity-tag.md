# Block: `severity-tag`

A catalogue of severity tag pills with semantics and usage notes.

**Group:** comparison · **Default packaging:** `static` · **Markdown fields:** `tags[].description`

## When To Use

When the document defines its own severity vocabulary and readers need to know what each tag *means* in this context. Common settings: incident reports defining `P0/P1/P2/P3`, design reviews defining `must-fix / nit / discussion`, code reviews defining `blocking / suggestion / question`, audit reports defining `critical / major / minor / informational`.

The block renders as both a definition catalogue and a reusable token reference. Other blocks (`annotated-diff`, callouts, timeline events) can reference the same tag names so the visual vocabulary stays consistent across the document.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the catalogue. |
| `layout` | enum: `grid`, `list` | no | Default `grid`. `list` stacks tag + description rows. |
| `tags` | array of tag objects | yes | At least two. |
| `tags[].name` | string | yes | Tag identifier. Becomes the displayed label by default. |
| `tags[].label` | string | no | Display label override. |
| `tags[].tone` | enum: `info`, `success`, `warning`, `danger`, `key`, `neutral` | yes | Drives colour. |
| `tags[].description` *(markdown)* | string | yes | What the tag means in this document. Renders to `descriptionHtml`. |
| `tags[].when` | string | no | Short "when to apply" phrase. |
| `tags[].sla` | string | no | Optional response-time or follow-up rule. |

## Example

```yaml
- type: severity-tag
  data:
    title: "Severity vocabulary used in this report"
    layout: grid
    tags:
      - name: "P0"
        tone: danger
        description: "Customer impact, no workaround. Drop everything."
        when: "Active outage, data loss, or compliance breach."
        sla: "Response under 15 min, mitigation under 1 h."
      - name: "P1"
        tone: warning
        description: "Customer impact with workaround, or imminent risk of outage."
        when: "Degraded service, escalating error rates."
        sla: "Response under 1 h, mitigation under 4 h."
      - name: "P2"
        tone: info
        description: "Not customer-facing yet, but should be addressed this sprint."
        when: "Internal warning thresholds tripped, single-replica failures."
        sla: "Response under 1 day."
      - name: "P3"
        tone: neutral
        description: "Tracked but not prioritised."
        when: "Minor noise, cosmetic issues."
```

## Rendering

Grid layout: each tag renders as a tone-coloured pill with the description, "when", and SLA stacked beneath. List layout: tag pill on the left, description on the right.

The renderer also writes a small CSS rule per tag name (`.tag-<name>` ➜ tone colour) so other blocks in the same document can reference the tag visually with `<span class="tag-P0">P0</span>`. This is what makes the catalogue genuinely reusable across the document rather than just a definition table.
