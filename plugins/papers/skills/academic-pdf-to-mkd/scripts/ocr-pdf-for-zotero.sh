#!/bin/bash
# Build a Zotero-ready searchable PDF.
#
# Usage:
#   ./scripts/ocr-pdf-for-zotero.sh <pdf_path> [output_pdf] [--split-spreads] [--no-compress]
#
# This is the PDF handoff branch of the skill: it repairs scan-only PDFs for
# Zotero while keeping the deliverable as a PDF rather than Markdown.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The Python environment: $PDF2MD_VENV when set (a plugin install keeps it in the plugin's
# data folder, since the plugin folder is replaced on update), else .venv beside the skill.
VENV="${PDF2MD_VENV:-$SCRIPT_DIR/../.venv}"

PDF_PATH=""
OUTPUT_PDF=""
SPLIT_SPREADS=0
COMPRESS=1

usage() {
    cat <<'EOF'
Usage: ./scripts/ocr-pdf-for-zotero.sh <pdf_path> [output_pdf] [--split-spreads] [--no-compress]

Build a Zotero-ready searchable PDF. Use --split-spreads when one scanned PDF
page contains two printed pages.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --split-spreads)
            SPLIT_SPREADS=1
            shift
            ;;
        --no-compress)
            COMPRESS=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            if [ -z "$PDF_PATH" ]; then
                PDF_PATH="$1"
            elif [ -z "$OUTPUT_PDF" ]; then
                OUTPUT_PDF="$1"
            else
                echo "Unexpected argument: $1" >&2
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$PDF_PATH" ]; then
    usage >&2
    exit 1
fi

if [ ! -f "$PDF_PATH" ]; then
    echo "PDF file not found: $PDF_PATH" >&2
    exit 1
fi

if ! command -v pdftotext >/dev/null 2>&1; then
    echo "pdftotext is required; install poppler with 'brew install poppler'" >&2
    exit 1
fi

if ! command -v pdftoppm >/dev/null 2>&1; then
    echo "pdftoppm is required; install poppler with 'brew install poppler'" >&2
    exit 1
fi

if ! command -v ocrmypdf >/dev/null 2>&1; then
    echo "ocrmypdf is required; install with 'brew install ocrmypdf'" >&2
    exit 1
fi

PDF_BASENAME="$(basename "$PDF_PATH" .pdf)"
PAPER_ID="$(echo "$PDF_BASENAME" | tr '[:upper:]' '[:lower:]' | sed 's/[[:space:]]/-/g' | sed 's/[^a-z0-9_-]//g')"
OUTPUT_PDF="${OUTPUT_PDF:-./output/$PAPER_ID/${PAPER_ID}-zotero.pdf}"
OUTPUT_DIR="$(dirname "$OUTPUT_PDF")"
WORK_DIR="$OUTPUT_DIR/zotero-ocr-work"
PREVIEW_DIR="$OUTPUT_DIR/previews"
mkdir -p "$WORK_DIR" "$PREVIEW_DIR"

PY="${PYTHON:-python3}"
if [ -d "$VENV" ]; then
    PY="$VENV/bin/python"
fi

WORD_COUNT=$(pdftotext -layout "$PDF_PATH" - 2>/dev/null | wc -w | tr -d ' ')
echo "zotero-ocr: source word count = $WORD_COUNT"

OCR_PDF="$WORK_DIR/${PAPER_ID}-ocr.pdf"
echo "zotero-ocr: running OCRmyPDF -> $OCR_PDF"
ocrmypdf -l eng --deskew --rotate-pages --rotate-pages-threshold 1 --output-type pdf "$PDF_PATH" "$OCR_PDF"

COPYFIX_PDF="$WORK_DIR/${PAPER_ID}-copyfixed.pdf"
SPLIT_ARGS=()
if [ "$SPLIT_SPREADS" -eq 1 ]; then
    SPLIT_ARGS=(--split-spreads)
fi

echo "zotero-ocr: rebuilding copy-friendly text layer -> $COPYFIX_PDF"
"$PY" "$SCRIPT_DIR/split-copyfriendly-ocr-pdf.py" "$OCR_PDF" "$COPYFIX_PDF" ${SPLIT_ARGS[@]+"${SPLIT_ARGS[@]}"}

if [ "$COMPRESS" -eq 1 ] && command -v gs >/dev/null 2>&1; then
    COMPRESSED_PDF="$WORK_DIR/${PAPER_ID}-copyfixed-compressed.pdf"
    echo "zotero-ocr: compressing -> $COMPRESSED_PDF"
    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 -dPDFSETTINGS=/ebook \
        -dNOPAUSE -dQUIET -dBATCH \
        -sOutputFile="$COMPRESSED_PDF" "$COPYFIX_PDF"
    cp "$COMPRESSED_PDF" "$OUTPUT_PDF"
else
    cp "$COPYFIX_PDF" "$OUTPUT_PDF"
fi

FINAL_WORD_COUNT=$(pdftotext "$OUTPUT_PDF" - 2>/dev/null | wc -w | tr -d ' ')
PAGE_COUNT=$(pdfinfo "$OUTPUT_PDF" 2>/dev/null | awk -F: '/^Pages:/ {gsub(/ /, "", $2); print $2}')

echo "zotero-ocr: rendering preview pages"
pdftoppm -png -f 1 -l 1 -r 100 "$OUTPUT_PDF" "$PREVIEW_DIR/page" >/dev/null 2>&1 || true
if [ -n "${PAGE_COUNT:-}" ] && [ "$PAGE_COUNT" -gt 1 ]; then
    pdftoppm -png -f "$PAGE_COUNT" -l "$PAGE_COUNT" -r 100 "$OUTPUT_PDF" "$PREVIEW_DIR/page" >/dev/null 2>&1 || true
fi

echo "zotero-ocr: output = $OUTPUT_PDF"
echo "zotero-ocr: pages = ${PAGE_COUNT:-unknown}"
echo "zotero-ocr: extractable words = $FINAL_WORD_COUNT"
echo "zotero-ocr: sample text:"
pdftotext -raw -f 1 -l 1 "$OUTPUT_PDF" - 2>/dev/null | sed -n '1,12p'
