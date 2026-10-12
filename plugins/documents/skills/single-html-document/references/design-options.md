# Design Options

The skill should not have one house style. It should choose a design option from the content shape, audience, and usage mode.

The current generated samples remain valid options:

- `dashboard-report`: compact operational report with KPI strip, bars, risks, downloads, and source appendix.
- `event-briefing`: workshop briefing with timeline, prompts, follow-up actions, downloads, and source appendix.
- `gallery-report`: inspection gallery with visual cards, filters, figure notes, downloads, and source appendix.

Generated design sample assets live in `single-html-document/assets/design-samples/`.

Local generated catalogue and usage-report examples add several additional directions. Treat those examples as direction, not as finished maximum-quality templates.

## Option 1: Institutional Analytics

Inspired by operational usage-report dashboards.

Use for:

- CSV/admin exports
- operational dashboards
- product-like reporting
- KPI-heavy usage reports

Core layout:

- left navigation rail
- topbar with title and metadata chips
- KPI card grid
- dashboard panel grid
- ranked table
- export/artifact section
- footer metadata strip

Design notes:

- warm sand/off-white background
- deep teal as primary data colour
- muted gold for warning/pending state
- restrained red for destructive state
- icons in nav items, metric tiles, filter chips, and export cards

Implementation notes:

- Use `lucide-react` icons such as `Home`, `Users`, `Layers`, `Wrench`, `FileText`, `Download`, `CalendarDays`, `Filter`, `MessageSquare`, `Database`, and `BarChart3`.
- Use real charts only when the data supports them. Do not invent comparison controls or trend lines.
- If Plotly is used, bundle it into the single file and expect a large output. Prefer lighter SVG/CSS charts for small reports.

## Option 2: Record Catalogue

Inspired by generated record catalogues with search and filters.

Use for:

- Markdown record inventories
- protocol libraries
- tool catalogues
- people/stakeholder directories
- compliance/risk registers

Core layout:

- compact institutional header
- sticky filter sidebar
- search and select filters
- summary stats
- stacked record cards
- status/type pills
- metadata grids

Design notes:

- this can stay stricter and more institutional than the other options
- preserve high contrast and clear focus states
- avoid over-softening records into generic cards
- improve density, spacing, icon support, and mobile filter handling

Implementation notes:

- Use `lucide-react` icons such as `Search`, `SlidersHorizontal`, `FileCheck2`, `ShieldAlert`, `UserRound`, `Tag`, `Calendar`, `Link2`, and `PanelLeftClose`.
- Render Markdown body text in the page. Do not leave source Markdown as downloads.
- Add source/provenance drawers for each record when the text is long.

## Option 3: Committee Briefing

Inspired by generated committee briefing and meeting notes pages.

Use for:

- committee packs
- meeting notes
- workshop records
- decision briefings
- pre-read documents

Core layout:

- landing overview
- attendance/fact cards
- highlights or decision callouts
- section overview grid
- sticky scroll navigation
- long-form article sections
- source appendix

Design notes:

- calm, reading-oriented, and polished
- landing must clarify audience, date, decision, and next action
- section cards should help navigation, not become decorative clutter
- source/provenance should be visible and searchable

Implementation notes:

- Use `lucide-react` icons such as `ClipboardList`, `UsersRound`, `Clock`, `CheckCircle2`, `AlertTriangle`, `ArrowRight`, and `ScrollText`.
- Add print styling because committee briefings may still be saved as PDF.

## Option 4: Protocol Dossier

Inspired by generated protocol share pages.

Use for:

- one important protocol
- policy proposal
- research plan
- risk review
- paper-like document with meeting presentation needs

Core layout:

- institutional hero
- metadata cards
- article body
- sticky fact rail
- table of contents
- optional reading/meeting mode toggle

Design notes:

- stronger institutional authority than the committee briefing
- good for a single document, not a collection
- prose can be more spacious
- metadata should be structured rather than buried in paragraphs

Implementation notes:

- Use `lucide-react` icons such as `ShieldCheck`, `FileWarning`, `ListChecks`, `BookOpenText`, `Network`, `CalendarClock`, and `Presentation`.
- Meeting mode should be generated from the same sections, not a separate hand-authored duplicate.

## Option 5: Tabbed Workshop

Inspired by generated tabbed briefing drafts.

Use for:

- workshop packs
- facilitation guides
- training sessions
- browser-based slide substitutes
- action-oriented strategy sessions

Core layout:

- compact hero
- stat strip
- tab navigation
- card grids
- action blocks
- print-all fallback

Design notes:

- works best when the user will present from the HTML file
- tabs should reflect session flow, not arbitrary headings
- each tab should be self-contained enough for live use

Implementation notes:

- Use `lucide-react` icons such as `PlayCircle`, `MessagesSquare`, `Route`, `Blocks`, `Target`, `ClipboardCheck`, and `Download`.
- Provide keyboard-accessible tab controls and print CSS that displays all panels.

## Option 6: Browser Slide Deck

Inspired by the `agents-and-ai-2026` and `understanding-ai-agent-architecture`
single-file presentation decks.

Use for:

- presentation decks that must be shared as one browser-openable HTML file
- strategy talks, training sessions, research briefings, and lecture decks
- slide-first artifacts with presenter notes, screenshots, and appendix material
- browser-native replacements for PowerPoint when the user will present live

Core layout:

- full-viewport slide stage
- structured slide IDs grouped by section
- keyboard navigation (`←`, `→`, space, home/end)
- progress footer or compact rail
- overview drawer with sectioned slide list and search
- presenter-notes drawer
- hash-based deep links for each slide
- screenshot/media appendix with figure captions and source metadata
- print-all handout mode that shows slides and notes in reading order

Design notes:

- keep it a slide deck, not a dossier, scrolling report, or tabbed microsite
- make every slide work as one viewport in presentation mode
- use card surfaces only for repeated slide elements, figure frames, or controls
- keep headings large enough for a room, but use responsive constraints so they do not clip on small screens
- make screenshots inspectable and clearly captioned; avoid using them as blurred decorative backgrounds
- institutional styling should be a theme layer over the deck pattern
- for institution-styled decks, use the supplied brand colour as an anchor, neutral shell/off-white backgrounds, restrained secondary accents, and clean sans-serif typography; avoid ruled-paper, parchment, or background-line treatments
- when the correct approved logo asset is not available, use a textual institutional masthead rather than recreating or approximating the logo

Implementation notes:

- Keep slide content in structured Markdown/YAML or generated JSON: `id`, `section`, `navTitle`, `title`, `layout`, `blocks`, `notes`, `figures`.
- Precompute section navigation, search labels, progress metadata, and figure/source manifests at build time.
- Use hash routing or in-page state only; do not rely on history routing for `file://` delivery.
- Package modest decks by direct inlining. For decks with many screenshots, use a Blob-backed payload and materialize image URLs lazily.
- Verify from `file://` as well as local HTTP: slide navigation, notes drawer, overview/search, image loading, deep links, and print mode.
- Run the single-HTML audit on the final packaged file and check that no root-relative assets or runtime fetches remain.

## Option 7: Inspection Gallery

This is the current `gallery-report` direction.

Use for:

- image/model comparisons
- screenshot galleries
- prompt galleries
- rubric-based evaluation
- visual evidence reviews

Core layout:

- utility rail
- category filters
- large figure grid
- figure metadata
- source/provenance drawers
- rubric or CSV artifact download

Design notes:

- primary visuals must be inspectable, not cropped atmosphere
- metadata belongs near each figure
- strong filtering matters more than a long narrative flow

Implementation notes:

- Use `lucide-react` icons such as `Image`, `Images`, `SlidersHorizontal`, `Eye`, `BadgeCheck`, `Scale`, `FileSpreadsheet`, and `Download`.
- Use real image assets or generated bitmap/SVG placeholders only when clearly marked as placeholders.
- Make the gallery fully navigable: every figure card should link to a detail section, category filters should work offline, and source/rubric sections should be reachable from the side navigation.

## Option 8: Workshop Report

Inspired by workshop notes folders that combine an agenda, session notes,
slide images, follow-up resources, and attendee-facing materials.

Use for:

- detailed event reports
- training-session summaries
- workshop records with slides and follow-up resources
- speaker/session microsites
- browser-openable replacements for a PDF report or PowerPoint handout

Core layout:

- image-led hero using an embedded slide or photograph
- sticky section navigation
- programme timeline
- session detail cards
- embedded slide/image gallery
- speaker cards
- materials and provenance sections

