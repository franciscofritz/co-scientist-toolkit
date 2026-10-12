#!/bin/bash
# Render PDF pages as PNG images for visual reference
# Usage: ./scripts/extract-pages.sh <pdf_path> <output_dir> <paper_id>

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PDF_PATH="$1"
OUTPUT_DIR="$2"
PAPER_ID="$3"

PAGES_DIR="$OUTPUT_DIR/pages"
mkdir -p "$PAGES_DIR"

if ! command -v pdftoppm >/dev/null 2>&1; then
    echo -e "  ${RED}Error: pdftoppm not found. Install: brew install poppler${NC}"
    exit 1
fi

echo -e "  Rendering pages at 150dpi..."
pdftoppm -r 150 -png "$PDF_PATH" "$PAGES_DIR/page"

# Rename to zero-padded format (pdftoppm uses varying padding)
# pdftoppm outputs page-1.png, page-2.png or page-01.png etc.
# Normalise to page-001.png, page-002.png
for f in "$PAGES_DIR"/page-*.png; do
    [ -f "$f" ] || continue
    basename_f="$(basename "$f")"
    # Extract the number
    num=$(echo "$basename_f" | sed 's/page-0*//' | sed 's/\.png//')
    # Zero-pad to 3 digits
    new_name=$(printf "page-%03d.png" "$num")
    if [ "$basename_f" != "$new_name" ]; then
        mv "$f" "$PAGES_DIR/$new_name"
    fi
done

PAGE_COUNT=$(find "$PAGES_DIR" -name "*.png" | wc -l | tr -d ' ')
echo -e "  ${GREEN}✓ $PAGE_COUNT page images saved to $PAGES_DIR${NC}"
