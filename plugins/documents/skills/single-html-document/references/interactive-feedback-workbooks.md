# Interactive Feedback Workbooks

Use this pattern when the single HTML file is a review form or QA workbook that
collects feedback from people outside the project environment.

## When To Use

Choose this pattern for:

- review forms sent by email or chat
- QA workbooks for a fixed list of pages, records, or tasks
- terminology, wording, claim, or definition review where comments need to
  attach to exact visible text
- offline feedback collection where the reviewer should return one file
- feedback that may include screenshots, voice notes, or other reviewer-added
  media

This is different from a read-only report. The file is both the delivered UI and
the data collection tool.

## Choose The Feedback Mode

Use section-level feedback when reviewers are judging whole items: pages,
screens, records, checklist tasks, sections, or deployed URLs. These workbooks
usually need status buttons, free-text notes, screenshots, and optional audio.

Use selected-text annotation feedback when reviewers are judging wording:
definitions, examples, claims, policy language, captions, or source excerpts.
The reviewer should select visible text, add a note to that exact quote, and
return the quote plus enough surrounding context to locate it later.

Use the commentable JAWGAI workbook pattern when the file is meant to come back
to the agent: reviewer name, overall note, a drawer that opens by default, a
small selection CTA, one canonical local-storage state, Copy for chat/agent,
Copy JSON, Download JSON, and Clear all with confirmation.

Use both modes in dense editorial workbooks. Keep one canonical feedback state
per review item, then let the UI render item comments, selected-text notes, and
media attachments from that state.

For general-purpose reader notes and editable draft review, read
`reader-annotation-and-editing.md`. This workbook reference specialises that
broader contract for QA and review forms.

## Authoring Structure

Keep these separate while building:

- source review plan or item data, usually JSON, YAML, or Markdown
- source JavaScript with comments
- source CSS
- generated single HTML output

The build step should inject the review data into the client script and then
inline the packaged script into the HTML. Avoid editing the generated HTML by
hand.

For feedback workbooks, expose a clear review item id in the rendered DOM. Text
selection, comments, media attachments, and removal controls should all resolve
back to this id so the exported JSON can be handled mechanically.

## JavaScript Packaging

Use an explicit package-time marker for injected data:

```js
const REVIEW_PLAN = __PLAN_JSON__;
```

The packager should replace the marker with serialized JSON, strip comments from
the distribution copy, and include the resulting script in the final HTML.

Add regression checks that assert:

- the marker is not present in the generated HTML
- the packaged script parses as JavaScript
- source-only comments are not present in the generated script
- the generated file has no external script, stylesheet, font, or asset
  dependency unless deliberately allowed

Keep comments in the source file. Strip them only from the packaged copy.

## Reviewer Controls

Prefer selected-state buttons over radio controls for compact review status.
Use labels such as:

- Works well
- Possible improvement
- Needs a fix

Make clicking the selected state clear it. Store the state as a short stable
value such as `pass`, `partial`, or `fail`.

Add removal controls at the level where reviewers notice the problem:

- remove a single item comment from the review summary
- remove a single selected-text note from the review summary
- remove audio or screenshot attachments from their item
- remove all feedback on a single item from that item's feedback box
- clear the whole workbook only as a separate global action with confirmation

Removal must update the canonical state and the export. Do not only hide the
visible note.

## Review-All-Notes Panel

For workbooks with more than a few review items, add a summary panel near the
top of the page that aggregates everything the reviewer has added.

The panel should show:

- item comments
- selected-text notes with their quote
- media attachment indicators
- links back to the original item

Make text notes editable in this panel. Edits must write back to the canonical
item state and, when relevant, the original item textarea. Do not create a
separate summary-only note store.

Avoid re-rendering the whole panel on every keystroke inside the panel. Persist
the edit, update progress, and only re-render the panel when notes are added or
removed. Otherwise focus can jump while the reviewer is moving through the
summary.

## Selected-Text Annotations

For editorial review, capture selected visible text inside the relevant review
item and show a small note popover. Ignore selections inside feedback controls
so reviewers can edit textareas normally.

Store each annotation with:

- stable annotation id
- item id
- selected quote
- note
- context before the quote
- context after the quote
- timestamp

