#!/bin/bash
# Academic PDF to Markdown — Main Orchestrator
#
# Usage: ./scripts/extract-pdf.sh <pdf_path> [output_dir] [--engine auto|docling|fast|math|poppler]
#
# Pipeline:
#   0. ocr-preflight.sh   — OCR the PDF if its text layer is sparse
#   1. detect-engine.py   — choose engine when --engine=auto (default)
#   2. dispatch:
#        docling  -> docling-extract.py        (MIT, layout model, balanced default)
#        fast     -> pymupdf4llm-extract.py    (AGPL, rule-based, no model load)
#        math     -> mineru-extract.sh         (Apache+thresholds, formula-strong)
#        poppler  -> extract-{text,pages,figures,tables}.sh  (GPL, no model fallback)
#   2b. if auto-chosen docling left equations undecoded, rerun the text with MinerU
#
# See README.md for licence and capability details on each engine.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The Python environment: $PDF2MD_VENV when set (a plugin install keeps it in the plugin's
# data folder, since the plugin folder is replaced on update), else .venv beside the skill.
VENV="${PDF2MD_VENV:-$SCRIPT_DIR/../.venv}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------

ENGINE="auto"
PDF_PATH=""
OUTPUT_DIR=""

while [ $# -gt 0 ]; do
    case "$1" in
        --engine)
            ENGINE="$2"
            shift 2
            ;;
        --engine=*)
            ENGINE="${1#--engine=}"
            shift
            ;;
        -h|--help)
            sed -n '2,18p' "$0"
            exit 0
            ;;
        *)
            if [ -z "$PDF_PATH" ]; then
                PDF_PATH="$1"
            elif [ -z "$OUTPUT_DIR" ]; then
                OUTPUT_DIR="$1"
            else
                echo -e "${RED}Unexpected argument: $1${NC}" >&2
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$PDF_PATH" ]; then
    echo -e "${RED}Usage: $0 <pdf_path> [output_dir] [--engine auto|docling|fast|math|poppler]${NC}" >&2
    exit 1
fi

if [ ! -f "$PDF_PATH" ]; then
    echo -e "${RED}Error: PDF file not found: $PDF_PATH${NC}" >&2
    exit 1
fi

ENGINE_REQUESTED="$ENGINE"
PDF_BASENAME="$(basename "$PDF_PATH" .pdf)"
PAPER_ID="$(echo "$PDF_BASENAME" | tr '[:upper:]' '[:lower:]' | sed 's/[[:space:]]/-/g' | sed 's/[^a-z0-9_-]//g')"
OUTPUT_DIR="${OUTPUT_DIR:-./output/$PAPER_ID}"

echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}Academic PDF to Markdown${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  PDF:       $PDF_PATH"
echo -e "  Paper ID:  $PAPER_ID"
echo -e "  Output:    $OUTPUT_DIR"
echo -e "  Engine:    $ENGINE (requested)"
echo ""

mkdir -p "$OUTPUT_DIR"

# ---------------------------------------------------------------------------
# Stage 0: OCR preflight (always runs — cheap when not needed)
# ---------------------------------------------------------------------------

echo -e "${BOLD}[Stage 0] OCR Preflight${NC}"
PDF_PATH="$(bash "$SCRIPT_DIR/ocr-preflight.sh" "$PDF_PATH" "$OUTPUT_DIR")"
echo -e "  Using PDF: $PDF_PATH"
echo ""

# ---------------------------------------------------------------------------
# Stage 1: Engine selection
# ---------------------------------------------------------------------------

if [ "$ENGINE" = "auto" ]; then
    echo -e "${BOLD}[Stage 1] Engine Detection${NC}"
    PY="python3"
    if [ -d "$VENV" ]; then PY="$VENV/bin/python"; fi
    ENGINE="$("$PY" "$SCRIPT_DIR/detect-engine.py" "$PDF_PATH")"
    echo -e "  Chosen engine: ${GREEN}$ENGINE${NC}"
    echo ""
fi

# ---------------------------------------------------------------------------
# Stage 2: Dispatch
# ---------------------------------------------------------------------------

run_in_venv() {
    if [ -d "$VENV" ]; then
        "$VENV/bin/python" "$@"
    else
        python3 "$@"
    fi
}

case "$ENGINE" in
    docling)
        echo -e "${BOLD}[Stage 2] Docling Extraction${NC}"
        run_in_venv "$SCRIPT_DIR/docling-extract.py" "$PDF_PATH" "$OUTPUT_DIR" "$PAPER_ID"
        ;;
    fast)
        echo -e "${BOLD}[Stage 2] pymupdf4llm Extraction (fast)${NC}"
        run_in_venv "$SCRIPT_DIR/pymupdf4llm-extract.py" "$PDF_PATH" "$OUTPUT_DIR" "$PAPER_ID"
        ;;
    math)
        echo -e "${BOLD}[Stage 2] MinerU Extraction (math-heavy)${NC}"
        bash "$SCRIPT_DIR/mineru-extract.sh" "$PDF_PATH" "$OUTPUT_DIR" "$PAPER_ID"
        ;;
    poppler)
        echo -e "${BOLD}[Stage 2] Poppler Fallback Pipeline${NC}"
        echo -e "${BOLD}  [1/4] Text${NC}"
        bash "$SCRIPT_DIR/extract-text.sh" "$PDF_PATH" "$OUTPUT_DIR" "$PAPER_ID"
        echo -e "${BOLD}  [2/4] Pages${NC}"
        bash "$SCRIPT_DIR/extract-pages.sh" "$PDF_PATH" "$OUTPUT_DIR" "$PAPER_ID"
        echo -e "${BOLD}  [3/4] Figures${NC}"
        bash "$SCRIPT_DIR/extract-figures.sh" "$PDF_PATH" "$OUTPUT_DIR" "$PAPER_ID"
        echo -e "${BOLD}  [4/4] Tables${NC}"
        bash "$SCRIPT_DIR/extract-tables.sh" "$PDF_PATH" "$OUTPUT_DIR" "$PAPER_ID"
        ;;
    *)
        echo -e "${RED}Unknown engine: $ENGINE${NC}" >&2
        echo -e "${RED}Valid: auto, docling, fast, math, poppler${NC}" >&2
        exit 1
        ;;
