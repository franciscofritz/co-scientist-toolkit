#!/usr/bin/env python3
"""Detect and extract tables from pdftotext -layout output.

Usage:
    python3 detect-tables.py <input_txt> <output_dir> <paper_id>

Reads raw pdftotext -layout output and uses heuristics to detect table regions:
- Lines with consistent column spacing (multiple whitespace gaps)
- Lines with multiple whitespace-separated numeric values
- Lines following a "Table N" caption

For each detected table, outputs:
- {paper_id}-table-NN-raw.txt  — raw text block
- {paper_id}-table-NN.md      — Markdown table with YAML frontmatter
- {paper_id}-table-NN.csv     — CSV (best-effort)
"""

import re
import os
import sys
import csv
import io
import argparse
from datetime import datetime, timezone


def parse_args():
    parser = argparse.ArgumentParser(description="Detect and extract tables from pdftotext output")
    parser.add_argument("input_txt", help="Path to raw pdftotext -layout output")
    parser.add_argument("output_dir", help="Output directory for table files")
    parser.add_argument("paper_id", help="Paper identifier for filenames")
    return parser.parse_args()


def find_table_regions(lines):
    """Detect table regions using heuristics.
    
    Returns list of (start_line, end_line, caption) tuples.
    """
    tables = []
    caption_pattern = re.compile(
        r"^\s*(Table)\s*\.?\s*(\d+)\s*[:.|\s](.+)",
        re.IGNORECASE,
    )

    i = 0
    while i < len(lines):
        # Look for table captions
        m = caption_pattern.match(lines[i])
        if m:
            table_num = int(m.group(2))
            caption = m.group(3).strip()

            # Collect caption continuation
            caption_end = i
            while (caption_end + 1 < len(lines) and
                   lines[caption_end + 1].strip() and
                   not is_table_row(lines[caption_end + 1]) and
                   not caption_pattern.match(lines[caption_end + 1])):
                caption += " " + lines[caption_end + 1].strip()
                caption_end += 1

            # Look for the table body starting after the caption
            body_start = caption_end + 1
            # Skip blank lines between caption and table
            while body_start < len(lines) and not lines[body_start].strip():
                body_start += 1

            if body_start >= len(lines):
                i += 1
                continue

            # Find the end of the table body
            body_end = find_table_end(lines, body_start)

            if body_end > body_start:
                tables.append((body_start, body_end, caption, table_num))

            i = body_end + 1
        else:
            # Also detect tables without explicit captions
            # Look for runs of lines with consistent column structure
            if is_table_row(lines[i]) and is_likely_table_start(lines, i):
                body_start = i
                body_end = find_table_end(lines, body_start)
                if body_end - body_start >= 2:  # At least 3 rows
                    tables.append((body_start, body_end, "", len(tables) + 1))
                i = body_end + 1
            else:
                i += 1

    return tables


def is_table_row(line):
    """Check if a line looks like a table row.
    
    Heuristics:
    - Has multiple blocks separated by 2+ spaces
    - Contains numbers or short text fields
    """
    stripped = line.strip()
    if not stripped or len(stripped) < 5:
        return False

    # Count whitespace gaps of 2+ spaces
    gaps = re.findall(r"\s{2,}", stripped)
    if len(gaps) < 1:
        return False

    # Split on whitespace gaps and check we have multiple columns
    columns = re.split(r"\s{2,}", stripped)
    columns = [c.strip() for c in columns if c.strip()]

    if len(columns) < 2:
        return False

    # Check that columns are reasonably short (not full sentences)
    avg_col_len = sum(len(c) for c in columns) / len(columns)
    if avg_col_len > 40:
        return False

    return True


def is_likely_table_start(lines, idx):
    """Check if position idx is likely the start of a table.
    
    Requires the previous line to be blank or a caption-like line,
    and at least 2 subsequent lines to also look like table rows.
    """
    if idx > 0 and lines[idx - 1].strip():
        # Previous line should be blank or a separator
        prev = lines[idx - 1].strip()
        if not re.match(r"^[-=_\s]+$", prev) and not re.match(r"^\s*Table\s", prev, re.IGNORECASE):
            return False

    count = 0
    for j in range(idx, min(idx + 5, len(lines))):
        if is_table_row(lines[j]):
            count += 1
    return count >= 3


