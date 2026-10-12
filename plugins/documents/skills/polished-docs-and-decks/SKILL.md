---
name: polished-docs-and-decks
description: "Build polished, themed deliverables: PowerPoint slide decks (.pptx via python-pptx + matplotlib) and typeset PDFs from Markdown (pandoc + xelatex), verified by rendering to images with headless LibreOffice. Use whenever the user wants a slide deck, talk, pitch, or lecture as a .pptx, or a nicely typeset PDF / handout / explainer / report / one-pager from Markdown or notes, or asks to render / preview / proof / check / convert a .pptx or .docx, even if they don't name the tool. Bundles a Unicode-math LaTeX preamble, a python-pptx helper module, a figure-overlap pre-check and the LibreOffice render-to-verify step. Boundaries: an animated HTML deck opened in a browser is a different job; a self-contained HTML document or dashboard is single-html-document. Prefer this over hand-rolling pptx/LaTeX from scratch."
---

# Polished docs and decks

Create either output type, then use the same verification step.

Assets live next to this file in `${CLAUDE_SKILL_DIR}/assets/`:
- `pdf_header.tex`: the xelatex preamble for the Markdown→PDF pipeline.
- `pptx_helpers.py`: python-pptx palette + slide helpers + the overlap pre-check.
- `figures.py`: matplotlib patterns for equations (mathtext) and node/arrow diagrams.

Copy the assets into a working folder and work there, because the plugin's own folder is
replaced on each update:

```bash
mkdir -p /tmp/<job> && cp "${CLAUDE_SKILL_DIR}"/assets/* /tmp/<job>/
```

`import pptx_helpers` needs the file on `sys.path`, so run your build script from that folder.
`figures.py` writes its images to `fig/` in the folder it is run from.

Requirements: Python 3 with `python-pptx` and `matplotlib` (Pipeline B); `pandoc` and a XeLaTeX
distribution (Pipeline A); LibreOffice and `pdftoppm` from poppler (Pipeline C). A full MacTeX
or TeX Live install has every package `pdf_header.tex` loads. BasicTeX lacks some of them; add
them with `sudo tlmgr install sectsty mdframed enumitem newunicodechar zref needspace soul`.

## When to use which pipeline

**Not this skill (hand off):** an animated HTML slide deck opened in a browser → an HTML slides skill, if you have one; a self-contained / interactive **HTML** document or dashboard → `single-html-document`. Reading or editing an **existing** `.pptx`/`.docx` as raw OOXML (extract text, tweak one file) → a `pptx` / `docx` skill, if you have them. Manipulating an **existing PDF** (merge/split/forms) → a `pdf` skill, if you have one. Use *this* skill to **author and render** new themed decks or typeset PDFs.

- **Slide deck / talk / presentation** → Pipeline B, then ALWAYS Pipeline C to verify.
- **Typeset PDF from Markdown** (explainer, handout, report) → Pipeline A.
- **"render / preview / check this .pptx or .docx"** → Pipeline C on its own.

---

## Pipeline A: Markdown → typeset PDF (pandoc + xelatex)

The one non-obvious thing: **do NOT** run `pandoc file.md -o out.pdf` or `pandoc -s … -o out.tex`.
Pandoc's standalone xelatex template loads `fontspec`, which silently **breaks `newunicodechar`
maps**; your `∑ ∫ 𝓘` etc. then error with `Missing $ inserted`. Instead emit a **body
fragment** and wrap it in our own preamble:

```bash
# 1. clean the markdown: move the H1 title to YAML metadata or set it via \title in main.tex.
# 2. body fragment only (NO -s, NO template). If step 1 took the title from an H1 and the
#    sections are ## headings, promote them one level, or they number 0.1, 0.2:
pandoc cleaned.md --shift-heading-level-by=-1 -t latex -o body.tex
#    (sections already # headings: leave out --shift-heading-level-by)
# 3. build main.tex around it:
cat > main.tex <<'EOF'
\documentclass[11pt]{article}
\input{pdf_header.tex}
\title{\textbf{My Title}\\[0.3em]\large My subtitle}
\author{Author}\date{June 2026}
\begin{document}\maketitle\tableofcontents\clearpage
\input{body.tex}
\end{document}
EOF
# 4. compile twice (TOC needs two passes):
xelatex -interaction=nonstopmode main.tex >/dev/null && xelatex -interaction=nonstopmode main.tex
grep -cE '^! ' main.log             # error lines: expect 0
grep 'Missing character' main.log  # a glyph the font or header cannot draw: expect no output
```

`pdf_header.tex` already handles the things that otherwise fail:
- **Unicode math → LaTeX** via `\newunicodechar` (Greek letters, ∂ ∇ ∑ ∏ ∫ ≤ ≥ ≠ ≈ ± × ∞ →, ⟨⟩ 𝓘, sub/superscripts …).
  If a new glyph appears in a document, add one `\newunicodechar{X}{\ensuremath{...}}` line.
  Find all non-ASCII characters with: `python3 -c "import sys;[print(hex(ord(c)),c) for c in set(open('f.md').read()) if ord(c)>127]"`.