esac
echo ""

# ---------------------------------------------------------------------------
# Stage 2b: docling writes each displayed equation it cannot read as
# <!-- formula-not-decoded -->. If it left any and docling was auto-chosen, rerun
# with MinerU: its text and figures replace docling's, and docling's tables and
# page images stay. A run that asked for docling by name keeps docling's output.
# ---------------------------------------------------------------------------

FULLTEXT="$OUTPUT_DIR/${PAPER_ID}-fulltext.md"
ENGINE_LABEL="$ENGINE"

if [ "$ENGINE" = "docling" ] && [ -f "$FULLTEXT" ]; then
    FORMULA_GAPS=$( (grep -o 'formula-not-decoded' "$FULLTEXT" || true) | wc -l | tr -d ' ')
    if [ "$FORMULA_GAPS" -gt 0 ] && [ "$ENGINE_REQUESTED" = "docling" ]; then
        echo -e "${YELLOW}docling left $FORMULA_GAPS equation(s) as <!-- formula-not-decoded -->.${NC}"
        echo -e "${YELLOW}Kept, since --engine docling was given; re-run with --engine math for the equations.${NC}"
        echo ""
    elif [ "$FORMULA_GAPS" -gt 0 ]; then
        echo -e "${BOLD}[Stage 2b] MinerU re-run: docling left $FORMULA_GAPS equation(s) undecoded${NC}"
        RERUN_DIR="$OUTPUT_DIR/_math-rerun"
        rm -rf "$RERUN_DIR"
        if bash "$SCRIPT_DIR/mineru-extract.sh" "$PDF_PATH" "$RERUN_DIR" "$PAPER_ID"; then
            awk -v n="$FORMULA_GAPS" '
                NR > 1 && !done && /^---$/ {
                    print "rerun_from: \"docling, which left " n " equations undecoded; tables and pages from docling\""
                    done = 1
                }
                { print }' "$RERUN_DIR/${PAPER_ID}-fulltext.md" > "$FULLTEXT"
            rm -rf "$OUTPUT_DIR/figures" "$OUTPUT_DIR/_mineru"
            mv "$RERUN_DIR/figures" "$OUTPUT_DIR/figures"
            mv "$RERUN_DIR/_mineru" "$OUTPUT_DIR/_mineru"
            rm -rf "$RERUN_DIR"
            ENGINE_LABEL="math (MinerU, after docling left $FORMULA_GAPS equations undecoded)"
        else
            rm -rf "$RERUN_DIR"
            echo -e "${YELLOW}MinerU re-run failed: kept docling's output, in which $FORMULA_GAPS equation(s) are${NC}"
            echo -e "${YELLOW}<!-- formula-not-decoded -->. Fix the error above and re-run with --engine math.${NC}"
        fi
        echo ""
    fi
fi

# Page thumbnails — only docling generates them natively; supply via pdftoppm
# for fast/math/poppler engines so the output tree is consistent.
if [ "$ENGINE" != "docling" ] && [ "$ENGINE" != "poppler" ]; then
    if command -v pdftoppm >/dev/null 2>&1; then
        echo -e "${BOLD}[Stage 3] Page Thumbnails (pdftoppm)${NC}"
        bash "$SCRIPT_DIR/extract-pages.sh" "$PDF_PATH" "$OUTPUT_DIR" "$PAPER_ID"
        echo ""
    fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Extraction complete${NC} (engine: ${BOLD}$ENGINE_LABEL${NC})"
echo ""
echo -e "Output directory: ${BOLD}$OUTPUT_DIR${NC}"
echo ""

PAGE_COUNT=$(find "$OUTPUT_DIR/pages" -name "*.png" 2>/dev/null | wc -l | tr -d ' ')
FIG_COUNT=$(find "$OUTPUT_DIR/figures" \( -name "*.png" -o -name "*.jpg" \) 2>/dev/null | wc -l | tr -d ' ')
TABLE_COUNT=$(find "$OUTPUT_DIR/tables" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

echo -e "  Fulltext:  $([ -f "$FULLTEXT" ] && echo "✓" || echo "✗") $FULLTEXT"
echo -e "  Pages:     $PAGE_COUNT images"
echo -e "  Figures:   $FIG_COUNT images"
echo -e "  Tables:    $TABLE_COUNT tables"
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