Design notes:

- selected slide images should be embedded as Base64 data URIs
- source Markdown notes should become readable HTML sections, not text downloads
- the report should work as a browsable archive and a polished first-read document
- keep source paths/provenance visible enough for later audit

Implementation notes:

- Use `lucide-react` icons such as `Presentation`, `CalendarClock`, `MessagesSquare`, `Images`, `UsersRound`, `FileArchive`, and `ScrollText`.
- Create a normal multi-section site first, then package selected images into the final single HTML.
- Use separate downloadable attachments only for full decks, CSVs, PDFs, or media that genuinely need separate distribution.

## Option 9: Composed Blocks

Inspired by component library and pattern-handbook deliverables, including the patterns demonstrated at thariqs.github.io/html-effectiveness.

Use for:

- pattern handbooks for a team
- design-system reference pages
- narrative walkthroughs that lean heavily on reusable visual structure
- documentation deliverables where the blocks themselves are the subject
- explainers that need TL;DRs, timelines, callouts, swatches, and diagrams in one place

Core layout:

- compact header with deliverable framing
- TL;DR block at the top
- grouped sections, one per block family or one per topic
- block instances shown with their authored type label (handbook variant) or as illustrative ingredients (walkthrough variant)
- closing FAQ and source/provenance section

Design notes:

- treat the page like documentation, not a dashboard
- lean on whitespace between blocks
- prefer one block per concept rather than chaining three of the same kind
- the handbook variant labels each block instance with its `type`; the walkthrough variant uses the blocks as illustration in service of narrative
- when the deliverable also defines its own severity vocabulary, lead with a `severity-tag` block so other blocks can reference it visually

Implementation notes:

- Read [`references/blocks/_protocol.md`](blocks/_protocol.md) before authoring; the protocol determines packaging behaviour for static and interactive blocks.
- Use the per-block files under `references/blocks/` as the source of truth for each block's schema; renderers live next to them under `scripts/blocks/`.
- Interactive blocks register against the shared bootstrap at `scripts/blocks/_bootstrap.js`; both the bootstrap and any used renderers must be inlined when packaging.
- Keep authored block content in YAML/JSON; let the compiler pre-render Markdown fields to HTML before passing them to renderers.
- Use the `custom` block sparingly. The audit script flags concentrations.

## Keeping The Existing Samples

The three current samples should remain in the toolkit because they are useful starter patterns:

- `dashboard-report` is the small-report version of institutional analytics.
- `event-briefing` is the lighter version of committee/workshop briefing.
- `gallery-report` is the media inspection pattern.

Do not treat new options as replacements. Treat them as a larger menu.

## Improving Generated Catalogue Direction

Generated catalogue pages already prove the right core idea: single HTML, generated from structured records, with filters, share pages, and meeting-friendly bespoke variants. Improvements should focus on reusable implementation quality:

- extract shared design tokens for institutional pages
- replace repeated hand-coded SVG/icon snippets with `lucide-react` icons in source components
- generate the catalogue, dossier, committee briefing, and tabbed workshop from the same content model
- keep the stricter record-catalogue look for inventories, but use committee/dossier styles for circulation pages
- add source/provenance drawers rather than only truncating long body text
- add accessible tabs and filter controls
- make print views intentional
- run strict single-file audit on every generated share page

## React Icon Rule

When a report uses React, prefer `lucide-react` for icons:

```bash
bun add lucide-react
```

```tsx
import { CalendarDays, Download, FileText, Filter, Search } from "lucide-react";

export function MetadataChip({ children }: { children: React.ReactNode }) {
  return (
    <span className="metadata-chip">
      <CalendarDays aria-hidden="true" size={18} strokeWidth={1.8} />
      {children}
    </span>
  );
}
```

Rules:

- import only the icons used by the page
- set icons to `aria-hidden="true"` unless the icon is the only visible label
- use `currentColor` styling through CSS, not hard-coded icon colours
- use consistent sizes: 16px for dense tables, 18-20px for controls, 22-24px for metric tiles
- bundle icons into the app at build time; do not use icon CDNs in the final file
- verify the packaged HTML has no external icon/font requests

The static design samples use inline SVG icons with Lucide-style stroke rules so
the samples remain dependency-free. Production React implementations should use
`lucide-react` source imports and let the normal bundle/package step inline the
result.
