---
name: course-to-pdf
description: "Bind a static HTML course or documentation site into one textbook-typeset PDF, retypesetting the screen CSS for print. Use whenever someone wants a course, handbook, lesson notes, or docs site as a single printable PDF or book, or asks why an HTML-to-PDF export came out enormous. Triggers include: 'turn the course into a PDF', 'make a single PDF of the lessons', 'can I get this as a book', 'print the whole site', 'the PDF is 300 pages', 'export the docs as PDF'."
---

# Course site to textbook PDF

Bind every lesson page of a static HTML site into one PDF that reads like a book rather
than a printed website. The hard part is not the binding, it is that site CSS is written
for screen reading and wastes roughly two thirds of every page.

## Run it

```bash
python3 "${CLAUDE_SKILL_DIR}/course_pdf.py" SITE_DIR \
    --title "Course name" --subtitle "Lesson notes" --out book.pdf
```

It auto-detects the content container and the stylesheet, takes page order from the site's
own `index.html`, and prints with headless Chrome. Options for when detection is wrong:
`--pattern` (which hrefs are lessons), `--content` (container class), `--css`, `--strip`
(extra classes to drop), `--keep` (default-stripped classes to keep), `--min-words` (skip stub
sections, default 40), `--print-css` (your own copy of the textbook stylesheet), `--no-typeset`
(to see what the site CSS does unaided).

Requirements: Python 3 (the script uses only the standard library) and Chrome or Chromium, found
automatically on macOS and Linux or named in the `CHROME` environment variable. The checks below
use `pdftoppm` and `pdftotext` from poppler.

Chrome is the renderer on purpose. Course sites contain client-side maths and inline SVG, both
of which a pandoc or LaTeX route mangles.

**Maths.** The script uses the site's own maths engine. It copies the source page's KaTeX
tags and inline config, so the site's custom macros
render. Without KaTeX, it adds MathJax 3.2.2 from cdn.jsdelivr.net only when the bound pages
contain `\(...\)` or `\[...\]` maths. A site with no maths makes no MathJax request. The
injected MathJax reads only those two delimiters, not `$...$`, and does not copy the site's own
MathJax setup. Check the run line for the engine used. If it says `mathjax 3.2.2 (injected)`,
inspect a page with equations. If Chrome could not fetch MathJax, the script prints a warning
and the PDF shows raw LaTeX.

## The procedure

**1. Point it at the released site, not the source repo.** A dev tree usually contains every future
session, so the book can have more sections than the released course. Check the section count
against what you expect before anything else.

**2. Run it once with no options** and read the lines it prints: which container it
detected, whether it found CSS, which maths engine it will use, and which sections it
skipped as too short. If it says `css NONE`, the output will be unstyled and nothing else
matters yet.

Courses under construction publish placeholder pages for unwritten weeks. The script skips
pages below `--min-words` and names them in the output. Without that report, a skipped section
looks exactly like one that was never there.

**3. Read the words-per-page number. That is the whole diagnostic.**

| words/page | meaning |
|---|---|
| under 380 | site CSS still winning; go to step 4 |
| 420 to 550 | textbook density, correct |
| over 700 | impossible. Content is being dropped or overlapping. Go to step 5 |

The 420 to 550 words-per-page band comes from `print.css` at 10 pt on A4. Short books have a
lower average, as the title and contents pages count but contain few words. A correct
three-lesson book averages well under 380 and still gets the `DENSITY LOW` line. Inspect the
pages before changing anything.

**4. If density is low, override in this order.** Each buys back more than the next, and
`print.css` next to this script already does all of them. If a site fights back, copy it, extend
the copy and pass it with `--print-css`: the plugin's own folder is replaced on each update.

1. `line-height` on body. Screen CSS runs 1.6 to 1.8; books run 1.3 to 1.4. Biggest single win.
2. Container padding. A `.content { padding: 42px 48px }` is paid on every page of the book.
3. Heading scale and the margins *above* headings, which are usually larger than the text.
4. Callout box padding and margins, typically 18 to 28px on screen against 7 to 9pt in print.
5. Forced page breaks. Break at section boundaries. Breaking at every sub-page leaves a
   part-empty page after each one.
6. Responsive grids. `repeat(auto-fit, minmax(240px, 1fr))` collapses to one full-width
   column in print, so each card eats a band. Force two columns.

**5. Render pages and look at them. Always.** Word counts and page counts cannot see a broken
layout. `pdftoppm -png -r 80 -f N -l N book.pdf out` then read the image. Check a title page,
a contents page, a dense body page, and one page carrying a figure.

## Failure modes that look like success

**Fix container-scoped CSS in print.css, not by restoring the container.** Site rules are routinely
scoped to the content class, so removing the wrapper disables rules such as the spacing between
a heading number and its text. Wrapping each fragment in a div with that class also restores the
container's whole screen box. Neutralising that box property by property fails: descendant rules
restore screen typography and increase the book's length. Write a rule in `print.css` based on
structure, not a site's class names, such as `h2 > span:first-child { margin-right:.5em }`.

**The container heuristic.** Extracting from the container to the last `</div>` in the file
includes footers on one layout and truncates content on another. Both errors produce a
plausible-looking PDF. The script matches the container's own closing tag by depth. If you adapt
it, keep that.

**An impossible density.** A book reporting 2,000 words per page is losing content. Check the
ratio of words to pages, not either count alone.

**One malformed page breaking every page after it.** Fragments are concatenated, so one
unclosed `<div>` puts the rest of the book inside a narrow container and reduces the words per
page part-way through. The script closes any tags a page leaves open before concatenating. To
check for it, count the words on each page of the `pdftotext` output and look for a count that
drops sharply and stays low.

    python3 - <<'EOF'
    import subprocess
    t = subprocess.run(['pdftotext','book.pdf','-'],capture_output=True,text=True).stdout
    c = [len(p.split()) for p in t.split('\f')]
    for lo in range(0, len(c), 200):
        seg = c[lo:lo+200]; print(lo+1, sum(seg)//len(seg))
    EOF

## Site layouts

On the sites tried, the script produced 420 to 550 words per page with no options beyond a
title. Books consisting mostly of derivations have a higher average, as display equations use
less space than prose. The script handles linked and inline CSS, URL-encoded hrefs and numbered
folders such as `week-1/`. Use `--pattern` for sites whose lessons are elsewhere, such as
`lessons/intro.html`.

## What to cut when it is still too long

Typography is spent by this point; the remaining levers are content. Reading lists,
class-discussion questions and lab Explore sections are usually not textbook material: drop
them with `--strip` and the class names the site gives them. Below about 9.5pt body text it
stops being comfortable on paper, so cut content rather than shrink type.
