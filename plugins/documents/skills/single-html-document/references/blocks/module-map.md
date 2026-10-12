# Block: `module-map`

A boxes-and-arrows view of a system's modules and how they connect.

**Group:** diagram · **Default packaging:** `static` · **Markdown fields:** `modules[].summary`

## When To Use

When the section explains how a codebase, service, or workflow is structured: package layout, service-to-service dependencies, data lineage, integration topology, or the difference between hot path and cold path. Pairs well with the `flowchart` block — `module-map` for *what depends on what*, `flowchart` for *how a request flows*.

For network or call-graph diagrams with many edges, simplify before reaching for this block. Module maps work best with 4–12 modules.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the map. |
| `columns` | array of `{label}` | no | Optional named columns (e.g. "client", "service", "external"). If omitted, modules group by `column` index without headers. |
| `modules` | array of module objects | yes | At least one module. |
| `modules[].id` | string | yes | Stable identifier referenced by connections. |
| `modules[].label` | string | yes | Module name. |
| `modules[].column` | integer ≥ 0 | yes | Which column the module belongs to. |
| `modules[].kind` | enum: `package`, `entry`, `hot-path`, `external` | no | Tints the box. |
| `modules[].summary` *(markdown)* | string | no | One-line description. Renders to `summaryHtml`. |
| `connections` | array of connection objects | no | At least one connection if the map is to convey relationships. |
| `connections[].from` | string | yes | Source module id. |
| `connections[].to` | string | yes | Target module id. |
| `connections[].label` | string | no | Edge label. |
| `connections[].kind` | enum: `import`, `data`, `event` | no | Stroke style. Default `import`. |
| `legend` | boolean | no | Show kind legend. Default `true` if any module declares a non-default `kind`. |

## Example

```yaml
- type: module-map
  data:
    title: "Repo layout · single-html-document"
    columns:
      - { label: "Authoring" }
      - { label: "Build" }
      - { label: "Runtime" }
    modules:
      - { id: content,   label: "content/",         column: 0, kind: entry,    summary: "Markdown + YAML sources" }
      - { id: compiler,  label: "scripts/build*",   column: 1,                 summary: "Compiles content into typed JSON" }
      - { id: blocks,    label: "scripts/blocks/",  column: 1, kind: hot-path, summary: "Vanilla JS renderers, one per block type" }
      - { id: site,      label: "src/",             column: 2,                 summary: "Vite/React app or static HTML host" }
      - { id: bundle,    label: "report.html",      column: 2, kind: package,  summary: "Single packaged deliverable" }
    connections:
      - { from: content,  to: compiler, label: "read" }
      - { from: compiler, to: site,     label: "emit JSON" }
      - { from: blocks,   to: site,     label: "imported" }
      - { from: site,     to: bundle,   label: "package" }
```

## Rendering

A flex layout with one column per `columns` entry. Modules render as bordered boxes tinted by `kind`. Connections render as SVG paths in an overlay layer with arrowheads. Stroke style varies by connection `kind` (solid for `import`, dashed for `data`, dotted for `event`).

The block is fully static — the SVG paths are computed at render time using the laid-out box positions. No JavaScript runs after the initial render unless `packaging: interactive` is specified (in which case hovering a module highlights its connections).
