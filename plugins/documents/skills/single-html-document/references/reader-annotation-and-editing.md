# Reader Annotation And Editing

Use this reference when a single HTML document is not only read, but also used
as a working surface. The two core modes are:

- **Annotation mode**: the reader highlights visible text, attaches a note, and
  exports those notes as JSON.
- **Edit-diff mode**: the reader edits marked text regions and exports a diff
  between the original packaged text and their edited version.

Both modes must work from `file://`, require no server, and keep the export
small enough to send by email or chat.

For a reusable browser helper, use `scripts/feedback-media-runtime.js`. It now
includes `createTextAnnotation()`, `createTextEditRecord()`, and
`buildInteractionExport()` alongside screenshot, audio, and media-export
helpers.

## Proven Interaction Shapes

The JAWGAI stress-testing documents use two useful variants that should guide
future implementations:

- **Annotatable document**: a lightweight layer injected into an existing share
  page. It adds a floating Notes button, a drawer, selection CTA, local-storage
  persistence, Markdown download, rich-text copy, jump-to-highlight, and
  remove-note controls. It lets the reader highlight first and add or edit the
  note afterwards.
- **Review workbook**: a stricter feedback surface for returned comments. It
  opens with a feedback drawer, captures reviewer name and overall note, asks
  for a note before saving a selection comment, and exports both chat-ready
  Markdown and structured JSON.

Use the lighter annotatable document when the artifact is mostly for reading
and occasional notes. Use the review workbook when the user expects returned
feedback that an agent or script can process.

## When To Use

Use annotation mode for:

- policy, guidance, or explainer review
- close reading of claims, wording, definitions, examples, or captions
- committee or workshop documents where comments need to point to exact text
- teaching or training material where readers collect notes while reading

Use edit-diff mode for:

- draft wording review
- policy language edits
- training-copy edits
- short proposal edits
- HTML replacements for tracked-change Word review when a browser-only return
  file is enough

Use both modes when reviewers need to comment on some passages and directly
rewrite others. Keep the modes visually distinct: note-taking should not make
the reader wonder whether they are changing the source text.

## Source Contract

Mark interaction targets in generated HTML with stable IDs. Do not rely on CSS
classes alone. For generated narrative documents, it is acceptable for the
client runtime to assign block IDs at startup, but the assignment must be
derived from stable section anchors and block order.

```html
<section id="scope" data-annotatable data-source-ref="pages/02-scope.md">
  <h2>Scope</h2>
  <p>Readers can highlight this paragraph and add a note.</p>
</section>

<p
  id="draft-purpose"
  data-editable
  data-source-ref="pages/01-purpose.md#purpose"
>
  This sentence can be edited by the reviewer.
</p>
```

The compiler should emit an interaction manifest or a JSON script tag with the
selectors needed by the runtime:

```json
{
  "schemaVersion": 1,
  "documentId": "example-document",
  "contentSelector": "main",
  "sectionSelector": "section[id]",
  "blockSelector": "p, li, h1, h2, h3, h4, dt, dd",
  "annotations": {
    "enabled": true,
    "targets": ["scope"]
  },
  "editDiff": {
    "enabled": true,
    "targets": ["draft-purpose"]
  }
}
```

## Annotation Mode

Capture selections only inside `[data-annotatable]`. Ignore selections inside
inputs, textareas, buttons, dialogs, and existing note controls.

For a broad reading document, the runtime can treat a configured content
selector as annotatable and assign IDs to paragraphs, bullets, and headings.
Use the explicit `[data-annotatable]` contract when only some regions should be
commentable.

Store enough context to recover the note even if exact visual re-highlighting
fails later:

```json
{
  "id": "annotation-abc123",
  "documentId": "example-document",
  "targetId": "scope",
  "sourceRef": "pages/02-scope.md",
  "quote": "highlighted visible text",
  "note": "Reader note",
  "contextBefore": "words before the quote",
  "contextAfter": "words after the quote",
  "createdAt": "2026-05-10T14:30:00.000Z",
  "updatedAt": "2026-05-10T14:31:00.000Z"
}
```

