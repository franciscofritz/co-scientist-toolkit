#!/bin/bash
# Detect and extract tables from PDF using layout-based heuristics
# Usage: ./scripts/extract-tables.sh <pdf_path> <output_dir> <paper_id>
#
# Uses pdftotext -layout to get layout-preserved text, then Python heuristics
# to detect table regions and output Markdown + CSV + raw text.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PDF_PATH="$1"
OUTPUT_DIR="$2"
PAPER_ID="$3"

TABLES_DIR="$OUTPUT_DIR/tables"
TEMP_DIR="$OUTPUT_DIR/.tmp-tables-$$"
mkdir -p "$TEMP_DIR"
trap "rm -rf '$TEMP_DIR'" EXIT

mkdir -p "$TABLES_DIR"

if ! command -v pdftotext >/dev/null 2>&1; then
    echo -e "  ${RED}Error: pdftotext not found. Install: brew install poppler${NC}"
    exit 1
fi

# Extract layout-preserved text (separate from fulltext extraction to keep original layout)
echo -e "  Extracting layout text for table detection..."
pdftotext -layout "$PDF_PATH" "$TEMP_DIR/layout-text.txt" 2>&1 || {
    echo -e "  ${YELLOW}Warning: pdftotext reported issues${NC}"
}

# Run table detection
echo -e "  Running table detection heuristics..."
python3 "$SCRIPT_DIR/detect-tables.py" \
    "$TEMP_DIR/layout-text.txt" \
    "$TABLES_DIR" \
    "$PAPER_ID"

TABLE_COUNT=$(find "$TABLES_DIR" -name "*-raw.txt" 2>/dev/null | wc -l | tr -d ' ')

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo -e "  ${GREEN}✓ $TABLE_COUNT table(s) extracted to $TABLES_DIR${NC}"
    echo -e "  ${YELLOW}→ Review raw text files and verify Markdown/CSV output${NC}"
else
    echo -e "  ${YELLOW}No tables detected (this is expected for some papers)${NC}"
fi
