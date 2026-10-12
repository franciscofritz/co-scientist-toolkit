---
name: single-html-document
description: "Build polished, self-contained single-file HTML documents: one browser-openable .html with all content, CSS, JavaScript, media, and export contracts inlined. Use whenever the user wants a rich, visual, or interactive document delivered as a standalone HTML file. Triggers: 'make a single-file HTML document', 'self-contained / standalone HTML', 'package this website into one .html', 'build an interactive briefing / explainer / dashboard / research synthesis as a webpage', 'a review or annotation workbook', 'an editable draft with edit-diff', 'a designed document I can open in a browser and email', or any request to collapse a multi-file site into one shareable HTML file. Authored as a Vite + React + TypeScript site (Markdown + YAML front matter compiled to JSON), then packaged with vite-plugin-singlefile. Boundaries: an animated HTML slide deck is a different job; a .pptx or typeset PDF is polished-docs-and-decks; this skill owns documents, dashboards, and workbooks."
---

# Single-File HTML Documents

Build the website first. Package it second.

Treat single-file HTML as a delivery format, not an authoring format. Keep content, styling, scripts, media, interaction state, and export contracts separate while building the project, then collapse the finished document into one browser-openable file only after the normal website works.

## Non-Negotiable Principle

The delivered document is one modern, polished HTML file that contains the full reading or working experience.

- Do not make text notes, Markdown, JSON, transcripts, manifests, source documents, or review plans available only as downloads or adjacent files.
- Any text file needed for understanding the document must be incorporated into the page as rendered content, searchable content, an appendix, source drawer, or embedded provenance section.
- Downloads are reserved for files that genuinely need separate distribution, especially PDFs, CSVs, spreadsheets, slide decks, or other binary/tabular attachments.
- External links are acceptable as citations or live service embeds, but they are not a substitute for incorporating the local source text needed by the document.
- If the document collects notes, annotations, edits, ratings, screenshots, or audio, those are first-class document data with a versioned export contract.
- The final file should feel like a designed product, not a plain generated dump.

## Start Here

- Reuse an existing project if the user already has one. Otherwise default to Vite + React + TypeScript for new work.
- Keep content in Markdown with YAML front matter, then compile it into generated JSON or TypeScript before rendering.
- Keep author-time CSS and JavaScript in separate files. Inline only at the packaging stage.
- For interactive feedback, annotation, or edit-diff documents, keep the reviewed data, commented client JavaScript, and generated HTML separate. Strip comments and package the distribution script only in the build step.
- Build a normal multi-file site first. Do not try to design directly inside one giant HTML file.
- Keep the final deliverable valid `.html`.
- When the user asks for a visual, interactive, reviewable, editor-like, or "not boring" document, read `references/html-effectiveness-patterns.md` before UI code.
- Choose a source pattern and preserve its interaction contract, not just its general vibe.
- Invent a new interaction pattern only when existing patterns are unsuitable.
- New pattern path: propose to user -> build small test implementation -> ask approval -> update skill after approval.

## Precedent Patterns

Inspect local precedents only when the user explicitly points to them. Useful patterns to reuse:

- Rich presentation handouts with extracted media, typed data, and presentation-oriented navigation.
- Browser-native slide decks with keyboard navigation, presenter notes, overview/search drawers, printable handout mode, and packaged screenshot/media assets.
- Markdown + YAML front matter compiled into generated JSON before rendering.
- Small-scale self-contained HTML export where all text, CSS, JavaScript, icons, and media are incorporated at package time.

Prefer reusing proven content-build patterns over inventing a new schema from scratch.

## Use This Workflow

1. Inspect the source material, existing project, and delivery goal.
   Identify whether the user is starting from Markdown content, a PPT-derived site, a research document, an explainer, a review workbook, an editable draft, or an already-built website that now needs a single-file export.
2. Choose the content model before touching UI code.
   Read [references/content-model.md](references/content-model.md) when designing or normalizing the schema.
3. Choose the visual/interaction contract before touching UI code.
   If the document is meant to be interactive or reviewable, read [references/html-effectiveness-patterns.md](references/html-effectiveness-patterns.md), name the closest source pattern, and list the pattern behaviours that must survive adaptation.
   If no source pattern fits, stop and suggest a new pattern contract to the user instead of silently inventing one.
   Build a narrow prototype only after the user accepts the proposal; update the pattern reference only after the prototype is approved.
4. Build the normal website first.
   Make sure it works as a regular multi-file site with separated JS, CSS, and assets before collapsing it.
5. Choose the packaging mode.
   Read [references/architecture.md](references/architecture.md) for the decision table and implementation patterns.
6. Package the site into a single deliverable.
   Keep the output browser-openable from disk. Avoid leaving external assets, split bundles, or runtime fetches.
7. Verify the packaged file under realistic conditions.
   Open it from `file://`, test navigation, media, search, downloads, and attachment export. Run `scripts/audit-single-html.mjs` on the final file.

## Choose The Packaging Mode

Use these as project heuristics, not hard browser limits:

| Mode | Use when | Packaging rule |
| --- | --- | --- |
| Direct inline | Small to medium deliverable, modest media, no heavy attachments | Inline app JS/CSS and imported assets directly into the final HTML |
| Blob-backed payload | Rich document with larger images, PDFs, spreadsheets, or media downloads | Embed attachment/media payloads as Base64 or gzip+Base64 data records, then materialize `Blob` URLs lazily in the browser |
| Compressed bootstrap | Large deliverable where raw inline HTML becomes unwieldy | Ship a small HTML bootstrap plus compressed embedded payload that is decompressed on load in a modern browser |

Do not use Web Bundles as the primary plan. They remain experimental and were removed from Chrome's normal implementation path. Do not use MHTML as the primary plan either unless the user explicitly asks for that format.

## Content Rules

- Separate content, presentation, and packaging concerns.
- Prefer `content/` plus a compile step over fetching raw Markdown at runtime.
- Keep theme tokens separate from narrative content.
- Store complex blocks as structured fields or sidecar JSON/YAML, not as ad-hoc HTML fragments.
- Treat attachments as manifest entries with metadata and payload, not as giant literal `href="data:..."` links sprinkled through templates.
- Precompute navigation, search indexes, figure metadata, and attachment metadata at build time.

## Packaging Rules

- Prefer imported assets over `public/` assets for anything that must end up inside the final file.
- Prefer hash routing or a single-page structure for packaged deliverables. Avoid history-based routing for `file://` usage.
- Avoid runtime network fetches in the final file.
- Avoid external fonts, CDNs, analytics, and third-party scripts.
- Avoid leaving root-absolute URLs such as `/assets/...` in the final file.
- Avoid external module scripts or leftover split chunks in the final file.
- Materialize downloadable attachments with `Blob` URLs and `a.download`, not with multi-megabyte `data:` anchors.
- Keep the final output valid as ordinary HTML.

## Default Tooling

When starting from scratch in a new project:

```bash
npm create vite@latest document-site -- --template react-ts
cd document-site
npm install
npm add gray-matter fast-glob
npm add -D vite-plugin-singlefile
```

Before the first build, remove the template's favicon link from `index.html`, as the audit rejects it as a local asset reference. Remove the demo content too, as it contains external links. If the repo already uses another package manager, such as `bun`, stay with it. The commands translate directly.

Requirements: Node.js 20.19 or later (or 22.12 or later), which the current Vite needs, to run the helper scripts (they are ES modules and need no npm packages) and the Vite build; `npm`; and a modern browser to check the result.

## Helper Scripts

- `scripts/make-attachment-manifest.mjs`
  Turn files or folders into an attachment manifest with MIME type, size, checksum, and Base64 or gzip+Base64 payloads.
- `scripts/audit-single-html.mjs`
  Inspect a packaged HTML file for leftover local/remote dependencies, unsafe routing assumptions, split-bundle hints, absolute web addresses outside links, and size guidance.
- `scripts/build-block-sample.mjs`
  Generate a single-file HTML document from a block manifest under `scripts/manifests/`. The script produces the composed-blocks handbook and walkthrough samples and can be reused for any composition of blocks. When building a document, pass your own output folder as the second argument. Without it, the script writes into this skill's `assets/design-samples/`, which a plugin update replaces. The script has no Markdown compiler. Supply each text field as HTML in its `...Html` form (`bodyHtml`, `answerHtml`), as a field named `body` is dropped without a warning.
- `scripts/feedback-media-runtime.js`
  Browser-side helper for standalone feedback documents that collect screenshots, pasted images, uploaded audio, recorded voice notes, selected-text annotations, and versioned JSON exports.
- `scripts/extract-feedback-media.mjs`
  Extract Base64 screenshot and audio attachments from returned feedback workbook JSON files.

Script paths in the reference files begin with the same variable as the commands in this file. If the shell does not expand it, put this skill's folder in its place.

Find the shipped design samples in `assets/design-samples/`.

## References

Architecture and packaging:

- [references/architecture.md](references/architecture.md) — the canonical pipeline, packaging modes, attachment pattern, offline-safe rules, and sourced rationale. Read before scaffolding or packaging a project.
- [references/packaging-examples.md](references/packaging-examples.md) — concrete direct-inline, Blob-manifest, compressed-bootstrap, and Vite packaging examples.
- [references/attachment-runtime-helpers.md](references/attachment-runtime-helpers.md) — when embedding downloadable PDF, CSV, spreadsheet, slide deck, ZIP, or media artifacts.

Content model and authoring:

