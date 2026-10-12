#!/usr/bin/env python3
"""Bind a static HTML course site into one textbook-typeset PDF.

    python3 course_pdf.py SITE_DIR [options]

    --index FILE       page-order source, relative to SITE_DIR (default index.html)
    --pattern REGEX    which hrefs are lesson pages (default: a path segment ending in
                       session, lesson, week, chapter, module, unit, part or topic, plus an
                       optional number, such as session-03/ or week1/)
    --content CLASS    class of the body container (default: auto-detect)
    --strip CLASS,...  extra classes to drop, comma separated
    --keep CLASS,...   classes NOT to strip even if in the default strip list
    --css FILE         site stylesheet (default: the first page's linked or inline CSS)
    --min-words N      skip sections shorter than N words (default 40; 0 keeps everything)
    --title / --subtitle
    --out FILE         output pdf
    --density          accepted for compatibility; has no effect, density is always reported
    --no-typeset       skip the textbook overrides (debug: shows what the site CSS does)
    --print-css FILE   textbook stylesheet to use instead of print.css next to this script

Chrome does the printing: these sites usually carry MathJax and inline SVG that a
LaTeX route mangles. The textbook stylesheet is print.css next to this script. Set the
CHROME environment variable to the browser's path if it is not found automatically.
"""
import argparse, html as H, os, pathlib, re, shutil, subprocess, sys
from urllib.parse import unquote
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent

CHROME_CANDIDATES = [
    os.environ.get("CHROME", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome") or "", shutil.which("chromium") or "",
    shutil.which("chromium-browser") or "",
]
DEFAULT_STRIP = ["resource-placeholder", "ai-notice", "page-nav", "back-nav",
                 "site-nav", "breadcrumb", "top-nav", "skip-link", "footer"]

def find_chrome():
    for c in CHROME_CANDIDATES:
        if c and pathlib.Path(c).exists(): return c
    sys.exit("No Chrome/Chromium found. Install one, or pass its path in CHROME env.")

BLOCK = ("div","section","article","aside","figure","ul","ol","li","p","table","tbody","tr","td","th","blockquote","pre","header","footer","nav","span","em","strong")

def balance(frag):
    """Close any tag the page left open.

    Fragments are concatenated, so one malformed page otherwise swallows every
    page after it. Attested: a 102-page site rendered correctly for 200 pages
    and then collapsed to 45 words/page for 1,600 more, from a single unclosed div.
    """
    stack = []
    for m in re.finditer(r'<(/?)(\w+)([^>]*)>', frag):
        closing, tag, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if tag not in BLOCK or attrs.rstrip().endswith("/"): continue
        if closing:
            if tag in stack:
                while stack and stack.pop() != tag: pass
        else:
            stack.append(tag)
    return frag + "".join(f"</{t}>" for t in reversed(stack))

def class_start(cls):
    """Opening tag whose class attribute (either quote style) has `cls` as a whole token."""
    return re.compile(rf'<(\w+)[^>]*\sclass=(["\'])(?:[^"\']*\s)?{re.escape(cls)}(?:\s[^"\']*)?\2[^>]*>')

def extract(doc, cls):
    """The container's own contents, found by matching its closing tag at depth.

    The naive version (slice to the last </div>) silently over-grabs footers on
    one layout and truncates on another; both look plausible until you render.
    """
    m = class_start(cls).search(doc)
    if not m: return None
    tag, start = m.group(1), m.end()
    depth, i = 1, start
    pat = re.compile(rf'</?{tag}\b', re.I)
    while depth and (t := pat.search(doc, i)):
        depth += -1 if t.group(0).startswith("</") else 1
        i = t.end()
    return doc[start:i - len(f"</{tag}>")] if depth == 0 else doc[start:]

def strip_class(frag, cls):
    """Remove every element carrying class token `cls`, matching its own closing tag at depth."""
    start = class_start(cls)
    pos = 0
    while (m := start.search(frag, pos)):
        tag, depth, i = m.group(1), 1, m.end()
        pat = re.compile(rf'</?{tag}\b[^>]*>', re.I)
        while depth and (t := pat.search(frag, i)):
            depth += -1 if t.group(0).startswith("</") else (0 if t.group(0).endswith("/>") else 1)
            i = t.end()
        if depth:
            pos = m.end()    # never closed: leave it, balance() deals with it
        else:
            frag = frag[:m.start()] + frag[i:]
            pos = m.start()
    return frag

def detect_content_class(pages):
    """The container class that appears once per page and wraps the most text."""
    counts = Counter()
    for p in pages[:8]:
        s = p.read_text(encoding="utf-8", errors="ignore")
        for cls in [c[1] for c in re.findall(r'<(?:div|main|article)[^>]*\sclass=(["\'])([^"\']+)\1', s)]:
            for c in cls.split():
                if c in ("content", "main", "article", "body-text", "lesson", "prose",
                         "page-content", "abody", "post", "entry", "doc", "text"):
                    counts[c] += 1
    return counts.most_common(1)[0][0] if counts else "content"

def detect_css(page, site):
    """Linked stylesheet if there is one, else the page's own inline <style> blocks."""
    s = page.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'<link[^>]+href="([^"]+\.css)"', s)
    if m:
        rel = re.sub(r'^(\.\./)+', '', m.group(1))
        cand = site / rel
        if cand.exists(): return cand.read_text(encoding="utf-8")
    inline = re.findall(r'<style[^>]*>(.*?)</style>', s, re.S)
    return "\n".join(inline) if inline else None

