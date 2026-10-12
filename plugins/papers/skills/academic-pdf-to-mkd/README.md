# Academic PDF to Markdown

Extract structured text, figures, and tables from academic PDFs into clean Markdown. Auto-picks the best engine per file (Docling / pymupdf4llm / MinerU) and OCRs scan-only inputs first.

## Quick start

With the papers plugin installed, ask Claude to extract a PDF. The skill runs the commands below. To run them yourself, use `${CLAUDE_SKILL_DIR}` for the skill's folder in the installed plugin and `${CLAUDE_PLUGIN_DATA}` for the plugin's data folder, set up under Requirements.

```bash
PDF2MD_VENV="${CLAUDE_PLUGIN_DATA}/pdf2md-venv" "${CLAUDE_SKILL_DIR}/scripts/extract-pdf.sh" path/to/paper.pdf [output_dir]
PDF2MD_VENV="${CLAUDE_PLUGIN_DATA}/pdf2md-venv" "${CLAUDE_SKILL_DIR}/scripts/extract-pdf.sh" path/to/paper.pdf --engine docling
```

## Requirements

```bash
brew install poppler ocrmypdf ghostscript   # ghostscript is optional
```

The Python packages are installed once with `uv` into the plugin's data folder. The exact command is in the Prerequisites section of `SKILL.md`. `PDF2MD_VENV` tells the scripts which environment to use.

## Pipeline

| Stage | Script | Purpose |
|---|---|---|
| 0 | `ocr-preflight.sh` | `ocrmypdf -l eng --deskew --rotate-pages` if text layer is sparse |
| 1 | `detect-engine.py` | Pick `docling` / `fast` / `math` from page count + math-symbol density |
| 2 | `<engine>-extract.*` | Produce fulltext + figures + (engine-dependent) tables |
| 2b | `mineru-extract.sh` | If auto-chosen docling left equations as `<!-- formula-not-decoded -->`, take the text and figures from MinerU |
| 3 | `extract-pages.sh` | Page PNG thumbnails via `pdftoppm` |

## Engines

- **docling** — default. MIT. Layout model, MPS-accelerated, best tables/figures.
- **fast** — `pymupdf4llm`. AGPL. No model load; sub-second on small clean docs.
- **math** — `MinerU`. Apache-2.0 with thresholds. Strongest formula handling.
- **poppler** — fallback. GPL. No models, weak structure recovery.

## Output

```
output/<paper_id>/
├── <paper_id>-fulltext.md      # engine recorded in YAML frontmatter
├── pages/page-NNN.png
├── figures/<paper_id>-figure-NN.png + .md
└── tables/<paper_id>-table-NN.md + .csv   # docling only
```

See `SKILL.md` for full documentation, `examples/` for output templates.