- [references/content-model.md](references/content-model.md) — Markdown/YAML schema layers (document, page, blocks, theme, interaction modes).
- [references/page-contract.md](references/page-contract.md) — page-level invariants every deliverable honours: sidebar TOC by default, no horizontal page scroll, no overflow inside blocks, predictable diagram-edge routing, print and offline safety. Required reading before designing a new shell or archetype.
- [references/icons.md](references/icons.md) — Lucide-by-name icon system. Authors reference icons by name (`icon: "shield-alert"`); the build tree-shakes so only used icons land in the output. Catalogue and how to add icons live here.
- [references/patterns/_protocol.md](references/patterns/_protocol.md) — page-pattern layer (parallel to blocks). Patterns are reusable page features (TOC, global search, keyboard help, future patterns) that manifests opt into and the build tree-shakes. Per-pattern docs in `references/patterns/<name>.md`; renderers in `scripts/patterns/<name>.js`.
- [references/blocks/_protocol.md](references/blocks/_protocol.md) — the contract every reusable content block follows (renderer signature, packaging modes, custom escape hatch). Read this before composing pages out of structured blocks.
- [references/blocks/_index.md](references/blocks/_index.md) — catalogue of every defined block (scaffolding, diagram, comparison, interactive). Each block has a colocated spec in `references/blocks/<name>.md`, renderer in `scripts/blocks/<name>.js`, and example in `assets/blocks/<name>.example.yml`.

Design and delivery shape:

- [references/html-effectiveness-patterns.md](references/html-effectiveness-patterns.md) — fidelity map for the Thariq `html-effectiveness` examples. Required for visual, interactive, reviewable, editor-like, or "not boring" deliverables.
- [references/archetype-recipes.md](references/archetype-recipes.md) — choosing a structure for dashboards, briefings, galleries, courses, research syntheses, decks, and review workbooks.
- [references/design-options.md](references/design-options.md) — visual direction for analytics, record catalogue, committee briefing, protocol dossier, tabbed workshop, browser slide deck, inspection gallery, and workshop report designs.
- [references/reader-annotation-and-editing.md](references/reader-annotation-and-editing.md) — highlight-and-note mode, editable draft mode, annotation export, and edit-diff export contracts.
- [references/interactive-feedback-workbooks.md](references/interactive-feedback-workbooks.md) — standalone review forms that collect ratings, screenshots, voice notes, annotations, and returned JSON feedback.

Verification:

- [references/test-plan.md](references/test-plan.md) — reusable build, browser, content, and privacy checks.
- [references/privacy-and-payload-review.md](references/privacy-and-payload-review.md) — before distributing documents that embed source notes, private data, or downloadable artifacts.

## Reusable Blocks

Pages compose out of typed blocks rather than ad-hoc HTML. The block layer keeps presentation in renderers (vanilla JS, packaging-safe) while authors stay in YAML/JSON.

- Each block lives as three colocated files: `references/blocks/<name>.md` (schema and when-to-use), `scripts/blocks/<name>.js` (renderer), `assets/blocks/<name>.example.yml` (canonical example).
- The contract is in `references/blocks/_protocol.md`; the catalogue is in `references/blocks/_index.md`.
- Available groups: scaffolding (tldr, callout, faq, before-after, glossary), diagram (timeline, flowchart, module-map, inline-svg), comparison and tokens (side-by-side, contact-sheet, swatches, severity-tag, tabbed-code), interactive (slider, toggle-deps, drag-reorder, live-template, annotated-diff).
- Interactive blocks hydrate from the shared bootstrap at `scripts/blocks/_bootstrap.js`; static blocks are rendered at compile time with no JS shipped.
- Use the `custom` escape hatch sparingly for one-offs that don't merit a permanent block type.

## Design Sample Assets

Use these local single-file samples as visual and structural references:

- `assets/design-samples/institutional-analytics.single.html`
- `assets/design-samples/record-catalogue.single.html`
- `assets/design-samples/committee-briefing.single.html`
- `assets/design-samples/protocol-dossier.single.html`
- `assets/design-samples/tabbed-workshop.single.html`
- `assets/design-samples/inspection-gallery.single.html`
- `assets/design-samples/workshop-report.single.html`
- `assets/design-samples/composed-blocks-handbook.single.html`
- `assets/design-samples/composed-blocks-walkthrough.single.html`

Regenerate the composed-blocks samples after editing any block. To write elsewhere, pass an output folder as the second argument:

```bash
node "${CLAUDE_SKILL_DIR}/scripts/build-block-sample.mjs" "${CLAUDE_SKILL_DIR}/scripts/manifests/composed-blocks-handbook.mjs"
node "${CLAUDE_SKILL_DIR}/scripts/build-block-sample.mjs" "${CLAUDE_SKILL_DIR}/scripts/manifests/composed-blocks-walkthrough.mjs"
```

For slide-deck deliverables, prefer the browser slide deck pattern in
`references/design-options.md` and `references/archetype-recipes.md` over
repurposing dossier, briefing, or tabbed-workshop layouts. Institutional
styling should be expressed as a theme layer on the deck; it should not change
the artifact into a report. For institution-styled slide decks, default to clean
sans-serif typography and an unruled background; use colour, spacing, captions,
and a textual masthead for institutional identity.

## Validation

- Make the site work normally before packaging it.
- Build the final output and open it from disk in a modern browser.
- Run:

```bash
node "${CLAUDE_SKILL_DIR}/scripts/audit-single-html.mjs" dist/document.html --strict
```

- Test at least:
  - internal navigation
  - images and media rendering
  - attachment downloads
  - search and client-side filters
  - annotation export or edit-diff export when enabled
  - the named `html-effectiveness` interaction contract when one was selected
  - print styling if the document is meant to print well