Exact visual re-highlighting is useful but should be conservative. If the quote
crosses multiple text nodes or cannot be re-highlighted after reload, the JSON
export should still be complete enough to act on.

Minimal annotation shape:

```json
{
  "id": "item-1-annotation-abc123",
  "itemId": "item-1",
  "quote": "selected visible text",
  "note": "Reviewer note",
  "contextBefore": "text before",
  "contextAfter": "text after",
  "createdAt": "2026-04-29T09:20:00.000Z"
}
```

### Annotation And Review Summary Starter

This is the browser-side shape to adapt into a source runtime. Keep the source
runtime separate from the generated HTML, then inject and strip it at package
time.

```js
const state = {
  items: {
    "item-1": {
      rating: "",
      comment: "",
      annotations: [],
      attachments: [],
    },
  },
};
const mediaRuntime = FeedbackMediaRuntime.createFeedbackMediaRuntime();

function itemState(itemId) {
  if (!state.items[itemId]) {
    state.items[itemId] = { rating: "", comment: "", annotations: [], attachments: [] };
  }
  return state.items[itemId];
}

function saveSelectedTextNote({ itemId, quote, note, contextBefore, contextAfter }) {
  const annotation = mediaRuntime.createTextAnnotation({ itemId, quote, note, contextBefore, contextAfter });

  if (!annotation) return null;
  itemState(itemId).annotations.push(annotation);
  persistFeedbackState();
  renderItemAnnotations(itemId);
  renderReviewAllNotes();
  return annotation;
}

function renderReviewAllNotes() {
  const notes = Object.entries(state.items).flatMap(([itemId, feedback]) => [
    ...(feedback.comment ? [{ kind: "comment", itemId, text: feedback.comment }] : []),
    ...feedback.annotations.map((annotation) => ({ kind: "annotation", itemId, annotation })),
    ...(feedback.attachments.length ? [{ kind: "attachments", itemId, attachments: feedback.attachments }] : []),
  ]);

  renderNotesPanel(notes);
}

async function removeAllFeedbackForItem(itemId, mediaRuntime) {
  const feedback = itemState(itemId);

  for (const attachment of feedback.attachments) {
    await mediaRuntime.deleteMediaAttachment(attachment.id);
  }

  feedback.rating = "";
  feedback.comment = "";
  feedback.annotations = [];
  feedback.attachments = [];

  persistFeedbackState();
  renderItemAnnotations(itemId);
  renderReviewAllNotes();
}
```

## Reviewer-Added Attachments

Reviewer-added media is not the same as embedded distribution attachments.
Screenshots and voice notes are created after the HTML has been delivered, so
they need a runtime storage and export path.

Use this hierarchy:

1. Save text drafts first.
2. Store media in IndexedDB when available.
3. Fall back to in-memory media with a persistent warning.
4. Provide a visible backup/export action.

Do not store screenshots or audio in `localStorage`. Browser quotas are small
and inconsistent, and base64 expands binary payloads by about one third. Keep
`localStorage` for compact text drafts and reviewer settings only.

## Collection Code Examples

These examples are dependency-free browser code that can be adapted into the
separate source JavaScript file before packaging. Keep the comments in source
and strip them only from the generated distribution script.

For a reusable copyable helper, use
`scripts/feedback-media-runtime.js`. It exposes
`FeedbackMediaRuntime.createFeedbackMediaRuntime()` in the browser.

### IndexedDB Media Store

Store blobs in IndexedDB and keep only small text draft state in `localStorage`.
If IndexedDB fails, keep media in memory and warn the reviewer to save before
closing the page.

```js
const MEMORY_MEDIA = new Map();

function openMediaDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("feedback-media", 1);

    request.onupgradeneeded = () => {
      request.result.createObjectStore("attachments", { keyPath: "id" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function saveMediaAttachment(record, blob) {
  try {
    const db = await openMediaDb();

    await new Promise((resolve, reject) => {
      const tx = db.transaction("attachments", "readwrite");
      tx.objectStore("attachments").put({ ...record, blob });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });

    return { storage: "indexeddb", warning: null };
  } catch (error) {
    MEMORY_MEDIA.set(record.id, { ...record, blob });
    return {
      storage: "memory",
      warning: "Attached media will be lost if this page is closed before saving.",
    };
  }
}

async function loadMediaAttachment(id) {
  if (MEMORY_MEDIA.has(id)) return MEMORY_MEDIA.get(id);

  const db = await openMediaDb();

  return new Promise((resolve, reject) => {
    const tx = db.transaction("attachments", "readonly");
    const request = tx.objectStore("attachments").get(id);

    request.onsuccess = () => resolve(request.result || null);
    request.onerror = () => reject(request.error);
  });
}
```

