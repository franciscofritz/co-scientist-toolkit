# Block: `flowchart`

A node-and-edge diagram with optional click-reveal node details.

**Group:** diagram · **Default packaging:** `interactive` · **Markdown fields:** `nodes[].body`

## When To Use

When the section explains a process, decision tree, or execution path that has more than one branch. Examples: a request flow with retry/fallback paths, a decision tree for choosing between options, a workflow that involves both human and automated steps.

For purely linear sequences, prefer the `timeline` block. For static system architecture (no flow direction), use `module-map`.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the diagram. |
| `direction` | enum: `top-down`, `left-right` | no | Layout direction. Default `top-down`. |
| `nodes` | array of node objects | yes | Each node placed by `lane` and `order`. |
| `nodes[].id` | string | yes | Stable identifier. Referenced by edges. |
| `nodes[].label` | string | yes | Short label shown inside the node. |
| `nodes[].lane` | integer ≥ 0 | yes | Column for `top-down` (or row for `left-right`). |
| `nodes[].order` | integer ≥ 0 | yes | Row for `top-down` (or column for `left-right`). |
| `nodes[].kind` | enum: `step`, `decision`, `terminal` | no | Default `step`. |
| `nodes[].body` *(markdown)* | string | no | Click-reveal details. Renders to `bodyHtml`. |
| `nodes[].timing` | string | no | Optional timing/duration label shown beneath the node. |
| `nodes[].status` | enum: `info`, `success`, `warning`, `danger` | no | Tints the node border. |
| `edges` | array of edge objects | yes | At least one edge. |
| `edges[].from` | string | yes | Source node id. |
| `edges[].to` | string | yes | Target node id. |
| `edges[].label` | string | no | Short label on the edge (e.g. condition). |

## Example

```yaml
- type: flowchart
  data:
    title: "Token validation"
    direction: top-down
    nodes:
      - { id: req,    label: "Incoming request",   lane: 0, order: 0, kind: terminal }
      - { id: parse,  label: "Parse JWT",          lane: 0, order: 1 }
      - { id: ok,     label: "Signature valid?",   lane: 0, order: 2, kind: decision }
      - { id: cache,  label: "Cache validation",   lane: 0, order: 3, status: success }
      - { id: reject, label: "Reject 401",         lane: 1, order: 3, kind: terminal, status: danger,
          body: "Logged with reason and request id; alerting fires only above threshold." }
    edges:
      - { from: req,   to: parse }
      - { from: parse, to: ok }
      - { from: ok,    to: cache,  label: "yes" }
      - { from: ok,    to: reject, label: "no" }
```

## Rendering

The renderer draws nodes in a CSS grid based on `lane` and `order`, then overlays an absolutely-positioned SVG layer for edges. Edges are simple orthogonal paths that route around the grid.

When `packaging: interactive`, clicking a node toggles a details panel beneath the diagram showing `body`, `timing`, and `kind`. The details panel keeps focus management for keyboard users.

When `packaging: static`, click-reveal degrades to all bodies rendered inline beneath the diagram.

## Layout Notes

The renderer does not auto-layout. Authors specify `lane` and `order` explicitly. This keeps diagrams predictable and reproducible across renders. For complex graphs, generate the lane/order assignment in the compiler from a layered-DAG layout if needed.
