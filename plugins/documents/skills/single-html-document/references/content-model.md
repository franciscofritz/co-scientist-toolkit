# Content Model

## Goal

Separate content from presentation without making the content model too weak for rich single-file documents.

Plain Markdown body plus trivial front matter is not enough for reports, explainers, decks, workbooks, editable drafts, or annotation tools. Keep narrative prose in Markdown, but add structured fields for layout-aware blocks, attachments, figures, tables, navigation, and interaction modes.

## Recommended Content Layers

Use four layers:

1. Document metadata
2. Page metadata
3. Structured blocks and collections
4. Interaction/export modes
5. Theme tokens

Recommended inputs:

- `document.yml` for document-wide metadata
- `pages/*.md` for narrative chapters or views
- `attachments.yml` for distribution artifacts
- `figures.yml` or `tables.yml` for reusable referenced content
- `interactions.yml` for annotation, feedback, or edit-diff modes when enabled
- `theme.yml` for branding and visual tokens

## Example Document Metadata

```yaml
title: "AI Translation Prototype Explainer"
subtitle: "Architecture, roadmap, and delivery plan"
slug: "ai-translation-prototype-explainer"
authors:
  - name: "Document Author"
    affiliation: "Example Research Team"
audience: "Stakeholders"
delivery:
  preferredExtension: ".html"
  sizeBudgetMb: 30
navigation:
  style: "sidebar"
search:
  enabled: true
branding:
  primary: "#0f3d5e"
  accent: "#ee6c4d"
interaction:
  annotations:
    enabled: false
  editDiff:
    enabled: false
```

## Example Page File

Use Markdown body for the main narrative. Use front matter for structure.

```markdown
---
id: executive-summary
title: Executive Summary
navTitle: Summary
section: findings
template: narrative
summary: Key outcomes, risks, and delivery path.
hero:
  eyebrow: Explainer
  highlight: Three decisions
blocks:
  - type: callout
    tone: key
    title: Recommended path
    body: Build a normal site first, then package it.
  - type: figure
    figureId: architecture-overview
  - type: attachment-list
    ids:
      - implementation-plan
      - backlog-csv
  - type: comparison-table
    columns: [Option, Strength, Risk]
    rows:
      - [PDF, Familiar, Weak interactivity]
      - [Single-File HTML, Rich and portable, More engineering]
seo:
  description: Portable document summary page.
interaction:
  annotationTarget: true
  editable: false
---

This document argues for a two-stage architecture. First build a normal website with
well-structured content, then collapse it into a single-file deliverable once the
full experience is stable.
```

## Example Attachments File

Keep author intent separate from the generated payload manifest.

```yaml
attachments:
  - id: implementation-plan
    label: "Implementation Plan"
    source: "../media/attachments/phased-implementation-plan.pdf"
    downloadName: "prototype-implementation-plan.pdf"
    description: "Detailed phased plan"
    inlinePolicy: on-demand
  - id: backlog-csv
    label: "Ticket Backlog"
    source: "../media/attachments/prototype-ticket-backlog.csv"
    downloadName: "prototype-ticket-backlog.csv"
    description: "Machine-readable backlog export"
    inlinePolicy: on-demand
```

Then transform this into a generated attachment manifest with the helper script.

## Example Theme Tokens

```yaml
fonts:
  heading: "Fraunces"
  body: "Inter"
colors:
  background: "#f7f3ee"
  surface: "#fffdf8"
  text: "#1f2933"
  primary: "#0f3d5e"
  accent: "#ee6c4d"
layout:
  density: "comfortable"
  heroStyle: "split"
```

## Example Interaction Modes

Use interaction modes when the document is also a working surface. Keep them
in source data so the build can render stable IDs, export controls, and privacy
checks consistently.

```yaml
interaction:
  annotations:
    enabled: true
    targets:
      - selector: "[data-annotatable]"
        scope: page
    export:
      fileName: "reader-notes.json"
      schemaVersion: 1
  editDiff:
    enabled: true
    targets:
      - selector: "[data-editable]"
        granularity: block
    export:
      fileName: "text-edits.diff.json"
      schemaVersion: 1
      includeFullEditedText: true
```

Annotation mode lets readers highlight visible text, add notes, and export a
versioned JSON file. Edit-diff mode marks specific text regions as editable,
stores the original text snapshot, and exports a structured diff of reader
changes. Read `reader-annotation-and-editing.md` before enabling either mode.

## Example Slide Deck Content

For browser slide decks, keep the deck structure as data rather than
hard-coding slides directly into one HTML file.

Recommended inputs:

- `deck.yml` for deck metadata, theme, controls, and packaging settings
- `sections/*.md` for section-level framing
- `slides/*.md` for one slide per file, with front matter for layout and notes
- `figures.yml` for screenshots, image metadata, captions, and source paths
- `theme.yml` for institutional styling such as brand colours and typography

Example slide file:

```markdown
---
id: A3
section: opening-threshold
navTitle: Vivian threshold
title: A public leader calls it a threshold.
layout: image-right
figureId: vivian-balakrishnan-threshold
blocks:
  - type: bullets
    items:
      - Not a startup pitch
      - Not an investor memo
      - A working official describing a personal agent as useful
notes: >
  Use this as the first concrete anchor. The important point is the social
  location of the claim: a foreign minister saying agents crossed a practical
  threshold.
---
```

The compiler should emit deck data like:

```text
src/data/generated/
├── deck.json
├── slides.json
├── sections.json
├── figures.json
├── search-index.json
└── attachments.generated.ts
```

Slides should carry all information needed for presenter mode, overview
navigation, print handouts, and source review. Do not bury speaker notes,
figure captions, or source paths in comments that disappear at packaging time.

## Compile Before Render

Prefer a content compiler script such as `scripts/build-content.ts` or
`src/content/build-content.ts`.

The compiler should:

- read all Markdown/YAML sources
- normalize defaults
- resolve references
- inline SVG or preprocessed content where needed
- emit generated JSON or TS into `src/data/generated`

Do not make the browser discover the content graph at runtime.

## Output Contract

Target a generated data layer like:

```text
src/data/generated/
├── document.json
├── pages.json
├── figures.json
├── interactions.json
├── search-index.json
└── attachments.generated.ts
```

Then keep React components dumb:

- they render typed data
- they do not parse Markdown files directly
- they do not read local files at runtime

## When Markdown Is Not Enough

Move content out of the Markdown body when:

- the block needs structured fields
- the block will be reused
- the block drives UI behavior
- the block references heavy media or attachments
- the block needs translation, filtering, or search metadata

Use sidecar JSON or YAML for:

- charts
- timelines
- attachment catalogs
- complex tables
- media galleries
- glossary or citation datasets

## Practical Rule

Keep prose in Markdown.

Keep everything that behaves like data in YAML or JSON.