MATHJAX = ('<script>window.MathJax={tex:{inlineMath:[[\'\\\\(\',\'\\\\)\']],'
           'displayMath:[[\'\\\\[\',\'\\\\]\']],processEscapes:true},'
           'svg:{fontCache:\'global\'}};</script>\n'
           '<script id="MathJax-script" async '
           'src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg.js" '
           'onerror="console.error(\'COURSE_PDF_MATHJAX_FAILED\')"></script>')
MATHJAX_VERSION = "3.2.2"


def detect_math(page):
    """Carry over the source page's own maths stack, if it has one.

    Injecting MathJax and hoping was wrong twice over on a KaTeX site: MathJax
    was configured for \\( \\) while the pages are written with $ ... $, so it
    loaded and matched nothing and every equation printed as raw LaTeX; and the
    site's custom macros (\\E, \\KL, \\given) exist only in ITS config, so even
    with the delimiters fixed the macros would have come out unrendered.

    Reusing the page's own KaTeX tags means the PDF renders exactly as the site
    does, macros included. A page without KaTeX gets MathJax injected when the
    bound pages hold \\( \\) or \\[ \\] maths; it reads only those delimiters and does not
    carry over a site's own MathJax setup.
    """
    s = page.read_text(encoding="utf-8", errors="ignore")
    tags = re.findall(r'<link[^>]+katex[^>]*>', s, re.I)
    tags += re.findall(r'<script[^>]+katex[^>]*>\s*</script>', s, re.I)
    if not tags:
        return None, "mathjax"
    # the inline block that drives the renderer, copied whole rather than sliced:
    # a mid-script cut is how you get a syntax error that silently kills all maths
    for m in re.finditer(r'<script(?![^>]*\bsrc=)[^>]*>.*?</script>', s, re.S | re.I):
        if "renderMathInElement" in m.group(0):
            tags.append(m.group(0))
            break
    return "\n".join(tags), f"katex from source ({len(tags)} tags)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site"); ap.add_argument("--index", default="index.html")
    ap.add_argument("--pattern", default=r'(?:session|lesson|week|chapter|module|unit|part|topic)[-_ ]?\d*/')
    ap.add_argument("--content", default=None); ap.add_argument("--css", default=None)
    ap.add_argument("--min-words", type=int, default=40,
                    help="skip sections shorter than this (default 40); 0 keeps everything")
    ap.add_argument("--strip", default=""); ap.add_argument("--keep", default="")
    ap.add_argument("--title", default=None); ap.add_argument("--subtitle", default="")
    ap.add_argument("--out", default=None); ap.add_argument("--density", action="store_true")
    ap.add_argument("--no-typeset", action="store_true")
    ap.add_argument("--print-css", default=None)
    a = ap.parse_args()

    site = pathlib.Path(a.site).resolve()
    idx_path = site / a.index
    if not idx_path.exists(): sys.exit(f"no index at {idx_path}")
    idx = idx_path.read_text(encoding="utf-8")

    ordered, seen = [], set()
    for m in re.finditer(r'<a\b[^>]*?\shref="([^"#?:]+)"[^>]*>(.*?)</a>', idx, re.S | re.I):
        href = m.group(1)
        if not re.search(a.pattern, href): continue
        if href in seen: continue
        f = (site / unquote(href))
        if f.is_dir(): f = f / "index.html"
        if f.suffix != ".html" or not f.exists(): continue
        seen.add(href)
        label = ' '.join(H.unescape(re.sub('<[^>]+>', '', m.group(2))).split())
        ordered.append((href, label, f))
    if not ordered: sys.exit(f"no lesson pages matched {a.pattern!r} in {a.index}")

    content = a.content or detect_content_class([f for _, _, f in ordered])
    if a.css:
        css = pathlib.Path(a.css).read_text(encoding="utf-8")
    else:
        css = detect_css(ordered[0][2], site) or ""

    keep = {k.strip() for k in a.keep.split(",") if k.strip()}
    strip = [s for s in DEFAULT_STRIP if s not in keep] + \
            [s.strip() for s in a.strip.split(",") if s.strip()]

    parts, toc, cur, words = [], [], None, 0
    skipped = []
    for n, (href, label, f) in enumerate(ordered, 1):
        s = f.read_text(encoding="utf-8")
        b = extract(s, content)
        if b is None:
            print(f"  skip (no .{content}): {href}", file=sys.stderr); continue
        hdr = re.search(r"<header>(.*?)</header>", s, re.S)
        for cls in strip:
            b = strip_class(b, cls)
            b = re.sub(rf'<!-- {cls.upper().replace("-","_")}-START -->.*?<!-- {cls.upper().replace("-","_")}-END -->', "", b, flags=re.S|re.I)
        b = re.sub(r'<!-- [A-Z-]*NAV-START -->.*?<!-- [A-Z-]*NAV-END -->', "", b, flags=re.S)
        def _abs(m, page=f):
            u = m.group(1)
            if re.match(r'(?:[a-z][a-z0-9+.-]*:|//|#)', u, re.I): return m.group(0)
            base = site if u.startswith("/") else page.parent
            return 'src="' + str((base / unquote(u.lstrip("/"))).resolve()) + '"'
        b = re.sub(r'src="([^"]+)"', _abs, b)
        b = balance(b)
        nw = len(H.unescape(re.sub("<[^>]+>", " ", b)).split())
        # A course under construction publishes placeholder pages for the weeks
        # it has not written. Binding them gives a contents list padded with
        # sections that are one sentence long and a run of near-blank pages: ten
        # of them, 15% of the book, on a course two weeks into twelve. Skipped
        # out loud, never silently, because a section that vanishes without a
        # word looks exactly like a section that was never there.
        #
        # A page carrying embedded video is NOT one of these. It is short only
        # because iframes do not print, and dropping it would lose a real
        # section: one such page on a real course site holds 34 words and five videos.
        embeds = len(re.findall(r"<iframe|<video|<embed|<object", b, re.I))
        if nw < a.min_words and not embeds:
            skipped.append(f"{label} ({nw}w)")
            continue
        words += nw
        grp = re.search(a.pattern + r"?([\w-]+)/", href)
        key = grp.group(1) if grp else "all"
        if key != cur:
            if cur is not None: parts.append("</div>")
            parts.append('<div class="pdfsection">'); cur = key
        toc.append(f'<li><a href="#pg{n}">{H.escape(label)}</a></li>')
        parts.append(f'<section class="pdflesson" id="pg{n}">'
                     f'<header>{hdr.group(1) if hdr else ""}</header>{b}</section>')
    if cur is not None: parts.append("</div>")
    if not toc:
        sys.exit(f"no section was bound: none of the {len(ordered)} pages held a .{content} container "
                 f"of at least {a.min_words} words. Check --content, or lower --min-words.")

    typeset = "" if a.no_typeset else (pathlib.Path(a.print_css) if a.print_css
                                       else HERE / "print.css").read_text(encoding="utf-8")
    title = a.title or site.name.replace("-", " ")
    mathblock, mathwhich = detect_math(ordered[0][2])
    if mathwhich == "mathjax":
        if re.search(r'\\\(|\\\[', "".join(parts)):
            mathblock, mathwhich = MATHJAX, f"mathjax {MATHJAX_VERSION} (injected)"
        else:
            mathblock, mathwhich = "", "none (no \\( or \\[ maths in the pages)"
    out = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>{H.escape(title)}</title>
{mathblock}
<style>{css}</style><style>{typeset}</style></head><body>
<div class="pdftitle"><h1>{H.escape(title)}</h1><p>{H.escape(a.subtitle)}</p>
<p class="pdfmeta">{len(toc)} sections</p></div>
<div class="pdfcontents"><h1>Contents</h1><ol>{''.join(toc)}</ol></div>
{''.join(parts)}</body></html>"""

    tmp = site / "_coursebook.html"; tmp.write_text(out, encoding="utf-8")
    pdf = pathlib.Path(a.out) if a.out else site.parent / f"{site.name}-book.pdf"
    try:
        run = subprocess.run([find_chrome(), "--headless", "--disable-gpu", "--no-sandbox",
                              "--run-all-compositor-stages-before-draw", "--virtual-time-budget=60000",
                              "--enable-logging=stderr", "--v=0",
                              "--no-pdf-header-footer", f"--print-to-pdf={pdf}", tmp.as_uri()],
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    finally:
        tmp.unlink(missing_ok=True)
    if run.returncode != 0 or not pdf.exists():
        sys.exit(f"Chrome did not write {pdf} (exit {run.returncode}):\n" + run.stderr[-2000:])
    if "COURSE_PDF_MATHJAX_FAILED" in run.stderr:
        print("  WARNING: MathJax did not load (no network?); the maths in this PDF is raw LaTeX.",
              file=sys.stderr)
    n_pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))
    print(f"  container .{content}   css {'found' if css else 'NONE — output will be unstyled'}"
          f"   maths {mathwhich}")
    if skipped:
        print(f"  skipped {len(skipped)} section(s) under {a.min_words} words: "
              + ", ".join(skipped[:6]) + (" ..." if len(skipped) > 6 else ""))
    print(f"  {len(toc)} sections, {words:,} words -> {pdf.name}")
    print(f"  {n_pages} pages, {words // max(1, n_pages)} words/page   ({pdf.stat().st_size/1e6:.1f} MB)")
    wpp = words // max(1, n_pages)
    if not a.no_typeset and wpp < 380:
        print("  DENSITY LOW: the site CSS may still be overriding print.css, or the book is short and its"
              " title and contents pages weigh on the average. See SKILL.md step 4.")
    if wpp > 700:
        print(f"  DENSITY IMPOSSIBLE ({wpp}/page): pages are being dropped or overlapping.")
        print("  Render a few pages and look before believing this PDF. See SKILL.md step 5.")

main()
