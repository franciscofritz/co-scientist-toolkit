#!/bin/bash
# OCR preflight — ensure the PDF has a usable text layer before extraction.
#
# Detects scan-only PDFs by counting words in the existing text layer.
# If sparse, runs ocrmypdf to produce a searchable copy and prints its path.
# If the layer is already populated, prints the original path unchanged.
#
# Usage: ./scripts/ocr-preflight.sh <pdf_path> <output_dir> [word_threshold]
# Output: prints the PDF path to use downstream (original or OCR'd copy).

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <pdf_path> <output_dir> [word_threshold]" >&2
    exit 1
fi

PDF_PATH="$1"
OUTPUT_DIR="$2"
THRESHOLD="${3:-100}"

if ! command -v pdftotext >/dev/null 2>&1; then
    echo "ocr-preflight: pdftotext not found; skipping OCR detection" >&2
    echo "$PDF_PATH"
    exit 0
fi

WORD_COUNT=$(pdftotext -layout "$PDF_PATH" - 2>/dev/null | wc -w | tr -d ' ')

echo "ocr-preflight: text-layer word count = $WORD_COUNT (threshold $THRESHOLD)" >&2

if [ "$WORD_COUNT" -ge "$THRESHOLD" ]; then
    echo "ocr-preflight: text layer present, skipping OCR" >&2
    echo "$PDF_PATH"
    exit 0
fi

if ! command -v ocrmypdf >/dev/null 2>&1; then
    echo "ocr-preflight: PDF has sparse text but ocrmypdf is not installed" >&2
    echo "ocr-preflight: install with 'brew install ocrmypdf' to enable OCR" >&2
    echo "$PDF_PATH"
    exit 0
fi

mkdir -p "$OUTPUT_DIR"
OCR_PATH="$OUTPUT_DIR/$(basename "${PDF_PATH%.pdf}")-ocr.pdf"

echo "ocr-preflight: running ocrmypdf -> $OCR_PATH" >&2
# Local modification: --skip-text so a born-digital PDF that already has a
# (sparse, sub-threshold) text layer doesn't abort with PriorOcrFoundError;
# only genuinely image-only pages get OCR'd.
ocrmypdf -l eng --deskew --rotate-pages --skip-text "$PDF_PATH" "$OCR_PATH" >&2

echo "$OCR_PATH"
