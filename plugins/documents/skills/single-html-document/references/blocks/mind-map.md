# Block: `mind-map`

A hierarchical outline laid out spatially — a central root with branches that spread outward, like a paper mind map.

**Group:** diagram · **Default packaging:** `static` · **Markdown fields:** `root.body`, `branches[].body` (recursive)

## When To Use

When the section's value is showing how a topic decomposes into branches: planning a workshop, breaking a research question into sub-questions, scoping a project, mapping out the regions of an idea space. Mind maps are best when the relationships are purely parent → child and there's a single anchor topic.

For networks of ideas with relationships in multiple directions and labelled connections, use [`concept-map`](concept-map.md). For temporal sequences use [`timeline`](timeline.md). For execution flow with decisions use [`flowchart`](flowchart.md).

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the map. |
| `direction` | enum: `radial`, `right`, `horizontal` | no | `radial` spreads branches around the root. `right` puts the root on the left and branches grow rightward (like an outline). `horizontal` mirrors children to both sides of the root. Default `horizontal`. |
| `root` | object | yes | The central node. |
| `root.label` | string | yes | The central topic. |
| `root.body` *(markdown)* | string | no | Optional one-line context. Renders to `bodyHtml`. |
| `root.icon` | string | no | Icon name from the catalogue. |
| `branches` | array of branch objects | yes | Top-level children of the root. |
| `branches[].label` | string | yes | Branch heading. |
| `branches[].body` *(markdown)* | string | no | One-liner shown beneath the label. Renders to `bodyHtml`. |
| `branches[].icon` | string | no | Icon name from the catalogue. |
| `branches[].kind` | enum: `info`, `success`, `warning`, `danger`, `key`, `neutral` | no | Tints the branch border. |
| `branches[].children` | array of branch objects | no | Recursive: branches can have children of their own. Two levels of children render cleanly; deeper trees should use `concept-map` or split into multiple maps. |

## Example

```yaml
- type: mind-map
  data:
    title: "Scoping the workshop"
    direction: horizontal
    root:
      label: "AI in higher education"
      body: "1-day workshop, ~30 participants"
    branches:
      - label: "Pedagogy"
        kind: info
        icon: book-open
        children:
          - { label: "Assessment redesign" }
          - { label: "Plagiarism vs. authorship" }
          - { label: "AI literacy curriculum" }
      - label: "Operations"
        kind: success
        icon: layers
        children:
          - { label: "Tooling procurement" }
          - { label: "Staff training programme" }
      - label: "Risk and policy"
        kind: warning
        icon: shield-alert
        children:
          - { label: "Data protection (GDPR)" }
          - { label: "Equitable access" }
          - { label: "Compliance reporting" }
```

## Rendering

Branches lay out around the root using a CSS grid. SVG edges connect each branch to the root with smooth curves. Children of branches stack beneath their branch, indented. Each branch carries its `kind` colour as a left rail (or border) so the categorisation is visible at a glance.

The root sits on its own card, prominent. Long labels wrap rather than overflow.

## Layout Notes

The renderer does not perform automatic layout — branches lay out in declaration order around the root. For a balanced visual, alternate branches between top/bottom or left/right based on `direction`.

For trees deeper than two levels of children, the visual gets crowded. Either split into multiple mind maps or switch to a `concept-map` where the relationships can be more flexible.
