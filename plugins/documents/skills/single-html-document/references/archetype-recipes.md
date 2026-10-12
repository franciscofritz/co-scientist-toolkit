# Archetype Recipes

Use these recipes to choose a structure before designing the UI. Each recipe still follows the same rule: source content is incorporated into the page, while downloads are reserved for real distributable artifacts.

## Explainer Or Guide

Use when the artifact explains a concept, policy, workflow, tool, or research
area as a polished standalone document rather than a dashboard or deck.

Inputs: Markdown chapters, examples, glossary terms, diagrams, citations,
source notes, and optional handouts.

Recommended stack: static HTML or Astro for mostly narrative explainers;
Vite/React when diagrams, search, filters, or interactive examples are central.

Packaging mode: direct inline for most explainers; Blob-backed payload only
for downloadable source packs, datasets, worksheets, or media.

Recommended blocks:

- overview or TL;DR
- short sections with stable anchors
- callouts for assumptions, risks, and implications
- glossary
- diagrams or module maps
- source/provenance appendix
- optional reader annotation mode

Local text rule: examples, source excerpts, definitions, and explanatory notes
must be rendered in the page, not left as Markdown downloads.

Legitimate downloads: worksheets, CSV/source packs, PDFs, or slide copies that
have independent reuse value.

Design notes:

- make the first screen establish the topic and reader task
- favour short readable chunks over article sprawl
- include sidebar navigation and search for long explainers
- if readers are expected to respond, enable annotation export rather than
  relying on informal comments by email

## Operational Dashboard Report

Use when readers need scanning, comparison, and follow-up actions.

Inputs: CSV extracts, short Markdown interpretation, risk notes, and optional methodology notes.

Recommended stack: Vite/React for complex dashboards, or Astro/static HTML for mostly narrative dashboards.

Packaging mode: direct inline for small dashboards; Blob-backed payload for CSV/spreadsheet downloads.

Recommended blocks:

- executive summary
- KPI strip
- trend or bar visual
- risk register
- action table
- source appendix
- CSV download for reusable tabular data

Local text rule: methodology notes, assumptions, and interpretation must be rendered in the page.

Legitimate downloads: CSV, spreadsheet, or PDF snapshot when readers need to reuse or archive them outside the report.

Design notes:

- dense but calm layout
- sticky navigation
- compact cards only for repeated metrics or rows
- strong search and filtering

## Workshop Or Event Briefing

Use when a report replaces a slide deck or participant handout.

Inputs: Markdown briefing notes, agenda data, prompt cards, facilitator notes, and optional handout artifacts.

Recommended stack: Astro or Vite with a simple client runtime.

Packaging mode: direct inline unless facilitator data or handouts need Blob-backed downloads.

Recommended blocks:

- purpose
- agenda or timeline
- facilitation prompts
- decision checklist
- follow-up actions
- source appendix
- CSV download only for reusable prompt-card data

Local text rule: agenda, prompts, assumptions, and follow-up notes must be readable in the page.

Legitimate downloads: prompt-card CSV, participant worksheet PDF, or slide deck when the user explicitly wants a separate artifact.

Design notes:

- first viewport should show the event identity and agenda
- avoid a marketing landing page
- make the artifact useful before, during, and after the session

## Browser Slide Deck

Use when the final artifact is still a slide deck, but must travel as a
single browser-openable HTML file rather than a PowerPoint, PDF, or scrolling
report.

Inputs: Markdown/YAML slide sources, section outline, speaker notes,
screenshots or figures, source/provenance notes, and optional downloadable
attachments such as a PPTX or PDF copy.

Recommended stack: Vite/React for substantial decks with drawers, search,
presenter state, and richer figure handling; static HTML is acceptable for
small decks when the content model is still kept separate during authoring.

Packaging mode: direct inline for modest decks; Blob-backed payload for decks
with many screenshots or binary attachments; compressed bootstrap only when the
single HTML becomes unwieldy after image embedding.

Recommended blocks:

- title slide
- section-divider slides
- statement or claim slides
- comparison/table slides
- trace/process slides
- full-slide screenshot or figure slides
- screenshot appendix or figure bank
- presenter notes drawer
- overview/search drawer
- print-all handout mode
- source/provenance appendix

Local text rule: slide notes, source notes, figure captions, and provenance
that explain the deck must be rendered in the page, not left as adjacent
Markdown files. Speaker notes may live in a drawer, side panel, or print-only
notes block.

