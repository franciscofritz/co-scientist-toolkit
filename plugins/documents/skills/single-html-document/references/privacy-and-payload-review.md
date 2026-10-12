# Privacy And Payload Review

Single HTML files look like ordinary documents, but they can contain whole source folders, Base64 attachments, images, transcripts, data exports, and hidden build metadata. Review them like a small website plus an archive.

## Payload Classes

| Class | Include in page? | Download? | Review focus |
| --- | --- | --- | --- |
| Narrative text | Yes | No | Accuracy, tone, confidential details |
| Local source notes | Yes, when needed for comprehension or provenance | No | Personal data, draft-only material, internal names |
| Search index | Yes | No | Hidden text snippets, names, source paths |
| Images and media | Yes, if licensed and needed | Sometimes | Redistribution rights, file size, embedded metadata |
| CSV/spreadsheets | Summarise in page | Yes, when reuse is expected | Personal data, row-level sensitivity |
| PDFs/slides/ZIPs | Summarise in page | Yes, when separate use is expected | Correct version, intended recipients |
| Build metadata | Usually no | No | Local paths, usernames, machine names |

## Pre-Distribution Checks

Pass only when all are true:

- The final `.html` passes strict audit.
- Required local text sources are rendered inside the page, not left as text downloads.
- Attachment downloads are intentional and named clearly.
- No API keys, session tokens, credentials, or private URLs are present.
- No unnecessary personal data is present in rendered text, source appendix, search index, or attachment payloads.
- No local filesystem paths are visible unless intentionally documented.
- No remote fonts, analytics, tracking pixels, or CDN scripts are present unless explicitly approved.
- Every embedded image or copied asset is allowed to be redistributed.
- File size is within the agreed distribution channel limits.
- The title/version/date make it clear which artifact is being shared.

## Practical Inspection Commands

Search visible and hidden text:

```bash
rg -n "api_key|token|secret|password|Bearer|client_secret|absolute path|local path" document.single.html
```

Audit dependencies:

```bash
node "${CLAUDE_SKILL_DIR}/scripts/audit-single-html.mjs" document.single.html --strict
```

Review attachment records:

```bash
rg -n "window.__ATTACHMENTS__|filename|mimeType|sha256" document.single.html
```

For large files, extract and inspect attachment manifests before distribution. The final review should include the generated HTML and any downloaded artifact produced from the embedded payloads.
