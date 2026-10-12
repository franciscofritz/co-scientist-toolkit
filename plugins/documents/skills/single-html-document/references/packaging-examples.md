# Packaging Examples

These examples are implementation patterns, not separate product modes. The principle is the same in all cases: make the website work first, then collapse it only at the packaging boundary.

## Direct Inline

Use for reports with modest media and no large binary attachments.

```html
<!doctype html>
<html>
<head>
  <style>/* bundled CSS */</style>
</head>
<body>
  <main><!-- rendered report --></main>
  <script>/* bundled runtime */</script>
</body>
</html>
```

Expected final dependencies: none.

Tradeoff: easiest to inspect and debug, but large images and long scripts make the HTML heavy quickly.

Audit:

```bash
node "${CLAUDE_SKILL_DIR}/scripts/audit-single-html.mjs" dist/document.html --strict
```

## Separated Client Script With Injected Data

Use for generated feedback workbooks and other interactive artifacts where the
source JavaScript should stay readable but the delivered file must remain
self-contained.

Source JavaScript:

```js
const REVIEW_PLAN = __PLAN_JSON__;

function mountWorkbook() {
  // Keep source comments here. The packager strips them from the distribution
  // copy before inlining the script.
}
```

Packager responsibilities:

- read the source JavaScript from its own file
- replace `__PLAN_JSON__` with serialized data
- strip comments from the distribution copy
- inline the resulting script into the HTML
- verify the packaged script parses

Regression checks should fail if the marker remains in the output, source-only
comments leak into the packaged script, or the generated HTML contains external
script dependencies.

## Embedded Manifest With Blob Downloads

Use when attachments need separate distribution, such as CSV, PDF, spreadsheet, slide deck, ZIP, or media files.

```html
<button type="button" data-attachment-id="usage-csv">Download CSV</button>
<script>
window.__ATTACHMENTS__ = [{
  id: "usage-csv",
  filename: "usage.csv",
  mimeType: "text/csv;charset=utf-8",
  encoding: "base64",
  payload: "d2Vlayx1c2FnZQo="
}];
</script>
<script>
function base64ToBytes(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-attachment-id]");
  if (!button) return;
  const record = window.__ATTACHMENTS__.find((item) => item.id === button.dataset.attachmentId);
  const url = URL.createObjectURL(new Blob([base64ToBytes(record.payload)], { type: record.mimeType }));
  const link = document.createElement("a");
  link.href = url;
  link.download = record.filename;
  link.click();
  URL.revokeObjectURL(url);
});
</script>
```

Expected final dependencies: none. The attachment is data inside the page until the user downloads it.

Tradeoff: Base64 adds roughly one third to the raw payload size. Use gzip+Base64 records for text-heavy attachments when the target browsers support decompression in your runtime.

## Compressed Bootstrap

Use for very large generated HTML where the readable shell is small but the report payload is large.

```html
<div id="app">Loading report...</div>
<script type="application/json" id="payload">
{"encoding":"gzip+base64","html":"...","css":"...","js":"..."}
</script>
<script>
// Read the payload, decompress with DecompressionStream where supported,
// then mount the generated app.
</script>
```

Expected final dependencies: none.

Tradeoff: smaller transfer and storage size, but slower startup, harder inspection, and more browser capability assumptions. Keep this as a deliberate large-report choice, not the default.

## Vite Single-File Build

For React/Vite projects, start from a normal app and add a dedicated package build:

```ts
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

export default defineConfig(({ mode }) => ({
  plugins: [react(), mode === "single" && viteSingleFile()].filter(Boolean),
  build: {
    assetsInlineLimit: mode === "single" ? Number.MAX_SAFE_INTEGER : 4096,
    cssCodeSplit: mode !== "single",
    rollupOptions: {
      output: {
        manualChunks: mode === "single" ? undefined : undefined,
      },
    },
  },
}));
```

Then:

```bash
vite build --mode single
node "${CLAUDE_SKILL_DIR}/scripts/audit-single-html.mjs" dist/index.html --strict
```

Failure modes to watch:

- leftover `/assets/...` references
- `modulepreload` links
- external font stylesheets
- `fetch("./content.json")` or `fetch("/data/...")`
- history-router links that break under `file://`
- text notes distributed only as downloads
