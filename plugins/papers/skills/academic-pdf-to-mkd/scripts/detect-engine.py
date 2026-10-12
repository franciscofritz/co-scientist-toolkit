"""Pick an extraction engine based on the PDF's text-layer characteristics.

Prints one of: docling | fast | math

Rules (post-OCR PDF assumed — caller runs ocr-preflight first):
  - math engine  if math-symbol density per word exceeds MATH_RATIO_THRESHOLD
  - fast engine  if the document is short, dense, clean, low-math
  - docling      otherwise (default)
"""

from __future__ import annotations

import re
import subprocess
import sys
import unicodedata

MATH_RATIO_THRESHOLD = 0.04
FAST_MAX_PAGES = 12
FAST_MIN_WORDS_PER_PAGE = 200
FAST_MAX_MATH_RATIO = 0.01

EXTRA_MATH_CHARS = set("∑∫∮∂∇∆≈≠≤≥∈∉∀∃∪∩⊆⊂⊇⊃±×÷√∞∝⊕⊗⋅←→↔⇒⇔αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΠΣΥΦΨΩ")


def count_math_chars(text: str) -> int:
    count = 0
    for ch in text:
        if ch in EXTRA_MATH_CHARS:
            count += 1
            continue
        if unicodedata.category(ch) == "Sm":  # math symbol
            count += 1
    # Inline-equation hints: (1), (2.3a) reference markers in body text
    count += len(re.findall(r"\([0-9]+(?:\.[0-9]+)?[a-z]?\)", text))
    return count


def page_count(pdf_path: str) -> int:
    try:
        out = subprocess.check_output(["pdfinfo", pdf_path], text=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 0
    for line in out.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split()[1])
            except (IndexError, ValueError):
                return 0
    return 0


def pdf_text(pdf_path: str) -> str:
    try:
        return subprocess.check_output(
            ["pdftotext", "-layout", pdf_path, "-"], text=True, stderr=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def choose_engine(pdf_path: str) -> tuple[str, dict]:
    text = pdf_text(pdf_path)
    words = text.split()
    word_count = len(words)
    math_chars = count_math_chars(text)
    pages = page_count(pdf_path) or 1
    math_ratio = math_chars / word_count if word_count else 0.0
    words_per_page = word_count / pages if pages else 0

    metrics = {
        "pages": pages,
        "words": word_count,
        "math_chars": math_chars,
        "math_ratio": round(math_ratio, 4),
        "words_per_page": int(words_per_page),
    }

    if math_ratio >= MATH_RATIO_THRESHOLD:
        return "math", metrics
    if (
        pages <= FAST_MAX_PAGES
        and words_per_page >= FAST_MIN_WORDS_PER_PAGE
        and math_ratio < FAST_MAX_MATH_RATIO
    ):
        return "fast", metrics
    return "docling", metrics


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: detect-engine.py <pdf_path>", file=sys.stderr)
        return 1
    engine, metrics = choose_engine(sys.argv[1])
    print(
        f"detect-engine: pages={metrics['pages']} words={metrics['words']} "
        f"math_chars={metrics['math_chars']} math_ratio={metrics['math_ratio']} "
        f"words_per_page={metrics['words_per_page']} -> {engine}",
        file=sys.stderr,
    )
    print(engine)
    return 0


if __name__ == "__main__":
    sys.exit(main())
