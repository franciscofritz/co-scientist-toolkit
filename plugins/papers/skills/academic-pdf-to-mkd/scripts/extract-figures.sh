#!/bin/bash
# Extract figure images from PDF and create metadata files
# Usage: ./scripts/extract-figures.sh <pdf_path> <output_dir> <paper_id>
#
# Uses pdfimages to extract embedded images, filters out tiny ones (<50x50px),
# and creates metadata Markdown files for each figure.

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PDF_PATH="$1"
OUTPUT_DIR="$2"
PAPER_ID="$3"

FIGURES_DIR="$OUTPUT_DIR/figures"
TEMP_DIR="$OUTPUT_DIR/.tmp-figures-$$"
mkdir -p "$TEMP_DIR"
trap "rm -rf '$TEMP_DIR'" EXIT

mkdir -p "$FIGURES_DIR"

if ! command -v pdfimages >/dev/null 2>&1; then
    echo -e "  ${RED}Error: pdfimages not found. Install: brew install poppler${NC}"
    exit 1
fi

# Extract all embedded images with page numbers
echo -e "  Extracting embedded images..."
pdfimages -png -p "$PDF_PATH" "$TEMP_DIR/img"

# Count raw extractions
RAW_COUNT=$(find "$TEMP_DIR" -name "*.png" | wc -l | tr -d ' ')
echo -e "  Raw images extracted: $RAW_COUNT"

if [ "$RAW_COUNT" -eq 0 ]; then
    echo -e "  ${YELLOW}No embedded images found in PDF${NC}"
    exit 0
fi

# Filter and rename
FIG_NUM=0
MIN_WIDTH=50
MIN_HEIGHT=50

for img in "$TEMP_DIR"/img-*.png; do
    [ -f "$img" ] || continue

    # Get dimensions
    if command -v identify >/dev/null 2>&1; then
        DIMS=$(identify -format "%w %h" "$img" 2>/dev/null || echo "0 0")
        WIDTH=$(echo "$DIMS" | awk '{print $1}')
        HEIGHT=$(echo "$DIMS" | awk '{print $2}')
    else
        # Fallback: use file size as proxy (skip files < 1KB)
        FILE_SIZE=$(stat -f%z "$img" 2>/dev/null || stat -c%s "$img" 2>/dev/null || echo "0")
        if [ "$FILE_SIZE" -lt 1024 ]; then
            continue
        fi
        WIDTH=100
        HEIGHT=100
    fi

    # Skip tiny images (icons, bullets, decorations)
    if [ "$WIDTH" -lt "$MIN_WIDTH" ] || [ "$HEIGHT" -lt "$MIN_HEIGHT" ]; then
        continue
    fi

    FIG_NUM=$((FIG_NUM + 1))
    FIG_ID=$(printf "%s-figure-%02d" "$PAPER_ID" "$FIG_NUM")

    # Extract page number from filename (format: img-PPP-NNN.png)
    IMG_BASENAME="$(basename "$img")"
    PAGE_NUM=$(echo "$IMG_BASENAME" | sed 's/img-0*//' | sed 's/-.*//')

    # Copy figure
    cp "$img" "$FIGURES_DIR/${FIG_ID}.png"

    # Create metadata file
    cat > "$FIGURES_DIR/${FIG_ID}.md" << EOF
---
figure_id: "${FIG_ID}"
source_page: ${PAGE_NUM}
dimensions: "${WIDTH}x${HEIGHT}"
status: "auto-extracted"
caption: ""
---

# Figure ${FIG_NUM}

- **Source page:** ${PAGE_NUM}
- **Dimensions:** ${WIDTH}×${HEIGHT}px
- **Image:** [${FIG_ID}.png](${FIG_ID}.png)

## Caption

> _Caption not yet populated. Check the fulltext for "Fig. ${FIG_NUM}" or "Figure ${FIG_NUM}" references._
EOF

done

echo -e "  ${GREEN}✓ $FIG_NUM figure(s) extracted (filtered from $RAW_COUNT raw images)${NC}"

if [ "$FIG_NUM" -gt 0 ]; then
    echo -e "  ${YELLOW}→ Review figure metadata files and add captions from the fulltext${NC}"
fi
