---
name: arxiv-fetcher
description: "Fetch LaTeX source and PDF from arXiv papers. Use this skill whenever the user mentions an arXiv paper, arXiv ID, arXiv URL, or asks to download/fetch/pull/get a paper from arXiv. Also triggers when the user wants to read, review, or analyse an arXiv paper and you need to retrieve it first. Handles all arXiv ID formats (2301.12345, 2301.12345v2, hep-th/0601234, arxiv.org URLs). Downloads source .tex files and PDF. Works as a standalone tool or as a prerequisite for the paper-review skill."
---

# arXiv Fetcher

Downloads LaTeX source files and PDFs from arXiv given an arXiv ID or URL.

## When to use

- User provides an arXiv ID or URL and wants to work with the paper
- The paper-review skill needs source files for a cited paper
- User asks to "pull", "fetch", "download", or "get" a paper from arXiv
- Any workflow where you need the .tex source of an arXiv paper

## Quick start

Run the fetch script:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/fetch_arxiv.py" <arxiv_id_or_url> [--output-dir <dir>]
```

The script handles:
- Parsing any arXiv ID format or URL
- Downloading the source tarball from `https://arxiv.org/src/<id>`
- Extracting .tex files (handles tar.gz, gzip-only, and plain tex)
- Downloading the compiled PDF from `https://arxiv.org/pdf/<id>`
- Identifying the main .tex file (the one with `\documentclass`)
- Extracting metadata (title, authors, abstract) from the abstract page

Output is written to `<output-dir>/<arxiv_id>/` with structure:
```
2301.12345/
├── source/          # all extracted source files
│   ├── main.tex     # (or whatever the files are named)
│   ├── appendix.tex
│   ├── figures/
│   └── ...
├── paper.pdf        # compiled PDF from arXiv
├── metadata.json    # arxiv_id, title, authors, abstract, primary_category, abs_url, pdf_url, src_url
├── manifest.json    # arxiv_id, source_available, main_tex, pdf_path, all_source_files
└── license.json     # what the paper's licence allows, written by the papers plugin's license-check tool
```

`license.json` records the paper's licence, a verdict and a one-line rights statement. The licence-check tool reads this record later and shows what the licence allows when a file in this folder is read. The record is written only when the papers plugin's `tools/license-check` is present. A failed check does not stop the fetch.

## Accepted input formats

All of these work:

| Input | Parsed ID |
|-------|-----------|
| `2301.12345` | `2301.12345` |
| `2301.12345v2` | `2301.12345v2` |
| `hep-th/0601234` | `hep-th/0601234` |
| `https://arxiv.org/abs/2301.12345` | `2301.12345` |
| `https://arxiv.org/pdf/2301.12345` | `2301.12345` |
| `https://arxiv.org/src/2301.12345` | `2301.12345` |
| `http://arxiv.org/abs/2301.12345v2` | `2301.12345v2` |
| `arxiv.org/abs/2301.12345` | `2301.12345` |
| `arXiv:2301.12345` | `2301.12345` |

## Fetching multiple papers

To fetch several papers (e.g., all references from a bibliography):

```bash
# From a list of IDs
for id in 2301.12345 2302.67890 hep-th/0601234; do
    python3 "${CLAUDE_SKILL_DIR}/scripts/fetch_arxiv.py" "$id" --output-dir ./papers/
done
```

## Extracting arXiv IDs from a .bib or .tex file

To fetch every arXiv paper cited in a bibliography, pass the file with `--from-file`. The script extracts new- and old-style IDs from arXiv: identifiers and arxiv.org links, then fetches each paper:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/fetch_arxiv.py" --from-file refs.bib --output-dir ./papers/
```

## Integration with paper-review skill

When the paper-review skill's positioning agent needs to retrieve cited papers:

1. Extract arXiv IDs from the paper's bibliography
2. Fetch each paper using this skill
3. Read the main .tex file (or at minimum the abstract + intro + results from metadata/source)
4. Pass the content to the positioning agent for analysis

The `metadata.json` provides a quick summary without needing to parse the full .tex.

## Error handling

The script handles common failure modes:
- **Source not available**: Some papers don't have source on arXiv (submission-only PDF). The script still downloads the PDF and metadata, and sets `"source_available": false` in manifest.json.
- **Non-tar source**: Some older papers have a single .tex file gzipped (not tarred). The script detects and handles this.
- **Plain TeX source**: the script does not recognise a single gzipped file containing neither `\document` nor `\begin` as source (for example a harvmac paper such as hep-th/9711200). It reports "Source not available or unrecognised format" and still downloads the PDF. If the TeX is needed, fetch the raw file from `https://arxiv.org/src/<id>`.
- **Rate limiting**: arXiv rate-limits aggressive scraping. The script includes a configurable delay between requests (default 3 seconds). If fetching many papers, increase this.
- **Network errors**: Retries up to 3 times with exponential backoff.

## Important notes

- **Be respectful of arXiv's servers.** Don't fetch hundreds of papers in rapid succession. The default 3-second delay between requests is the minimum; increase it for bulk fetches.
- **arXiv source is not always LaTeX.** Occasionally papers are submitted as PDF-only, Word documents converted to PDF, or other formats. The script detects this and reports it in manifest.json.
- **Version pinning**: If you need a specific version (e.g., v1 vs v2), include the version suffix in the ID. Without it, arXiv returns the latest version.