def find_table_end(lines, start):
    """Find the end of a table body starting at `start`.
    
    A table ends when we hit:
    - 2+ consecutive blank lines
    - A line that looks like a new section heading
    - A line that looks like a caption for a different element
    """
    blank_count = 0
    end = start
    heading_pattern = re.compile(r"^#{1,3}\s")
    caption_pattern = re.compile(r"^\s*(Fig\.?|Figure|Table)\s*\.?\s*\d+", re.IGNORECASE)

    for i in range(start, len(lines)):
        stripped = lines[i].strip()

        if not stripped:
            blank_count += 1
            if blank_count >= 2:
                break
            continue
        else:
            blank_count = 0

        if heading_pattern.match(stripped):
            break

        # New caption means table ended
        if i > start + 1 and caption_pattern.match(stripped):
            break

        # Separator lines are part of the table
        if re.match(r"^[-=_\s]+$", stripped):
            end = i
            continue

        # Regular content line — check if it still looks tabular
        if is_table_row(lines[i]) or len(stripped) < 5:
            end = i
        else:
            # Non-tabular line — might be table note or end
            # Allow one non-tabular line (could be a table note)
            if i + 1 < len(lines) and is_table_row(lines[i + 1]):
                end = i
            else:
                break

    return end


def extract_columns(lines):
    """Extract column boundaries from table lines.
    
    Uses whitespace gap positions to determine column boundaries.
    """
    if not lines:
        return []

    # Find positions where gaps consistently appear
    gap_positions = []
    for line in lines:
        positions = []
        in_gap = False
        gap_start = 0
        for j, ch in enumerate(line):
            if ch == " ":
                if not in_gap:
                    in_gap = True
                    gap_start = j
            else:
                if in_gap and (j - gap_start) >= 2:
                    positions.append((gap_start, j))
                in_gap = False
        gap_positions.append(positions)

    if not gap_positions:
        return []

    # Find consistent gap regions — positions that appear in most lines
    # Use a simple approach: split on 2+ spaces for each line
    all_rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped or re.match(r"^[-=_\s]+$", stripped):
            continue
        cols = re.split(r"\s{2,}", stripped)
        cols = [c.strip() for c in cols if c.strip()]
        all_rows.append(cols)

    return all_rows


def table_to_markdown(rows, caption=""):
    """Convert extracted rows to a Markdown table."""
    if not rows:
        return ""

    # Determine max columns
    max_cols = max(len(r) for r in rows)

    # Pad rows to same length
    padded = []
    for row in rows:
        padded.append(row + [""] * (max_cols - len(row)))

    # Build markdown
    md_lines = []
    if caption:
        md_lines.append(f"> **Table:** {caption}")
        md_lines.append("")

    # Header row
    md_lines.append("| " + " | ".join(padded[0]) + " |")
    md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")

    # Data rows
    for row in padded[1:]:
        md_lines.append("| " + " | ".join(row) + " |")

    return "\n".join(md_lines)


def table_to_csv(rows):
    """Convert extracted rows to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def process_tables(input_path, output_dir, paper_id):
    """Main processing function."""
    os.makedirs(output_dir, exist_ok=True)

    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    lines = text.split("\n")
    regions = find_table_regions(lines)

    if not regions:
        print("No tables detected.")
        return 0

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    table_count = 0

    for start, end, caption, table_num in regions:
        table_count += 1
        table_id = f"{paper_id}-table-{table_num:02d}"
        table_lines = lines[start : end + 1]
        raw_text = "\n".join(table_lines)

        # Save raw text
        raw_path = os.path.join(output_dir, f"{table_id}-raw.txt")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(raw_text)

        # Extract columns and build structured output
        rows = extract_columns(table_lines)

        if rows:
            # Markdown output with frontmatter
            md_content = [
                "---",
                f'table_id: "{table_id}"',
                f'caption: "{caption}"',
                f'extracted_at: "{now}"',
                f"source_lines: [{start + 1}, {end + 1}]",
                f'status: "auto-extracted"',
                "---",
                "",
                table_to_markdown(rows, caption),
            ]
            md_path = os.path.join(output_dir, f"{table_id}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_content))

            # CSV output
            csv_content = table_to_csv(rows)
            csv_path = os.path.join(output_dir, f"{table_id}.csv")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write(csv_content)

        print(f"✓ Table {table_num}: {len(table_lines)} lines → {table_id}")

    return table_count


def main():
    args = parse_args()
    count = process_tables(args.input_txt, args.output_dir, args.paper_id)
    print(f"✓ Extracted {count} table(s)")


if __name__ == "__main__":
    main()
