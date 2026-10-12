# Test Plan For Single HTML Documents

Use this list on every substantial document before sending it to readers.

## Build Checks

- Build the normal website first.
- Build the packaged `.single.html` file.
- Run `node "${CLAUDE_SKILL_DIR}/scripts/audit-single-html.mjs" <file> --strict`.
- Run `node "${CLAUDE_SKILL_DIR}/scripts/test-feedback-media-runtime.mjs"` when annotation, feedback, or edit-diff export helpers are used.
- Confirm size is within the agreed budget: usually 10-30 MB, with an explicit exception for 30-100 MB documents.
- Confirm there are no local text, Markdown, JSON, CSS, JS, or image dependencies left outside the file.
- Confirm downloads are only real distributable artifacts such as CSV, PDF, spreadsheet, slides, ZIP, or media.

## Browser Checks

- Open the single HTML file from `file://`, not only from a dev server.
- Open it from a temporary folder with no adjacent assets.
- Check browser console errors.
- Test internal navigation and hash links.
- Test search, filters, tabs, accordions, drawers, and other stateful UI.
- Test every attachment download and inspect the downloaded file name, MIME type, and content.
- Test images and media after disconnecting network access.
- Test print preview when the artifact may be printed or saved as PDF.
- Test desktop, tablet-width, and mobile-width layouts.
- If annotation mode is enabled, add, edit, delete, reload, and export a highlighted-text note.
- If edit-diff mode is enabled, edit a marked text region, reset another, and export a diff.

## Pattern Fidelity Checks

Use these checks whenever the deliverable selected a source pattern from
`html-effectiveness-patterns.md`.

- Confirm the selected source pattern is named in the project source README or build notes.
- Confirm the main interaction still works as the source pattern's interaction:
  - triage board: drag between lanes, visible lane counts, copy/export ordering
  - feature flags: grouped toggles, dependency/conflict warnings, diff/full export
  - prompt tuner: editable template, live preview, copy/reset
  - annotated PR: file risk map, line notes, severity tags, jump links
  - flowchart: clickable nodes, detail panel, path/status legend
  - feature explainer: TL;DR, step path, tabbed samples, glossary/FAQ
- Confirm any export/copy button returns a useful artifact, not just a prose summary.
- Confirm visible counts, statuses, risk tags, and next actions sit near the object being reviewed.
- Confirm the result could not be replaced by a Markdown report without losing the main affordance.
- If a new interaction pattern was used, confirm:
  - source notes show why existing patterns were unsuitable
  - user approved the proposal
  - test implementation was reviewed
  - approved pattern was added back to `html-effectiveness-patterns.md`

## Content Checks

- Confirm all local source text needed to understand the document is rendered in the page.
- Confirm source appendix or provenance sections are searchable.
- Confirm citations or external links are clearly supplementary, not required for basic comprehension.
- Confirm the document can still be understood if JavaScript fails, at least at the level of static reading.
- Confirm the cover, title, date, version, and audience are clear.
- Confirm generated annotation or edit exports use versioned schemas and stable target IDs.

## Privacy And Payload Checks

- Search the final HTML source for personal data, secrets, tokens, and internal-only paths.
- Inspect embedded Base64 manifests for accidental inclusion of draft files.
- Confirm generated media and copied images are allowed to be redistributed.
- Confirm attachments are intentionally downloadable.
- Confirm no analytics, tracking pixels, remote fonts, or CDN scripts are present unless the user explicitly wants them.