- **`amsmath`**: pandoc passes real math (`$…$`, `\[ \]`) through verbatim, so `\text{}` and
  `\operatorname{}` need amsmath or you get `Undefined control sequence`.
- **`calc` + `\providecommand{\real}[1]{#1}`**: pandoc width-tables emit
  `p{(\linewidth-…)*\real{0.33}}`; without these you get `Missing number / Illegal unit / \real undefined`.
- **Images, strikethrough and code**: `graphicx` with pandoc's `\pandocbounded` (large images are
  scaled to the page), `soul` for `~~strikethrough~~`, and pandoc's syntax-highlighting
  definitions, so fenced code keeps its colours.
- Blockquotes (`>`) are restyled as shaded callout boxes; headings are coloured (sectsty).
  So: put displayed formulas / key statements in `>` blockquotes to box them.

Render the result to confirm (it's a PDF, so just Read its pages as images).

---

## Pipeline B: themed PowerPoint deck (python-pptx + matplotlib)

Author a build script that imports `pptx_helpers` (`import pptx_helpers as D`) and lays out
slides; render the figures with `figures.py` first. See the docstrings in both assets for the
full API. The shape of a good deck:

- **16:9**, one idea per slide. **Pace ≈ 1.5–2 min/slide** → a 30-min talk is ~20 slides;
  give the centrepiece idea 2 slides.
- Title slide (`D.title_slide`), section `D.divider`s, content slides
  (`D.header` + `D.body` + `D.pic`), a summary, a closing.
- **Put a timed speaker script in EVERY slide's `D.notes(s, "[~2 min · ~16:30] …")`.**
  The notes are what turn slides into a talk and let it actually hit a target length.
- **Equations and diagrams are IMAGES**, rendered by `figures.py` (matplotlib mathtext for
  formulas; boxes/arrows for diagrams). Do NOT type ∑ ∫ 𝓘 or fancy subscripts (`𝓘ₘₐₓ`,
  `dᵥ`) into slide text; Calibri lacks them and they render as tofu. Use plain words
  ("mutual information", "d_V") in text, and the rendered symbol in the figure.
- `D.add_footers(label="…")` then `D.save(path)` at the end.

**Overlap pre-check (do this; it is the #1 silent bug).** python-pptx text boxes don't clip,
and a figure placed by `width=` takes a height set by the image's TRUE (tight-cropped) aspect,
which is rarely what you guessed from `figsize`. So a figure routinely overruns the bullets
below it. After placing, verify with the helper:

```python
assert D.overlaps_ok("fig/loop.png", top_in=1.55, width_in=8.4, next_text_top_in=5.3)
```

Use PNG files for figures. `overlaps_ok` reads their sizes from the PNG header.

Fix by shrinking `width_in`, lowering the figure, or pushing the text `t=` down, then re-check.
Then **always render and eyeball (Pipeline C)** before delivering; the math gets you close, the
render confirms it.

---

## Pipeline C: render any .pptx / .docx to verify (headless LibreOffice)

This is the only way to truly see a generated Office file. **Always do it before delivering a
deck**, and use it whenever the user asks to preview/proof/check one.

```bash
SOFFICE="$(command -v soffice || echo "$HOME/Applications/LibreOffice.app/Contents/MacOS/soffice")"
"$SOFFICE" --headless --convert-to pdf --outdir /tmp/render "/path/to/Deck.pptx"
# then Read /tmp/render/Deck.pdf pages as images (the Read tool renders PDF pages)
```

LibreOffice can lag if an instance is open; add `-env:UserInstallation=file:///tmp/lo_profile`
if a convert hangs. For per-slide PNGs, convert to PDF then rasterise (`pdftoppm -png`), or read
PDF pages directly. Reading the pages catches font substitution, text overflow, and odd figure
placement that layout math cannot.

**One-time install (no admin password):**
```bash
brew install --cask --appdir="$HOME/Applications" libreoffice
```

---

## Gotchas
- Pandoc's `-s`/PDF path + fontspec **breaks `newunicodechar`** → body-fragment + own preamble.
- Pandoc math passthrough needs **amsmath**; pandoc width-tables need **calc + `\real`**.
- PowerPoint fonts **lack math glyphs** → render equations/symbols as PNGs, keep slide TEXT plain ASCII-ish.
- python-pptx **doesn't clip text** and image height follows the **tight-cropped** aspect → run `overlaps_ok()`.
- A deck without **speaker notes** can't be timed → script every slide; ~1.5–2 min each.
- **Keep slide titles to one line** (~≤48 chars). Longer titles wrap into the accent bar, or
  run *under* the top-right tag chip: silent collisions the overlap math won't catch.
- Never trust a generated Office file unseen → **render with LibreOffice and look** (this is
  how the title-collision class of bug gets caught; reading 3–4 representative pages is enough).
