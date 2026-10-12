---
name: academic-pdf-to-mkd
description: "Extract academic PDFs into structured Markdown (body text, figures, tables, page thumbnails as separate artefacts) with automatic per-file engine selection (docling / pymupdf4llm / MinerU-math / poppler) and an OCR preflight. Use whenever the user wants to convert or extract a paper, preprint, or scanned PDF into Markdown, especially when figures, tables, or equations must survive. Triggers: 'extract this PDF to markdown', 'convert this paper to markdown', 'get the text and figures out of this PDF', 'OCR this scanned paper', 'this PDF has no text layer', 'copy-paste comes out garbled', 'make this PDF searchable for Zotero', 'split these two-up scanned spreads', or any hand-off needing fulltext.md before review (feeds paper-review). Handles math-heavy (MinerU), short born-digital (fast), and two-column (docling) papers, plus a Zotero branch producing a searchable OCR PDF from a scan. For arXiv papers prefer arxiv-fetcher (native .tex is cleaner). Prefer this over the generic pdf skill for research papers."
---

# Academic PDF to Markdown

Extracts academic PDFs into structured Markdown, with figures, tables, and page thumbnails as separate artefacts. The orchestrator runs an OCR preflight, picks the right engine per file, and produces a consistent output tree regardless of engine.

## Engines

| Engine | When chosen | Notes |
|---|---|---|
| **docling** *(default for most papers)* | Two-column papers, layout-heavy PDFs, fall-through case | MIT. MPS-accelerated. Best figures/tables. Writes a displayed equation it cannot read as `<!-- formula-not-decoded -->`; an auto run that finds one reruns the text with MinerU. |
| **fast** *(pymupdf4llm)* | Short (≤12 pp), dense, low-math, born-digital | AGPL. No model load — sub-second on small docs. |
| **math** *(MinerU)* | Math-symbol density ≥ 4% of word count | Apache-2.0 with usage thresholds. Strong on formulas. **~4.5 GB models, not bundled — first run downloads them (see below).** |
| **poppler** *(fallback)* | Explicit `--engine poppler` when no Python venv | GPL. Deterministic, no models, weak structure. |

Auto-detection rules live in `scripts/detect-engine.py` — math-symbol ratio (`∑∫∂∇...` + numbered-equation markers), page count, and words-per-page.

## Prerequisites