UI requirements:

- show a small note popover after a valid text selection
- show existing notes in a drawer or review-all-notes panel
- let readers jump from a note back to the highlighted text
- let readers edit and delete notes before export
- persist draft notes in `localStorage`
- export notes as versioned JSON, and optionally as Markdown or rich text for
  email/chat workflows
- make storage boundaries explicit: local notes stay in this browser until the
  reader copies or downloads them

Do not promise perfect text highlighting. The export is the durable artifact;
visual highlights are a convenience.

When readers should be able to highlight first and write later, call
`createTextAnnotation()` with `requireNote: false` or create the draft record in
the document runtime and fill `note` as the drawer textarea changes. When the
workflow is a formal feedback workbook, require a non-empty note before saving.

## Edit-Diff Mode

Only marked elements become editable. The build must capture the original text
snapshot before the reader edits anything.

Recommended generated shape:

```html
<p
  id="draft-purpose"
  data-editable
  data-original-text="This sentence can be edited by the reviewer."
  contenteditable="true"
>
  This sentence can be edited by the reviewer.
</p>
```

For larger passages, avoid storing long original text in an attribute. Put the
snapshot in the interaction manifest instead and reference it by `id`.

Export a structured JSON diff rather than only a plain text blob:

```json
{
  "editDiffSchemaVersion": 1,
  "documentId": "example-document",
  "generatedAt": "2026-05-10T14:40:00.000Z",
  "edits": [
    {
      "targetId": "draft-purpose",
      "sourceRef": "pages/01-purpose.md#purpose",
      "originalText": "This sentence can be edited by the reviewer.",
      "editedText": "This sentence has been tightened by the reviewer.",
      "diff": [
        { "op": "equal", "text": "This sentence " },
        { "op": "delete", "text": "can be edited" },
        { "op": "insert", "text": "has been tightened" },
        { "op": "equal", "text": " by the reviewer." }
      ]
    }
  ]
}
```

Use a word-level diff for prose by default. Use line-level diff only for code,
tables, or structured text where line boundaries matter.

UI requirements:

- make editable regions visually obvious but quiet
- provide reset for each editable region
- show changed/unchanged state
- export only changed regions by default
- optionally include unchanged snapshots when auditability matters

## Combined Export

When both modes are enabled, one export file can contain both note and edit
records:

```json
{
  "singleHtmlDocumentFeedbackVersion": 1,
  "documentId": "example-document",
  "generatedAt": "2026-05-10T14:45:00.000Z",
  "annotations": [],
  "edits": []
}
```

Name buttons for readers, not implementers:

- `Save notes`
- `Save edits`
- `Save notes and edits`
- `Copy notes for email`

Avoid labels like "serialize JSON" or "download payload" in the primary UI.

## Privacy And Safety

Before distribution:

- confirm annotation targets do not expose private source text accidentally
- confirm edit targets are limited to intended regions
- confirm exported JSON contains no local absolute paths
- confirm no server endpoint is implied unless the user explicitly asks for one
- confirm the document still reads correctly if JavaScript fails

Before accepting returned data:

- treat exported JSON as untrusted input
- inspect payload size before processing
- never apply edits automatically to source files without review
- keep `sourceRef` as a locator, not proof that the source still matches

## Verification

For annotation mode:

1. Open the packaged file from disk.
2. Highlight text in an annotatable region.
3. Add a note, edit it, delete it, and add another.
4. Reload and confirm draft persistence.
5. Export JSON and check `quote`, `contextBefore`, `contextAfter`, and
   `targetId`.

For edit-diff mode:

1. Edit one marked region.
2. Reset another marked region.
3. Export JSON.
4. Confirm unchanged regions are omitted unless configured otherwise.
5. Confirm each changed region includes original text, edited text, and a diff.

For combined mode, verify that notes and edits export together and remain
separate arrays.