Legitimate downloads: PPTX/PDF exports, source CSVs, worksheets, or media
bundles when the audience genuinely needs a separate reusable file.

Design notes:

- preserve slide-deck behaviour: one primary slide viewport, keyboard
  navigation, progress state, and hash/deep-link support
- do not drift into a scrolling dossier, committee briefing, or tabbed
  workshop unless the user asks to change the artifact type
- use report-like affordances only around the deck: overview, notes, source
  appendix, search, and print handout
- design for the room first, then for individual reading
- for institutional decks, express the institution through theme tokens,
  typography, masthead, colour, spacing, and captions rather than through
  decorative page furniture
- for institution-styled decks, anchor the theme in the supplied brand colour,
  use shell/off-white and stone-grey neutrals, limit secondary accents, prefer
  accessible brand-colour/white/black text combinations, use clean sans-serif
  typography, and avoid ruled-paper, parchment, or background-line treatments
- if no approved logo file is supplied, use a text masthead such as
  `Institution Name · Programme or Unit` and leave space for a proper logo
  rather than approximating one

## Media Or Image Gallery Report

Use when readers need visual inspection and provenance.

Inputs: image files, prompt records, evaluation notes, rubric data, and generated-media metadata.

Recommended stack: Vite/React for filtering and richer state; static HTML is fine for small galleries.

Packaging mode: direct inline for small image sets; Blob-backed payload for large source media or rubric downloads; compressed bootstrap only for very large galleries.

Recommended blocks:

- overview
- figure grid
- category filters
- figure notes
- prompt/source appendix
- rubric download

Local text rule: prompts, evaluation notes, and provenance must be incorporated into the page.

Legitimate downloads: CSV rubric, source media ZIP, or image bundle when reviewers need reusable files.

Design notes:

- large figure surfaces
- clear metadata on every visual
- explicit labels for generated, edited, and source media
- size budget before adding high-resolution assets

## Course Or Learning Pack

Use when distributing a rich course clone, learning sequence, or self-guided lesson.

Inputs: Markdown lesson pages, activity data, images, rubrics, and optional handouts.

Recommended stack: Astro for content-heavy lessons; Vite/React for interactive activities.

Packaging mode: direct inline for text-heavy packs; Blob-backed payload for handouts or worksheets.

Recommended blocks:

- module navigation
- objectives
- lesson sections
- embedded activities
- glossary
- completion checklist
- optional CSV/PDF handouts

Local text rule: lesson notes, instructions, and activity explanations must appear in the page.

Legitimate downloads: PDF handouts, CSV datasets, or templates intended for learner reuse.

Design notes:

- preserve reading order
- make activities work without a backend
- include local lesson notes in the page rather than as text downloads

## Research Synthesis

Use when converting notes, meetings, or desk research into a portable report.

Inputs: Markdown notes, meeting summaries, evidence tables, source excerpts, and optional data exports.

Recommended stack: Astro/static HTML for mostly narrative reports; Vite/React when search, filters, or evidence views are complex.

Packaging mode: direct inline for most reports; Blob-backed payload only for reusable datasets or appended PDFs.

Recommended blocks:

- question
- method
- findings
- evidence table
- uncertainty and limits
- recommendations
- source appendix

Local text rule: local notes that support claims must be rendered, summarised, or quoted in the report. Do not put them in downloadable text files.

Legitimate downloads: CSV evidence tables, PDF source packs, or spreadsheet models.

Design notes:

- keep evidence close to claims
- make assumptions explicit
- include raw local notes only when privacy review permits it

## QA Or Review Workbook

Use when reviewers need to compare two systems or versions side by side, record structured pass/partial/fail judgements, attach screenshots, and send back a machine-readable response.

Inputs: structured QA plan, original-vs-target links, step-by-step test instructions, expected screenshots, and reviewer guidance.

Recommended stack: normal static website first, then package into one portable single HTML file with client-side autosave.

Packaging mode: direct inline for small and medium workbooks; Blob-backed payload only if expected screenshots or embedded reference images become too large.

Recommended blocks:

- purpose and reviewer instructions
- per-section original and target link panels
- explicit test checklist
- expected outcome block
- compact reviewer response fields
- screenshot capture or paste area
- JSON feedback export and send instructions

