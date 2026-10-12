# Single-File HTML Architecture

## Core Position

Treat the single-file deliverable as the last build artifact, not the working project structure.

Recommended pipeline:

1. Author content in Markdown/YAML and sidecar data files.
2. Compile content into generated JSON or TypeScript.
3. Build a normal website with separate JS, CSS, and media.
4. Package the website into one HTML deliverable.
5. Verify the packaged file under `file://`.

This matches the strongest local precedents on this machine:

- `PPT2HandoutSkill`: normal React site first, media processing second.
- `agents_session/scripts/build-content.ts`: Markdown/YAML compiled into generated data before rendering.

## Recommended Stack

For new projects, default to:

- Vite
- React
- TypeScript
- Static content compiler using `gray-matter` + `fast-glob`

Reasoning:

- Vite is already the preferred stack on this machine.
- React is a good fit for rich navigation, search, media views, and layout variants.
- TypeScript makes the content contract explicit.
- Compiling content first keeps the runtime simple and `file://` safe.

## Recommended Directory Layout

```text
project/
├── content/
│   ├── report.yml
│   ├── pages/
│   │   ├── 01-executive-summary.md
│   │   ├── 02-findings.md
│   │   └── 03-appendix.md
│   ├── attachments.yml
│   ├── figures.yml
│   └── theme.yml
├── media/
│   ├── images/
│   ├── attachments/
│   └── video/
├── scripts/
│   ├── build-content.ts
│   └── build-search-index.ts
├── src/
│   ├── data/
│   │   └── generated/
│   ├── components/
│   ├── pages/
│   └── styles/
├── vite.config.ts
└── package.json
```

Do not fetch raw Markdown or YAML from the browser in the final packaged file. Compile it ahead of time.

## Packaging Modes

### 1. Direct Inline

Use when:

- the site is mostly narrative content
- images are moderate in number and size
- there are few or no downloadable binary attachments
- the target file should stay comfortably below the user's 10-30 MB preference

Implementation pattern:

- build a standard site
- inline JS and CSS
- inline imported assets
- avoid `public/` for anything that must be inlined

Good first pass:

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';

export default defineConfig({
  base: './',
  plugins: [react(), viteSingleFile({ removeViteModuleLoader: true })],
  build: {
    cssCodeSplit: false,
  },
});
```

Use this as the default path unless the site clearly needs a heavier delivery model.

### 2. Blob-Backed Payload

Use when:

- the site contains larger binaries
- the deliverable must expose downloadable attachments
- the site includes media that should not become giant literal `data:` attributes in the DOM
- the file may grow into the 20-100 MB range

Implementation pattern:

- embed attachment records in a JSON or TS manifest
- store payloads as Base64 or gzip+Base64
- decode only on demand
- create `Blob` objects in the browser
- generate temporary `blob:` URLs for downloads or media playback

Reasoning:

- `data:` URLs are fine for many inline images
- `Blob` URLs are a better fit for large resources and download flows
- lazy decode avoids inflating every binary into live DOM attributes on initial load

### 3. Compressed Bootstrap

Use when:

- the final file is getting too large in raw inline form
- the target browser is modern
- the user cares more about transport size than view-source readability

Implementation pattern:

- keep a small HTML bootstrap
- embed a compressed payload block
- decompress it on startup with `DecompressionStream`
- hydrate the app from the decompressed JSON/assets payload

Reasoning:

- Base64 costs roughly 33% overhead on raw binary
- gzip can claw back a meaningful part of that for JSON, HTML, SVG, and some text-heavy assets
- this is a strong option for research reports with many tables, appendices, and attachments

## Offline-Safe Rules

The final packaged file should satisfy all of these:

- no runtime fetches for local assets
- no root-absolute asset references such as `/assets/...`
- no history-based SPA routing assumptions
- no reliance on cookies or server headers
- no external fonts or CDNs
- no leftover chunk files or modulepreload links
- no unresolved `public/` assets

Prefer:

- anchor links
- one-page layouts
- hash routing
- generated search indexes
- embedded icons and theme tokens

## Attachment Pattern

Generate a manifest before the final build:

```bash
node "${CLAUDE_SKILL_DIR}/scripts/make-attachment-manifest.mjs" \
  --output src/data/generated/attachments.generated.ts \
  --root media/attachments \
  --gzip \
  media/attachments
