#!/usr/bin/env python3
"""Post-process pdftotext output into structured Markdown.

Usage:
    python3 clean-text.py <input_txt> <output_md> [--pdf-path <path>] [--page-count <n>]

Reads raw pdftotext -layout output and produces clean Markdown with:
- YAML frontmatter with extraction metadata
- Detected section headings converted to # / ## / ###
- Removed page headers and footers
- Rejoined hyphenated words at line breaks
- Detected figure/table captions marked as blockquotes
- Formatted references section
"""

import re
import sys
import os
import argparse
from datetime import datetime, timezone
from collections import Counter


def parse_args():
    parser = argparse.ArgumentParser(description="Clean pdftotext output into structured Markdown")
    parser.add_argument("input_txt", help="Path to raw pdftotext output")
    parser.add_argument("output_md", help="Path for output Markdown file")
    parser.add_argument("--pdf-path", default="", help="Original PDF path (for frontmatter)")
    parser.add_argument("--page-count", type=int, default=0, help="Page count (for frontmatter)")
    return parser.parse_args()


def read_input(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def split_pages(text):
    """Split text on form-feed characters (page breaks from pdftotext)."""
    return text.split("\f")


def detect_headers_footers(pages, threshold=0.5):
    """Detect repeated lines at the top/bottom of pages (headers/footers).
    
    A line is considered a header/footer if it appears in more than
    `threshold` fraction of pages (ignoring empty lines and very short lines).
    """
    page_num_pattern = re.compile(r"^\s*\d{1,4}\s*$")

    if len(pages) < 3:
        return set(), set(), page_num_pattern

    # Collect first and last non-empty lines from each page
    first_lines = Counter()
    last_lines = Counter()

    for page in pages:
        lines = [l.strip() for l in page.split("\n") if l.strip()]
        if not lines:
            continue
        # Check first 3 lines for headers
        for line in lines[:3]:
            if len(line) > 5:
                first_lines[line] += 1
        # Check last 3 lines for footers
        for line in lines[-3:]:
            if len(line) > 5:
                last_lines[line] += 1

    min_occurrences = max(2, int(len(pages) * threshold))

    headers = {line for line, count in first_lines.items() if count >= min_occurrences}
    footers = {line for line, count in last_lines.items() if count >= min_occurrences}

    # Page numbers (standalone digits) are matched by page_num_pattern.
    return headers, footers, page_num_pattern


def remove_headers_footers(text, headers, footers, page_num_pattern):
    """Remove detected header/footer lines from text."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped in headers or stripped in footers:
            continue
        if page_num_pattern.match(stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def fix_hyphenation(text):
    """Rejoin words hyphenated across line breaks.
    
    Matches patterns like 'word-\\n  continuation' and joins them.
    Only rejoins when the second part starts with a lowercase letter.
    """
    # Handle hyphenation at end of line followed by next line starting with lowercase
    text = re.sub(r"(\w)-\s*\n\s*([a-z])", r"\1\2", text)
    return text


def detect_headings(text):
    """Convert detected section headings to Markdown heading syntax.
    
    Detects:
    - Numbered sections: 1. Introduction, 2.1 Methods, etc.
    - ALL CAPS lines (likely section titles)
    - Common section names: Abstract, Introduction, Methods, etc.
    """
    lines = text.split("\n")
    result = []
    prev_blank = True  # Track if previous line was blank

    # Patterns for numbered headings
    numbered_h2 = re.compile(r"^\s*(\d+)\.\s+([A-Z][\w\s,:&-]+)$")
    numbered_h3 = re.compile(r"^\s*(\d+\.\d+)\s+([A-Z][\w\s,:&-]+)$")
    numbered_h4 = re.compile(r"^\s*(\d+\.\d+\.\d+)\s+([A-Z][\w\s,:&-]+)$")

    # Common section names (case-insensitive match for ALL CAPS)
    section_names = {
        "ABSTRACT", "INTRODUCTION", "BACKGROUND", "METHODS", "METHODOLOGY",
        "MATERIALS AND METHODS", "RESULTS", "DISCUSSION", "CONCLUSION",
        "CONCLUSIONS", "REFERENCES", "BIBLIOGRAPHY", "ACKNOWLEDGMENTS",
        "ACKNOWLEDGEMENTS", "APPENDIX", "SUPPLEMENTARY", "SUPPLEMENTARY MATERIALS",
        "RELATED WORK", "LITERATURE REVIEW", "THEORETICAL FRAMEWORK",
        "DATA AND METHODS", "FINDINGS", "LIMITATIONS", "FUTURE WORK",
        "ETHICAL CONSIDERATIONS", "FUNDING", "CONFLICT OF INTEREST",
        "AUTHOR CONTRIBUTIONS", "DATA AVAILABILITY",
    }

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            result.append("")
            prev_blank = True
            continue

        # Check numbered headings (most specific first)
        m = numbered_h4.match(stripped)
        if m and prev_blank and len(stripped) < 80:
            result.append(f"### {m.group(1)} {m.group(2).strip()}")
            prev_blank = False
            continue

        m = numbered_h3.match(stripped)
        if m and prev_blank and len(stripped) < 80:
            result.append(f"### {m.group(1)} {m.group(2).strip()}")
            prev_blank = False
            continue

        m = numbered_h2.match(stripped)
        if m and prev_blank and len(stripped) < 80:
            result.append(f"## {m.group(1)}. {m.group(2).strip()}")
            prev_blank = False
            continue

        # Check lines that match known section names (case-insensitive)
        if stripped.upper() in section_names:
            title = stripped.title()
            result.append(f"## {title}")
            prev_blank = False
            continue

        # Check for ALL CAPS lines (potential headings) — must be short and standalone
        if (stripped.upper() == stripped and
                len(stripped) > 3 and
                len(stripped) < 60 and
                prev_blank and
                not stripped.startswith("(") and
                not stripped.startswith("[") and
                re.match(r"^[A-Z][A-Z\s,&:;-]+$", stripped)):
            title = stripped.title()
            result.append(f"## {title}")
            prev_blank = False
            continue

        # Check for "Extended Data" style headings (Nature papers)
        if (prev_blank and
                len(stripped) < 80 and
                re.match(r"^Extended Data\s+(Fig\.|Figure|Table)\s+\d+", stripped)):
            result.append(f"### {stripped}")
            prev_blank = False
            continue

        result.append(line)
        prev_blank = False

    return "\n".join(result)


def detect_captions(text):
    """Detect figure and table captions and format as blockquotes."""
    lines = text.split("\n")
    result = []
    caption_pattern = re.compile(
        r"^\s*(Fig\.?|Figure|Table|Exhibit)\s*\.?\s*(\d+)\s*[:.|\s](.+)",
        re.IGNORECASE,
    )

    i = 0
    while i < len(lines):
        m = caption_pattern.match(lines[i])
        if m:
            caption_type = m.group(1).strip().rstrip(".")
            caption_num = m.group(2)
            caption_text = m.group(3).strip()

            # Captions often span multiple lines — collect continuation lines
            while (i + 1 < len(lines) and
                   lines[i + 1].strip() and
                   not caption_pattern.match(lines[i + 1]) and
                   not lines[i + 1].strip().startswith("#")):
                i += 1
                caption_text += " " + lines[i].strip()

            # Normalise caption type
            if caption_type.lower().startswith("fig"):
                caption_type = "Figure"
            elif caption_type.lower() == "table":
                caption_type = "Table"

            result.append(f"> **{caption_type} {caption_num}:** {caption_text}")
            result.append("")
        else:
            result.append(lines[i])
        i += 1

    return "\n".join(result)


def format_references(text):
    """Detect the references section and format entries as a numbered list."""
    lines = text.split("\n")
    result = []
    in_references = False
    ref_buffer = []

    # Pattern to detect start of a reference entry
    ref_start = re.compile(r"^\s*\[?\d{1,3}\]?\s*[A-Z]")
    ref_section = re.compile(r"^#{1,3}\s*(References|Bibliography)", re.IGNORECASE)

    def flush_ref():
        if ref_buffer:
            joined = " ".join(ref_buffer).strip()
            result.append(f"- {joined}")
            ref_buffer.clear()

    for line in lines:
        if ref_section.match(line):
            in_references = True
            result.append(line)
            continue

        if in_references:
            stripped = line.strip()
            if not stripped:
                flush_ref()
                result.append("")
                continue

            # New section heading exits references
            if line.startswith("#"):
                flush_ref()
                in_references = False
                result.append(line)
                continue

            if ref_start.match(stripped):
                flush_ref()
                ref_buffer.append(stripped)
            else:
                ref_buffer.append(stripped)
        else:
            result.append(line)

    flush_ref()
    return "\n".join(result)


def collapse_blank_lines(text):
    """Collapse runs of 3+ blank lines into 2."""
    return re.sub(r"\n{4,}", "\n\n\n", text)


def strip_trailing_whitespace(text):
    """Remove trailing whitespace from each line."""
    return "\n".join(line.rstrip() for line in text.split("\n"))


def add_frontmatter(text, pdf_path="", page_count=0):
    """Add YAML frontmatter with extraction metadata."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fm = [
        "---",
        f'source_pdf: "{os.path.basename(pdf_path)}"',
        f'extracted_at: "{now}"',
        'tool: "academic-pdf-to-mkd"',
    ]
    if page_count:
        fm.append(f"page_count: {page_count}")
    fm.append("---")
    fm.append("")
    return "\n".join(fm) + text


def clean_text(raw_text, pdf_path="", page_count=0):
    """Run the full cleaning pipeline on raw pdftotext output."""
    pages = split_pages(raw_text)

    # Detect and remove headers/footers
    headers, footers, page_num_pat = detect_headers_footers(pages)
    text = "\f".join(pages)
    text = remove_headers_footers(text, headers, footers, page_num_pat)

    # Remove form-feeds
    text = text.replace("\f", "\n")

    # Fix hyphenation
    text = fix_hyphenation(text)

    # Detect headings
    text = detect_headings(text)

    # Detect captions
    text = detect_captions(text)

    # Format references
    text = format_references(text)

    # Clean up whitespace
    text = collapse_blank_lines(text)
    text = strip_trailing_whitespace(text)

    # Add frontmatter
    text = add_frontmatter(text, pdf_path, page_count)

    return text


def main():
    args = parse_args()
    raw_text = read_input(args.input_txt)
    result = clean_text(raw_text, args.pdf_path, args.page_count)

    with open(args.output_md, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"✓ Cleaned text written to {args.output_md}")


if __name__ == "__main__":
    main()
