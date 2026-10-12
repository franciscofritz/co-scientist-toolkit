# Attachment Runtime Helpers

## Purpose

Single-file reports sometimes need to distribute files as files: PDFs, CSVs,
spreadsheets, slide decks, ZIPs, or original media. Those are legitimate
downloads. Text sources such as Markdown notes, JSON records, transcripts, and
source manifests should normally be rendered into the page instead.

Use this pattern when a binary or tabular artifact must be embedded inside the
HTML and exported on demand.

For feedback workbooks, separate packaged attachments from reviewer-added
attachments. Packaged attachments are embedded before delivery. Reviewer-added
screenshots and audio are created after delivery and need runtime storage,
usually IndexedDB, plus an export path in the returned feedback file.

## Attachment Record Shape

Use the same shape emitted by `scripts/make-attachment-manifest.mjs`:

```ts
type AttachmentRecord = {
  id: string;
  fileName: string;
  relativePath: string;
  mimeType: string;
  originalSizeBytes: number;
  storedSizeBytes: number;
  encoding: 'base64' | 'gzip+base64';
  sha256: string;
  payload: string;
};
```

## Browser Runtime

This helper is framework-neutral. It works in React, Astro, Eleventy, or a
hand-written HTML bootstrap.

```js
function base64ToBytes(payload) {
  const binary = atob(payload);
  const bytes = new Uint8Array(binary.length);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  return bytes;
}

async function decompressGzipBytes(bytes, mimeType) {
  if (!('DecompressionStream' in globalThis)) {
    throw new Error('This browser does not support DecompressionStream.');
  }

  const compressed = new Blob([bytes], { type: 'application/gzip' });
  const stream = compressed.stream().pipeThrough(new DecompressionStream('gzip'));
  const blob = await new Response(stream).blob();

  return new Blob([blob], { type: mimeType });
}

export async function materializeAttachment(record) {
  const bytes = base64ToBytes(record.payload);

  if (record.encoding === 'gzip+base64') {
    return decompressGzipBytes(bytes, record.mimeType);
  }

  if (record.encoding === 'base64') {
    return new Blob([bytes], { type: record.mimeType });
  }

  throw new Error(`Unsupported attachment encoding: ${record.encoding}`);
}

export async function createAttachmentUrl(record) {
  const blob = await materializeAttachment(record);
  return URL.createObjectURL(blob);
}

export async function downloadAttachment(record) {
  const url = await createAttachmentUrl(record);
  const anchor = document.createElement('a');

  anchor.href = url;
  anchor.download = record.fileName || record.id || 'attachment';
  anchor.rel = 'noopener';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
}
```

## Preview Pattern

For previews, keep the object URL alive while the preview element remains in the
DOM. Revoke it only when the preview closes or the component unmounts.

```js
let previewUrl;

async function openPreview(record, iframe) {
  if (previewUrl) URL.revokeObjectURL(previewUrl);

  previewUrl = await createAttachmentUrl(record);
  iframe.src = previewUrl;
}

function closePreview(iframe) {
  iframe.removeAttribute('src');

  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
    previewUrl = undefined;
  }
}
```

## Download Policy

Default to these classes:

| Class | Examples | Runtime behaviour |
| --- | --- | --- |
| `reader-text` | Markdown report, transcript, meeting notes | Render in page |
| `source-text` | source manifest, prompt text, JSON record | Render in source drawer or appendix |
| `artifact-download` | PDF, CSV, XLSX, PPTX, ZIP | Embed as payload and export with Blob URL |
| `remote-reference` | citation, hosted video, live slide embed | Link or embed intentionally |

Do not hide local text sources behind download buttons. If the reader needs the
text to understand the report, it belongs in the HTML.

## Build-Time Rule

Generate attachment manifests at build time:

```bash
node "${CLAUDE_SKILL_DIR}/scripts/make-attachment-manifest.mjs" \
  --root media/attachments \
  --output src/data/generated/attachments.generated.ts \
  --gzip \
  media/attachments
```

Use `--gzip` for text-heavy artifacts and test whether it helps for already
compressed files such as PDFs, JPEGs, PNGs, and WebP images.

## Audit Rule

The final HTML should not contain local artifact links unless they are
intentionally permitted by the audit:

```bash
node "${CLAUDE_SKILL_DIR}/scripts/audit-single-html.mjs" dist/document.html --strict
```

If the deliverable intentionally points to adjacent artifact files rather than
embedding them, run:

```bash
node "${CLAUDE_SKILL_DIR}/scripts/audit-single-html.mjs" dist/document.html --strict --allow-local-artifacts
```

For the normal single-file report workflow, prefer embedding artifacts and
exporting them with `downloadAttachment(record)`.

## Reviewer-Added Media

Do not use `localStorage` for reviewer screenshots, pasted images, recorded
audio, or uploaded media. The quota is too small for reliable binary feedback,
and base64 expands payloads by about one third.

For interactive review forms:

- keep text notes and ratings in a small text-first draft
- store media blobs in IndexedDB when available
- show a persistent warning when media is only held in memory
- provide a visible "Save feedback file" or backup action
- export attachment metadata with the returned JSON
- fall back to text-only feedback plus separately sent media when payloads are
  too large for email or clipboard return
