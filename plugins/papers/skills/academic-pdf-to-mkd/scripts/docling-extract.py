import sys
import os
import json
from pathlib import Path

# Provide pip module feedback if missing
try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.base_models import InputFormat
    from docling_core.types.doc.document import PictureItem, TableItem
except ImportError:
    print("Error: docling not installed. Please install docling inside virtual environment.", file=sys.stderr)
    sys.exit(1)

def _save_pil(img_obj, dest_path):
    """Persist a docling image to PNG. Newer docling exposes .pil_image;
    older returns a PIL.Image directly."""
    pil = getattr(img_obj, "pil_image", None) or img_obj
    pil.save(dest_path, format="PNG")


def _resolve_captions(item, doc) -> str:
    """Resolve item.captions, which may be RefItem references (newer docling)
    or item objects with a .text attribute (older docling)."""
    parts = []
    for cap in getattr(item, "captions", None) or []:
        text = None
        # Newer Docling: RefItem with .resolve(doc) -> TextItem
        if hasattr(cap, "resolve"):
            try:
                resolved = cap.resolve(doc)
                text = getattr(resolved, "text", None)
            except Exception:
                text = None
        # Older Docling: object already has .text
        if text is None:
            text = getattr(cap, "text", None)
        if text:
            parts.append(text)
    return ". ".join(parts)


# Minimum image dimension for a PictureItem to count as a real figure.
# Below this we treat it as formatting noise (publisher logo, CC-BY badge, decorative icon, etc.)
MIN_PICTURE_DIM_PX = 80
MIN_PICTURE_BYTES = 4096   # also drop trivially small encoded files


def extract_pdf(pdf_path, output_dir, paper_id):
    out_dir = Path(output_dir)
    pages_dir = out_dir / "pages"
    figures_dir = out_dir / "figures"
    tables_dir = out_dir / "tables"

    # Create directories
    for d in [out_dir, pages_dir, figures_dir, tables_dir]:
        d.mkdir(parents=True, exist_ok=True)

    print(f"Loading document: {pdf_path}")
    
    # Configure pipeline settings
    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = 2.0
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True
    # pipeline_options.generate_table_images = True # Optional, could add later

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    result = doc_converter.convert(pdf_path)
    doc = result.document

    print(f"Extraction completed. Saving files to {out_dir}")

    # 1. Save Markdown Fulltext
    md_content = doc.export_to_markdown()
    md_file = out_dir / f"{paper_id}-fulltext.md"
    
    # Add simple YAML frontmatter
    frontmatter = f"---\ntitle: \"{paper_id}\"\ntype: \"paper-fulltext\"\n---\n\n"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(frontmatter + md_content)
    print(f"Saved: {md_file.name}")

    # 2. Iterate items to save pictures and tables
    fig_idx = 1
    table_idx = 1

    for item, _level in doc.iterate_items():
        if isinstance(item, PictureItem):
            if hasattr(item, "image") and item.image is not None:
                # Filter formatting noise: tiny pictures (publisher logos, CC-BY badges, icons).
                pil = getattr(item.image, "pil_image", None) or item.image
                w, h = getattr(pil, "size", (0, 0))
                if w < MIN_PICTURE_DIM_PX or h < MIN_PICTURE_DIM_PX:
                    print(f"Skipped tiny picture ({w}x{h} < {MIN_PICTURE_DIM_PX}px)")
                    continue

                # Save to a temp buffer first so we can size-check the encoded file too.
                from io import BytesIO
                buf = BytesIO()
                pil.save(buf, format="PNG")
                if buf.tell() < MIN_PICTURE_BYTES:
                    print(f"Skipped tiny picture ({buf.tell()} bytes < {MIN_PICTURE_BYTES})")
                    continue

                padded = f"{fig_idx:02d}"
                fig_img_file = figures_dir / f"{paper_id}-figure-{padded}.png"
                fig_md_file = figures_dir / f"{paper_id}-figure-{padded}.md"

                with open(fig_img_file, "wb") as f:
                    f.write(buf.getvalue())

                # Create metadata md
                fig_caption = _resolve_captions(item, doc)

                md_content = f"---\ntype: figure\nfigure_id: \"{padded}\"\npaper_key: \"{paper_id}\"\nimage_file: \"{fig_img_file.name}\"\ncaption: \"{fig_caption}\"\n---\n\n# Figure {padded}\n\n## Caption\n{fig_caption}\n\n## Description\nTODO: Describe figure\n"
                with open(fig_md_file, "w", encoding="utf-8") as f:
                    f.write(md_content)

                print(f"Saved: {fig_img_file.name}")
                fig_idx += 1
                
        elif isinstance(item, TableItem):
            padded = f"{table_idx:02d}"
            table_md_file = tables_dir / f"{paper_id}-table-{padded}.md"
            table_csv_file = tables_dir / f"{paper_id}-table-{padded}.csv"
            
            # Save CSV
            df = item.export_to_dataframe()
            df.to_csv(table_csv_file, index=False)
            
            # Create Metadata MD
            table_caption = _resolve_captions(item, doc)
                
            md_table = item.export_to_markdown()
            md_content = f"---\ntype: table\ntable_id: \"{padded}\"\npaper_key: \"{paper_id}\"\ndata_file: \"{table_csv_file.name}\"\ncaption: \"{table_caption}\"\n---\n\n# Table {padded}\n\n## Caption\n{table_caption}\n\n## Data\n\n{md_table}\n"
            
            with open(table_md_file, "w", encoding="utf-8") as f:
                f.write(md_content)
                
            print(f"Saved: {table_csv_file.name}")
            table_idx += 1

    # 3. Save Pages — handle both dict (older) and list (newer) APIs
    if hasattr(result, "pages") and result.pages:
        page_iter = result.pages.items() if hasattr(result.pages, "items") else enumerate(result.pages, start=1)
        saved = 0
        for p_idx, page in page_iter:
            if hasattr(page, "image") and page.image is not None:
                padded = f"{p_idx:03d}"
                page_img_file = pages_dir / f"page-{padded}.png"
                _save_pil(page.image, page_img_file)
                saved += 1
        print(f"Saved {saved} page images.")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python docling-extract.py <pdf_path> <output_dir> <paper_id>")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2]
    paper_id = sys.argv[3]
    
    extract_pdf(pdf_path, output_dir, paper_id)