Local text rule: the full test instructions and expected outcomes must be readable inside the page. Do not hide the actual QA brief in sidecar Markdown or downloadable notes.

Legitimate downloads: structured JSON feedback, optional attachment bundle for reviewer screenshots, and only genuine external evidence packs when needed.

Design notes:

- keep reviewer overhead low
- prefer one name field over a full metadata intake form unless the testing workflow genuinely needs more
- support local autosave because reviewers may open the file from email or a shared drive
- treat screenshot capture as first-class, including pasted clipboard images and base64/data-URL payloads when practical

## Editable Draft Review

Use when the single HTML document is a review copy and the reader should edit
specific text regions directly, then return a structured diff.

Inputs: Markdown draft sections, source refs for each editable region, reviewer
guidance, and optional read-only context sections.

Recommended stack: static HTML with a small client runtime for short drafts;
Vite/React only when the draft also needs complex navigation, filters, or media.

Packaging mode: direct inline. Store original editable snapshots in generated
JSON or attributes and keep returned edits in a separate export file.

Recommended blocks:

- reviewer instructions
- read-only context
- editable text regions with stable IDs
- change summary panel
- reset controls
- JSON diff export
- optional selected-text annotation mode

Local text rule: the draft text and context must be visible in the page. Do not
ship the actual draft as a hidden download with a thin wrapper around it.

Legitimate downloads: exported edit-diff JSON, optional full edited-text export,
or source pack if the reviewer needs offline context.

Design notes:

- mark editable regions clearly but calmly
- avoid making the whole page editable unless the workflow truly requires it
- export changed regions only by default
- never apply returned diffs to source files without human review

## Composed Blocks

Use when the deliverable's whole point is showing a set of reusable content blocks together — either as a reference handbook a team can study, or as a narrative walkthrough that uses the blocks to explain something.

Inputs: a curated list of block instances (TL;DRs, callouts, timelines, swatches, flowcharts, etc.) defined as authored YAML/JSON, plus the framing prose that ties them together.

Recommended stack: static HTML for the handbook variant; Vite/React or static HTML for the walkthrough, depending on how much navigation surrounds the blocks.

Packaging mode: direct inline. Interactive blocks rely on the shared bootstrap (`scripts/blocks/_bootstrap.js`); both the bootstrap and the registered renderer modules are inlined at packaging time.

Recommended blocks:

- top-of-page `tldr` framing the deliverable
- a `glossary` block when the deliverable defines its own vocabulary
- the actual demonstrated blocks, grouped under section headings
- a `severity-tag` catalogue when the deliverable also defines a tag vocabulary other blocks reference
- a closing `faq` block for anticipated reviewer questions

Local text rule: every block's authored content (Markdown body, alt text, captions, descriptions) must be rendered in the page. Don't ship the YAML sources as side downloads — the rendered blocks are the point.

Legitimate downloads: the source content folder as a ZIP only when the deliverable explicitly asks readers to fork the patterns.

Design notes:

- frame the deliverable like documentation, not a dashboard
- use plenty of whitespace between blocks; blocks pressed too close together lose their identity
- the handbook variant should label each block instance with its `type` so readers can map demonstration back to schema
- the walkthrough variant should hide the type labels and instead use the blocks as illustration in service of the narrative
- prefer one block per concept rather than chaining three of the same kind
- read [`references/blocks/_protocol.md`](blocks/_protocol.md) before authoring; the protocol determines packaging behaviour

## Existing-Site Capture Fallback

Use when the source is already a built site and there is no time to rebuild the content model.

Inputs: local or deployed website, asset folder, and any source documents that are not already visible in the site.

Recommended stack: SingleFile or a custom post-build inliner for capture; follow up with a content-model rebuild when the workflow will repeat.

Packaging mode: direct inline capture first; Blob-backed payload only for legitimate downloads.

Required UI patterns:

- clear landing state
- working internal navigation
- embedded source/provenance section for any local notes not already visible
- explicit download section for real artifacts

Local text rule: if the source website linked to local Markdown, TXT, JSON, or notes, incorporate the text into the captured artifact before distribution.

Legitimate downloads: preserve existing PDF/CSV/spreadsheet downloads only when they are intended distributable artifacts.

Audit expectations:

- strict audit passes
- no leftover root-relative assets
- no service worker assumptions
- no external fonts or scripts unless approved

Use this fallback sparingly. It is a packaging rescue path, not the best authoring architecture.