Python deps via `uv` (per `pyproject.toml`), installed once into the plugin's data folder, which
survives plugin updates (the plugin's own folder is replaced on each update):

```bash
UV_PROJECT_ENVIRONMENT="${CLAUDE_PLUGIN_DATA}/pdf2md-venv" uv sync --frozen --project "${CLAUDE_SKILL_DIR}"
```

This installs `docling`, `pymupdf4llm`, and `mineru[all]`. Python 3.11 to 3.13 is required, as the
pinned `torch` has no build for 3.14. `uv` uses an installed version or downloads one if needed,
so don't pass `--python`. The scripts use the environment named by `PDF2MD_VENV`, or otherwise
a `.venv/` beside the skill. A plain `uv sync` in the skill's folder creates that environment
when the skill is used outside a plugin. If the scripts report a missing module, run the command
above first.

System tools:

```bash
brew install poppler ocrmypdf ghostscript
```

`ocrmypdf` is required for the OCR preflight on scan-only PDFs. `ghostscript`
is optional but useful for compressing repaired Zotero PDFs; everything else
degrades gracefully.

### Model footprint (check before running the math engine)

`uv sync` installs the *code*, not the model weights. Disk footprint per engine:

- **docling** (default) — ~506 MB (`docling-models` + `docling-layout-heron`), kept cached.
- **fast** / **poppler** — no models.
- **math** (MinerU) — **~4.5 GB** (`opendatalab/PDF-Extract-Kit-1.0` + `MinerU2.5-Pro`), **not pre-cached**.

The math engine's models are **not bundled** to keep the cache small. `mineru-extract.sh`
checks the HF cache (`$HF_HOME` or `~/.cache/huggingface/hub`) first: if the `opendatalab`
models are absent it **refuses to run** rather than silently pulling ~4.5 GB. To proceed,
re-run with `MINERU_ALLOW_DOWNLOAD=1`; otherwise use `--engine docling` for non-math papers.
An auto run that chose docling also calls MinerU when docling leaves equations undecoded; without
the models, that run keeps docling's output and prints a warning.
Reclaim the space later with `rm -rf ~/.cache/huggingface/hub/models--opendatalab--*`.

## Quick start

```bash
PDF2MD_VENV="${CLAUDE_PLUGIN_DATA}/pdf2md-venv" "${CLAUDE_SKILL_DIR}/scripts/extract-pdf.sh" /path/to/paper.pdf
# or pin an engine
PDF2MD_VENV="${CLAUDE_PLUGIN_DATA}/pdf2md-venv" "${CLAUDE_SKILL_DIR}/scripts/extract-pdf.sh" /path/to/paper.pdf --engine docling
PDF2MD_VENV="${CLAUDE_PLUGIN_DATA}/pdf2md-venv" "${CLAUDE_SKILL_DIR}/scripts/extract-pdf.sh" /path/to/paper.pdf ~/out/paper-x --engine fast
```

Default output directory: `./output/<paper_id>/`.

### Zotero-ready OCR PDF

Use this branch when the deliverable should remain a searchable PDF for Zotero
rather than Markdown.

```bash
PDF2MD_VENV="${CLAUDE_PLUGIN_DATA}/pdf2md-venv" "${CLAUDE_SKILL_DIR}/scripts/ocr-pdf-for-zotero.sh" /path/to/chapter.pdf
PDF2MD_VENV="${CLAUDE_PLUGIN_DATA}/pdf2md-venv" "${CLAUDE_SKILL_DIR}/scripts/ocr-pdf-for-zotero.sh" /path/to/chapter.pdf ~/out/chapter-zotero.pdf --split-spreads
```

Use `--split-spreads` for scanned book chapters where one PDF page contains
two printed pages. This produces one printed page per PDF page and prevents text
selection from crossing facing pages. Use `--no-compress` if Ghostscript
compression damages a particular scan.

## Pipeline stages

```
Stage 0   ocr-preflight.sh         Detect scan-only PDFs (< 100 words in pdftotext)
                                   → ocrmypdf -l eng --deskew --rotate-pages
Stage 1   detect-engine.py         Choose docling | fast | math   (skip if --engine ≠ auto)
Stage 2   <engine>-extract.{py,sh} Produce fulltext.md + figures/ + tables/
Stage 2b  mineru-extract.sh        Auto-chosen docling left <!-- formula-not-decoded -->:
                                   MinerU's text and figures replace docling's
Stage 3   extract-pages.sh         pdftoppm thumbnails (skipped if engine emits them)
```

### Zotero PDF repair stages

```
Stage Z0  ocr-pdf-for-zotero.sh       Run OCRmyPDF with deskew, rotation, and low rotation threshold
Stage Z1  split-copyfriendly-ocr-pdf  Rebuild hidden text as whole-line invisible text
Stage Z2  --split-spreads optional    Split two-up scans into one printed page per PDF page
Stage Z3  Ghostscript optional        Compress the final PDF
Stage Z4  validation                  Word count, page count, raw text sample, preview PNGs
```

## Output structure

```text
{output_dir}/
├── {paper_id}-fulltext.md          # YAML frontmatter records engine used
├── pages/page-NNN.png              # Page thumbnails
├── figures/
│   ├── {paper_id}-figure-NN.png
│   └── {paper_id}-figure-NN.md     # Caption + TODO description
└── tables/
    ├── {paper_id}-table-NN.md      # Markdown rendering + caption
    └── {paper_id}-table-NN.csv     # Raw data (docling only)
```

Tables are emitted as separate CSVs only by docling. `fast` and `math` engines keep tables inline in the fulltext markdown — read the engine field in the fulltext frontmatter to know which. After a Stage 2b rerun the frontmatter says `engine: "mineru"` with a `rerun_from` line, the fulltext has MinerU's inline tables, and `tables/` and `pages/` are still docling's.

## Zotero-ready OCR PDF repair

This branch handles a different success criterion from Markdown extraction:
Zotero needs a PDF that is searchable, selectable, and logically paged.

### When to use

- Scan-only PDF: `pdftotext input.pdf - | wc -w` returns fewer than ~100 words.
- The user wants to attach the file to Zotero.
- Copy/paste from the OCR PDF shows character spacing such as `T h e r e i s`.
- Text selection crosses a two-page spread.
- The scanned PDF contains two printed pages per PDF page.

### OCR command

The wrapper uses this OCRmyPDF pattern:

```bash
ocrmypdf -l eng --deskew --rotate-pages --rotate-pages-threshold 1 \
  --output-type pdf input.pdf output-ocr.pdf
```

The lower rotation threshold is useful when visual inspection shows that pages
share one sideways orientation but OCRmyPDF leaves low-confidence pages
unrotated.

### Copy/paste failure modes

Do not treat OCR success as only "words exist." Validate three layers:

- **Recognition:** `pdftotext output.pdf - | wc -w` should return a plausible word count.
- **Text-layer geometry:** `pdftotext -raw -f 1 -l 1 output.pdf -` should not show spaced letters or merged words.
- **Page structure:** selection should not cross facing pages; scanned spreads should normally be split.

If copied text appears as spaced characters, the OCR recognition may be fine
but the hidden text layer may be bad. Rebuild the text layer as line-level
invisible text with `split-copyfriendly-ocr-pdf.py` rather than using tightly
positioned character or word fragments.

If copied text or selection crosses facing pages, split the two-up spread. Move
left-half OCR lines onto the left page and right-half OCR lines onto a new page
with the right-half coordinates shifted to the new origin. Skip blank final
halves.

Avoid horizontally squeezing invisible text to fit OCR boxes. It can make text
extractors merge words. Prefer normal word spacing and reduce font size to fit
long invisible lines inside their source line box.

### Validation commands

```bash
pdfinfo output.pdf | sed -n '1,40p'
pdftotext output.pdf - | wc -w
pdftotext -raw -f 1 -l 1 output.pdf - | sed -n '1,80p'
pdftoppm -png -f 1 -l 1 -r 100 output.pdf previews/page
```

Visually inspect representative first, middle, and final pages, especially after
rotation or spread splitting.

## Agent workflow

0. **Licence:** `license-check check <pdf> --write <output_dir>/license.json`. Exit code 3 means
   the paper may not be processed here (a subscription copy from any publisher, or a manuscript
   under review): stop, tell the user, and offer the open copy the card names. The licence-check
   hook refuses the extraction command in that case anyway. The `license.json` makes any later
   read of the output show the licence, and refuses it when the paper was refused.
1. **Run:** `PDF2MD_VENV="${CLAUDE_PLUGIN_DATA}/pdf2md-venv" "${CLAUDE_SKILL_DIR}/scripts/extract-pdf.sh" <pdf> [output_dir]`. Auto-detection picks the engine.
2. **Verify:** Read `{paper_id}-fulltext.md`. Confirm headings parsed correctly and the engine in frontmatter matches expectations. If the run warned that the MinerU rerun failed, the equations are still `<!-- formula-not-decoded -->`: fix the cause it printed (usually the model download, `MINERU_ALLOW_DOWNLOAD=1`) and re-run with `--engine math`.
3. **Override if needed:** Re-run with `--engine docling|fast|math|poppler` if auto picked wrong.
4. **Enhance figures (optional):** Each `figures/*.md` has a `TODO: Describe figure` placeholder. Use Vision to view the PNG and fill it in if the workflow needs it.
5. **Hand off:** If this is part of a `paper-review` workflow, move `{paper_id}-fulltext.md` into the review's working dir (e.g. `paper-analysis/{paper_id}/`).

### Agent workflow for Zotero PDFs

1. **Run:** `PDF2MD_VENV="${CLAUDE_PLUGIN_DATA}/pdf2md-venv" "${CLAUDE_SKILL_DIR}/scripts/ocr-pdf-for-zotero.sh" <pdf> [output_pdf]`.
2. **Split spreads when needed:** Add `--split-spreads` for two-up scanned book chapters.
3. **Verify copy text:** Check the sample lines printed by the wrapper and run `pdftotext -raw` on pages where the user saw bad copy/paste.
4. **Verify visuals:** Inspect preview PNGs for first and final pages; render middle pages if crop/gutter risk remains.
5. **Hand off:** Give the final PDF path, page count, and extractable word count. Prefer the split version for Zotero when spreads were present.

## Licence notes

- The skill code itself is permissive; engines have their own terms.
- **Docling** (MIT) — safe to embed.
- **pymupdf4llm** (AGPL-3.0) — fine for local use; networked redistribution triggers source-disclosure.
- **MinerU** (Apache-2.0 + thresholds) — commercial licence required above 100 M MAU or USD 20 M monthly revenue; attribution required for online services.
- **Poppler** (GPL) — invoked as a separate binary, not linked.
