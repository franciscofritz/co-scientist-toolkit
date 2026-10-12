# HTML Effectiveness Pattern Fidelity

Use this reference when a user asks for an interactive, visual, reviewable, or
"not just a report" single-file HTML document.

The `html-effectiveness` examples are not mood-board inspiration. They are
task-shaped UI contracts. Pick the closest contract and reproduce its working
structure before inventing custom chrome.

Source: <https://thariqs.github.io/html-effectiveness/>

## Core Principle

Do not translate "make this interactive" into generic tabs, cards, filters, or
a dashboard wrapper.

Translate the user's task into the matching artifact type:

- compare options -> side-by-side option boards
- review code -> annotated diff with file risk map and jump links
- understand a system -> module map or request path
- tune behaviour -> sliders or live preview
- make a choice -> drag board or compact editor
- inspect visual options -> contact sheet
- learn a concept -> TL;DR, step path, tabs, glossary, FAQ
- report status -> metric strip, timeline, shipped/slipped sections

If the chosen pattern has an interaction, the deliverable must implement that
interaction in the same spirit:

- drag means actual drag/reorder, not static columns
- tuner means editable inputs with live rendered output
- feature flags means dependency/conflict warnings and changed-config export
- annotated diff means line-linked notes and severity tags
- flowchart means clickable steps with details
- visual design exploration means real variants side by side

## Pattern Map

### Exploration And Planning

Use when the user is still choosing an approach.

Canonical examples:

- `01-exploration-code-approaches.html`
- `02-exploration-visual-designs.html`
- `16-implementation-plan.html`

Required shape:

- multiple complete alternatives, visible together
- trade-offs attached to each alternative, not buried later
- recommendation or handoff plan
- visual or code representation for each option

Do not make a narrative essay with a few cards. The whole point is parallel
inspection.

### Code Review And Understanding

Use when the source material is a PR, diff, repo, package, module, or code
change.

Canonical examples:

- `03-code-review-pr.html`
- `04-code-understanding.html`
- `17-pr-writeup.html`

Required shape:

- file/module risk map
- annotated diff or module map
- severity tags near the reviewed surface
- jump links from summary to exact evidence
- suggested next steps

Do not summarize a code review as prose when the diff or module relationships
can be visible.

### Design Review

Use when reviewing visual directions, components, tokens, or variants.

Canonical examples:

- `05-design-system.html`
- `06-component-variants.html`

Required shape:

- contact sheet or token sheet
- live component states or variants
- copyable tokens when tokens are the object
- compact metadata near each variant

Do not describe designs that can be rendered.

### Prototyping

Use when the question is about feel, timing, interaction, or flow.

Canonical examples:

- `07-prototype-animation.html`
- `08-prototype-interaction.html`

Required shape:

- actual motion or click-through state
- controls for the tunable parameters
- visible current settings
- reset/copy/export when useful

Do not describe the interaction in paragraphs alone.

### Diagrams

Use when the shape of a system or process matters.

Canonical examples:

- `10-svg-illustrations.html`
- `13-flowchart-diagram.html`

Required shape:

- inline SVG or structured diagram, not ASCII or prose-only flow
- clickable nodes when there are hidden details
- readable labels and arrow paths
- legend for statuses, decisions, or paths

Do not use decorative diagrams. The diagram must carry reviewable information.

### Decks

Use when the artifact must be presented live.

Canonical example:

- `09-slide-deck.html`

Required shape:

- one slide viewport at a time
- arrow-key navigation
- progress state
- overview or source appendix when substantial

Do not turn slide work into a scrolling report unless the user asks for that.

### Research And Learning

Use when the user asks for an explainer, feature walkthrough, or concept
learning artifact.

Canonical examples:

- `14-research-feature-explainer.html`
- `15-research-concept-explainer.html`

Required shape:

- TL;DR panel
- step-by-step path or live model
- tabbed code/config samples
- glossary near where terms appear
- FAQ for edge cases

Do not make the reader hold the whole explanation in a linear essay.

### Reports

Use when the user needs a status update, incident review, post-mortem, or
operational report.

Canonical examples:

- `11-status-report.html`
- `12-incident-report.html`

Required shape:

- metric strip
- coloured status or severity vocabulary
- timeline when time order matters
- shipped/slipped or impact/follow-up sections
- checklist of next actions

Do not create a plain report with decorative cards.

### Custom Editors

Use when the user needs to review, sort, tune, or return structured decisions.

Canonical examples:

- `18-editor-triage-board.html`
- `19-editor-feature-flags.html`
- `20-editor-prompt-tuner.html`

Required shape:

- task-specific editor surface
- local state
- reset
- export/copy button that returns useful Markdown, JSON, diff, or config
- warnings for invalid combinations when the editor has dependencies

Do not make generic notes the only output. The edited state is the deliverable.

## Fidelity Gate

Before writing UI code, create a short pattern contract in the project notes or
source README:

```text
html-effectiveness source pattern: 18-editor-triage-board
local block/pattern equivalents: drag-reorder, severity-tag, global-search
must preserve:
  - drag cards between lanes
  - visible lane counts
  - tag/filter affordance
  - copy as markdown
allowed adaptation:
  - labels and content
  - colour tokens
  - extra review-note export
not allowed:
  - replacing drag with static cards
  - replacing export with prose summary
```

## New Pattern Escalation

New interaction patterns are allowed only when the existing
`html-effectiveness` patterns and local archetypes are not suitable for the
user's task.

Do not silently invent a new pattern during delivery work. Use this sequence:

1. Exhaust the existing pattern map.
   Name the closest candidates and explain why each one fails the task.
2. Propose the new pattern to the user before implementation.
   Keep the proposal short and concrete:

   ```text
   proposed pattern name:
   user task it serves:
   why existing patterns do not fit:
   core interaction:
   export/copy contract:
   approval question:
   ```

3. Build a narrow test implementation.
   The prototype should prove the main interaction, not finish the whole
   document.
4. Ask for approval against the prototype.
   If the user rejects it, return to the existing patterns or revise the
   proposal.
5. After approval, update this skill.
   Add the new pattern to this reference with:

   - pattern name
   - when to use it
   - canonical local example or prototype path
   - required shape
   - not-allowed substitutions
   - verification checks

Until that approval happens, treat the pattern as experimental and document it
in the project source notes only.

## Common Failure Mode

Bad:

- read the pattern catalogue
- extract words such as "module map", "flowchart", "triage", "sliders"
- hand-roll a new dashboard that happens to contain those words

Good:

- pick one or two canonical source examples
- inspect their visible structure and interaction contract
- map the user's content into that contract
- reuse existing block renderers where possible
- verify that the interaction still does the same job

## Verification Checklist

The final browser check must answer yes to these:

- Does the page visibly resemble the selected source pattern's layout type?
- Does the main interaction from the source pattern actually work?
- Is there a task-specific export/copy path when the pattern has one?
- Are statuses, risk tags, and counts visible where the reviewer is looking?
- Is the source text still incorporated into the document?
- Could a reviewer make a decision from the visual surface without reading the
  whole prose report first?
