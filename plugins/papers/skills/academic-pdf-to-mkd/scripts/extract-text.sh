#!/bin/bash
# Extract and clean text from a PDF into structured Markdown
# Usage: ./scripts/extract-text.sh <pdf_path> <output_dir> <paper_id> [--ocr]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PDF_PATH="$1"
OUTPUT_DIR="$2"
PAPER_ID="$3"
USE_OCR="${4:-}"

TEMP_DIR="$OUTPUT_DIR/.tmp-text-$$"
mkdir -p "$TEMP_DIR"
trap "rm -rf '$TEMP_DIR'" EXIT

# Get page count for frontmatter
PAGE_COUNT=0
if command -v pdfinfo >/dev/null 2>&1; then
    PAGE_COUNT=$(pdfinfo "$PDF_PATH" 2>/dev/null | grep "^Pages:" | awk '{print $2}' || echo "0")
fi

if [ "$USE_OCR" = "--ocr" ]; then
    # OCR mode: render pages then OCR
    echo -e "  ${YELLOW}Using OCR mode (tesseract)...${NC}"

    if ! command -v tesseract >/dev/null 2>&1; then
        echo -e "  ${RED}Error: tesseract not found. Install: brew install tesseract${NC}"
        exit 1
    fi

    # Render pages at 300dpi for OCR
    pdftoppm -r 300 -png "$PDF_PATH" "$TEMP_DIR/ocr-page"

    # OCR each page
    > "$TEMP_DIR/raw-text.txt"
    for img in "$TEMP_DIR"/ocr-page-*.png; do
        tesseract "$img" "$TEMP_DIR/ocr-tmp" --psm 1 2>/dev/null
        cat "$TEMP_DIR/ocr-tmp.txt" >> "$TEMP_DIR/raw-text.txt"
        echo -e "\f" >> "$TEMP_DIR/raw-text.txt"  # Page break
        rm -f "$TEMP_DIR/ocr-tmp.txt"
    done

    echo -e "  ${GREEN}✓ OCR complete${NC}"
else
    # Standard mode: pdftotext with layout
    if ! command -v pdftotext >/dev/null 2>&1; then
        echo -e "  ${RED}Error: pdftotext not found. Install: brew install poppler${NC}"
        exit 1
    fi

    echo -e "  Extracting text with pdftotext -layout..."
    pdftotext -layout "$PDF_PATH" "$TEMP_DIR/raw-text.txt" 2>&1 || {
        echo -e "  ${YELLOW}Warning: pdftotext reported issues${NC}"
    }

    echo -e "  ${GREEN}✓ Raw text extracted${NC}"
fi

# Post-process with clean-text.py
OUTPUT_FILE="$OUTPUT_DIR/${PAPER_ID}-fulltext.md"

echo -e "  Cleaning and structuring text..."
python3 "$SCRIPT_DIR/clean-text.py" \
    "$TEMP_DIR/raw-text.txt" \
    "$OUTPUT_FILE" \
    --pdf-path "$PDF_PATH" \
    --page-count "$PAGE_COUNT"

# Report stats
LINE_COUNT=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
HEADING_COUNT=$(grep -c "^#" "$OUTPUT_FILE" || true)
echo -e "  ${GREEN}✓ Fulltext: $OUTPUT_FILE ($LINE_COUNT lines, $HEADING_COUNT headings)${NC}"