### Screenshot Upload And Paste

Use file upload for reliability and paste handling for convenience. Store the
original blob rather than converting to base64 immediately.

```html
<input id="screenshot-input" type="file" accept="image/*" />
```

```js
function createAttachmentRecord({ itemId, kind, file }) {
  const extension = file.name.split(".").pop() || "bin";
  const id = `${itemId}-${kind}-${crypto.randomUUID()}`;

  return {
    id,
    itemId,
    kind,
    fileName: `${itemId}-${kind}.${extension}`,
    mimeType: file.type || "application/octet-stream",
    sizeBytes: file.size,
    createdAt: new Date().toISOString(),
  };
}

async function collectScreenshotFile(itemId, file) {
  if (!file || !file.type.startsWith("image/")) return null;

  const record = createAttachmentRecord({
    itemId,
    kind: "screenshot",
    file,
  });
  const result = await saveMediaAttachment(record, file);

  return { ...record, storage: result.storage, warning: result.warning };
}

document.querySelector("#screenshot-input").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  const attachment = await collectScreenshotFile("review-item-1", file);

  if (attachment?.warning) showMediaWarning(attachment.warning);
  if (attachment) addAttachmentToDraft(attachment);
});

document.addEventListener("paste", async (event) => {
  const imageItem = [...event.clipboardData.items].find((item) =>
    item.type.startsWith("image/")
  );
  if (!imageItem) return;

  const file = imageItem.getAsFile();
  const attachment = await collectScreenshotFile("review-item-1", file);

  if (attachment?.warning) showMediaWarning(attachment.warning);
  if (attachment) addAttachmentToDraft(attachment);
});
```

### Voice Upload And Recording

Support audio upload first. Add recording when `MediaRecorder` is available and
cap the recording duration.

```html
<input id="voice-input" type="file" accept="audio/*" />
<button type="button" id="record-voice">Record</button>
<button type="button" id="stop-voice" disabled>Stop</button>
```

```js
async function collectVoiceFile(itemId, file) {
  if (!file || !file.type.startsWith("audio/")) return null;

  const record = createAttachmentRecord({
    itemId,
    kind: "voice-note",
    file,
  });
  const result = await saveMediaAttachment(record, file);

  return { ...record, storage: result.storage, warning: result.warning };
}

document.querySelector("#voice-input").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  const attachment = await collectVoiceFile("review-item-1", file);

  if (attachment?.warning) showMediaWarning(attachment.warning);
  if (attachment) addAttachmentToDraft(attachment);
});

async function startVoiceRecording(itemId) {
  if (!("MediaRecorder" in window)) {
    showMediaWarning("Recording is not available in this browser. Upload an audio file instead.");
    return;
  }

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream);
  const chunks = [];
  const stopAfterMs = 60_000;

  recorder.addEventListener("dataavailable", (event) => {
    if (event.data.size > 0) chunks.push(event.data);
  });

  recorder.addEventListener("stop", async () => {
    stream.getTracks().forEach((track) => track.stop());

    const mimeType = recorder.mimeType || "audio/webm";
    const blob = new Blob(chunks, { type: mimeType });
    const file = new File([blob], `${itemId}-voice-note.webm`, { type: mimeType });
    const attachment = await collectVoiceFile(itemId, file);

    if (attachment?.warning) showMediaWarning(attachment.warning);
    if (attachment) addAttachmentToDraft(attachment);
  });

  recorder.start();
  window.setTimeout(() => {
    if (recorder.state === "recording") recorder.stop();
  }, stopAfterMs);

  document.querySelector("#stop-voice").disabled = false;
  document.querySelector("#stop-voice").onclick = () => recorder.stop();
}

document.querySelector("#record-voice").addEventListener("click", () => {
  startVoiceRecording("review-item-1");
});
```

