# Block: `concept-map`

A network of nodes connected by labelled edges. Every relationship is named; there is no central root.

**Group:** diagram · **Default packaging:** `static` · **Markdown fields:** `nodes[].body`

## When To Use

When the section's value is showing how concepts relate to each other in multiple directions: theory of change, dependency graphs between ideas, propositions ("X *causes* Y", "A *is part of* B", "P *contradicts* Q"), domain models, pedagogy maps. Concept maps differ from mind maps because the relationships themselves carry meaning — the verb on each edge matters as much as the nodes.

For a single-anchor topic with parent → child relationships, use [`mind-map`](mind-map.md). For a process flow with decisions, use [`flowchart`](flowchart.md). For a system architecture with stable layers, use [`module-map`](module-map.md).

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the map. |
| `nodes` | array of node objects | yes | At least two. |
| `nodes[].id` | string | yes | Stable identifier referenced by edges. |
| `nodes[].label` | string | yes | Concept label inside the node. |
| `nodes[].body` *(markdown)* | string | no | One-line elaboration. Renders to `bodyHtml`. |
| `nodes[].col` | integer ≥ 0 | yes | Grid column (0-indexed, left to right). |
| `nodes[].row` | integer ≥ 0 | yes | Grid row (0-indexed, top to bottom). |
| `nodes[].kind` | enum: `info`, `success`, `warning`, `danger`, `key`, `neutral` | no | Tints the node border. |
| `nodes[].icon` | string | no | Icon name from the catalogue. |
| `edges` | array of edge objects | yes | At least one. **All edges must have a `label`** — that is the point of a concept map. |
| `edges[].from` | string | yes | Source node id. |
| `edges[].to` | string | yes | Target node id. |
| `edges[].label` | string | yes | The relationship — the proposition's verb phrase. |
| `edges[].kind` | enum: `causes`, `partOf`, `dependsOn`, `contradicts`, `example`, `enables`, `default` | no | Drives stroke style. Default `default`. |

## Example

```yaml
- type: concept-map
  data:
    title: "Why authoring blocks separately matters"
    nodes:
      - { id: blocks,    label: "Typed blocks",         col: 0, row: 0, kind: key,     icon: package }
      - { id: schema,    label: "Strict schema",        col: 0, row: 1, kind: success }
      - { id: drift,     label: "Renderer/spec drift",  col: 1, row: 0, kind: danger,  icon: alert-triangle }
      - { id: reuse,     label: "Reuse across pages",   col: 1, row: 1, kind: info }
      - { id: agent,     label: "LLM authorability",    col: 2, row: 0, kind: success, icon: zap }
      - { id: maintainability, label: "Long-term maintainability", col: 2, row: 1, kind: success }
    edges:
      - { from: blocks,  to: schema,           label: "is governed by", kind: dependsOn }
      - { from: blocks,  to: reuse,            label: "enables",         kind: enables }
      - { from: schema,  to: drift,            label: "prevents",        kind: contradicts }
      - { from: schema,  to: agent,            label: "improves",        kind: causes }
      - { from: reuse,   to: maintainability,  label: "supports",        kind: causes }
      - { from: drift,   to: maintainability,  label: "undermines",      kind: contradicts }
```

## Rendering

Nodes lay out in a CSS grid based on their `(col, row)` coordinates. SVG edges connect nodes with orthogonal-or-diagonal paths and arrowheads pointing at the target. Edge labels render with a halo background sized to the text bbox so the label is readable even when other paths pass behind it.

The renderer does not perform automatic layout — authors specify positions explicitly. This keeps the visual reproducible and predictable across renders. For complex graphs (more than ~10 nodes), split into multiple maps or pre-compute positions in the compiler.

## Edge Kind Strokes

| Kind | Stroke | Suggests |
|---|---|---|
| `causes` | solid | Direct causal influence ("X causes Y"). |
| `partOf` | solid double | Composition ("Y is part of X"). |
| `dependsOn` | solid | Functional dependency. |
| `contradicts` | dashed in red | Negation, tension, opposition. |
| `example` | dotted | Exemplification. |
| `enables` | solid with double-arrow | Permits or enables. |
| `default` | solid | Generic relationship. |

## Authoring Note

Every edge must have a `label`. An unlabelled edge in a concept map is a tell that the author wasn't sure what the relationship was — and that ambiguity should be resolved before publishing, not papered over with a blank arrow. The compiler emits a warning when an edge label is missing or empty.