```

Recommended attachment record shape:

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

Runtime pattern:

```ts
async function materializeAttachment(record: AttachmentRecord): Promise<Blob> {
  const bytes = Uint8Array.from(atob(record.payload), (char) => char.charCodeAt(0));

  if (record.encoding === 'gzip+base64') {
    const compressed = new Blob([bytes], { type: 'application/gzip' });
    const stream = compressed.stream().pipeThrough(new DecompressionStream('gzip'));
    return await new Response(stream).blob();
  }

  return new Blob([bytes], { type: record.mimeType });
}

async function downloadAttachment(record: AttachmentRecord): Promise<void> {
  const blob = await materializeAttachment(record);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = record.fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}
```

Do not pre-render huge attachment payloads as `href="data:..."` values for download buttons.

## Delivery Format

Emit `.html`. The deliverable is an ordinary HTML file that can be opened by a modern browser from disk.

## Use Capture Tools Carefully

Use tools like SingleFile only for:

- capturing an already-built site
- comparing how a complex third-party page behaves when collapsed
- archival snapshots

Do not use them as the primary authoring architecture for structured reports. They are a packaging or capture aid, not the content model.

## Sources

The architectural choices above are grounded in the following references. Read these if you need to defend a packaging decision or extend it for a new context.

### Data and Blob URLs

- [MDN: `data:` URLs](https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Schemes/data) — embedding inline content; opaque-origin behaviour; top-level navigation is blocked.
- [RFC 2397](https://www.ietf.org/rfc/rfc2397.txt) — original framing of `data:` as best for small inline items.
- [RFC 4648: Base64 encoding](https://datatracker.ietf.org/doc/html/rfc4648) — Base64 grows raw binary by ~33% before HTML overhead.
- [MDN: `blob:` URLs](https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Schemes/blob) — better runtime representation for larger embedded resources.
- [MDN: `HTMLAnchorElement.download`](https://developer.mozilla.org/en-US/docs/Web/API/HTMLAnchorElement/download) — pair with `URL.createObjectURL()` for export flows.

### `file://` and module loading

- [MDN: Origin glossary](https://developer.mozilla.org/en-US/docs/Glossary/Origin) — browsers treat `file:` URLs as opaque origins.
- [MDN: JavaScript modules guide](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules) — external module fetching from `file://` is the risky part; inline modules are fine.

### Build tooling

- [Vite build guide](https://vite.dev/guide/build) and [Vite build options](https://main.vite.dev/config/build-options) — `base: "./"` for relative output paths; `assetsInlineLimit` for Base64 inlining.
- [`vite-plugin-singlefile`](https://github.com/richardtallent/vite-plugin-singlefile) — direct-inline packaging plugin; documented caveats around `public/` assets, SVG handling, and history-based routing.

### Compression

- [MDN: Compression Streams API](https://developer.mozilla.org/en-US/docs/Web/API/Compression_Streams_API) — gzip/deflate compression and decompression baseline available in modern browsers, including in Web Workers.

### Capture tools and bundle formats

- [SingleFile](https://github.com/gildas-lormeau/SingleFile) and [SingleFile FAQ](https://github.com/gildas-lormeau/SingleFile/blob/master/faq.md) — capture tool; interactive elements may fail unless scripts are preserved.
- [Chrome Developers: Web Bundles](https://developer.chrome.com/docs/web-platform/web-bundles/) — experimental implementation of navigation to Web Bundles was removed in February 2023; not a default delivery target.