### Export Media In Returned JSON

Convert blobs to base64 only when exporting. This keeps runtime storage smaller
and makes it easier to fall back to a text-only export if the payload is too
large.

```js
function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => {
      const dataUrl = String(reader.result);
      resolve(dataUrl.slice(dataUrl.indexOf(",") + 1));
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

async function buildFeedbackExport(draft) {
  const attachments = [];

  for (const attachment of draft.attachments) {
    const stored = await loadMediaAttachment(attachment.id);

    if (!stored?.blob) {
      attachments.push({ ...attachment, payloadMissing: true });
      continue;
    }

    attachments.push({
      ...attachment,
      payloadEncoding: "base64",
      payload: await blobToBase64(stored.blob),
    });
  }

  const payload = {
    feedbackSchemaVersion: 2,
    generatedAt: new Date().toISOString(),
    reviewer: draft.reviewer || "anonymous",
    items: draft.items,
    attachments,
    mediaIncluded: attachments.every((item) => !item.payloadMissing),
  };

  const encodedSize = new Blob([JSON.stringify(payload)]).size;
  return { ...payload, encodedSizeBytes: encodedSize };
}
```

## Voice Notes

Support upload first because it works across more browsers and permission
contexts. Add recording with `MediaRecorder` when available.

Recommended constraints:

- cap recording duration, usually 60 seconds
- show recording state clearly
- save the MIME type from the recorded blob
- keep a manual upload fallback
- include audio metadata in the exported feedback

If transcription is part of the workflow, treat it as an extraction step after
the returned JSON is received. Do not require transcription in the browser
workbook unless the user explicitly asks for that complexity.

## Export Contract

Use a versioned payload:

```json
{
  "feedbackSchemaVersion": 2,
  "generatedAt": "2026-04-26T17:49:36.000Z",
  "reviewDocument": "Document being reviewed",
  "reviewDocumentId": "document-id",
  "reviewer": "anonymous",
  "overallComment": "",
  "summary": {
    "totalItems": 12,
    "commentedItems": 3,
    "annotationCount": 2,
    "attachmentCount": 1
  },
  "items": []
}
```

Each item should include:

- stable id
- type, title, and section where available
- status or rating
- free-text comment
- `annotations`, as selected-text notes
- `attachments`, as reviewer-added media records

Each attachment should include:

- stable id
- review item id
- kind, such as `screenshot` or `voice-note`
- file name
- MIME type
- byte size
- base64 payload when included
- `payloadMissing` when the attachment metadata exists but the browser no
  longer has the media payload

If the export becomes too large for the expected return channel, provide a
text-only fallback and ask the reviewer to send original media separately.

## Progress Navigation

For dense review lists, show item progress in the navigation sidebar.

Use icon-only status markers when space is tight:

| State | Label | Colour |
| --- | --- | --- |
| unrated | Not rated | grey |
| pass | Works well | green |
| partial | Possible improvement | orange |
| fail | Needs a fix | red |

Each marker needs a tooltip and accessible label. The icon should update as soon
as the rating changes.

## Verification Checklist

Before distributing:

1. Generate the single HTML file from source.
2. Run static checks against the generated file.
3. Parse or compile-check the packaged JavaScript.
4. Open the file from disk with `file://`.
5. If browser automation blocks `file://`, use a temporary local HTTP server for
   smoke testing while preserving disk-open compatibility.
6. Add ratings, notes, a screenshot, and a voice note.
7. Confirm progress navigation updates.
8. Add a selected-text annotation when the workbook supports editorial review.
9. Edit item comments and selected-text notes from the review-all-notes panel.
10. Remove a comment, selected-text note, media attachment, and all feedback on
    one item.
11. Export feedback JSON.
12. Confirm edited feedback is present and removed feedback is absent.
13. Extract media attachments from the JSON and confirm they open.
14. Transcribe a test voice note when the project requires audio verification.

Use reviewer-facing labels such as "Save feedback file", "Copy feedback for
email", and "What to send back". Avoid technical storage or encoding language in
the primary UI.

Use `scripts/extract-feedback-media.mjs` to unpack returned media:

```bash
node "${CLAUDE_SKILL_DIR}/scripts/extract-feedback-media.mjs" feedback.json --out feedback-media
```
