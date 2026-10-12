#!/usr/bin/env python3
"""Rebuild OCR PDFs for copy/paste and optional two-up spread splitting.

The source PDF should already have a usable OCR layer. This script reuses
Poppler's line-level bounding boxes, redraws the scanned page image, and writes
whole-line invisible text. That fixes many viewer copy/paste failures caused by
tightly positioned OCR fragments.
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

FONT_NAME = "Helvetica"
RENDER_DPI = 220
Image = None
ImageReader = None
PdfReader = None
canvas = None
stringWidth = None


def load_pdf_deps() -> None:
    global Image, ImageReader, PdfReader, canvas, stringWidth

    if Image is not None:
        return

    try:
        from PIL import Image as pil_image
        from pypdf import PdfReader as pypdf_reader
        from reportlab.lib.utils import ImageReader as reportlab_image_reader
        from reportlab.pdfbase.pdfmetrics import stringWidth as reportlab_string_width
        from reportlab.pdfgen import canvas as reportlab_canvas
    except ImportError as exc:
        raise SystemExit(
            "Missing Python PDF dependencies. Install the skill's Python environment as "
            "described under Prerequisites in SKILL.md and set PDF2MD_VENV to it, "
            "or install pillow, pypdf, and reportlab in the active Python."
        ) from exc

    Image = pil_image
    ImageReader = reportlab_image_reader
    PdfReader = pypdf_reader
    canvas = reportlab_canvas
    stringWidth = reportlab_string_width


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def render_pages(source_pdf: Path, out_dir: Path) -> list[Path]:
    prefix = out_dir / "page"
    run(["pdftoppm", "-png", "-r", str(RENDER_DPI), str(source_pdf), str(prefix)])
    return sorted(out_dir.glob("page-*.png"))


def page_sizes(source_pdf: Path) -> list[tuple[float, float]]:
    load_pdf_deps()
    reader = PdfReader(str(source_pdf))
    return [(float(page.mediabox.width), float(page.mediabox.height)) for page in reader.pages]


def extract_layout_lines(source_pdf: Path) -> list[list[dict[str, float | str]]]:
    result = run(["pdftotext", "-bbox-layout", str(source_pdf), "-"])
    root = ET.fromstring(result.stdout)
    pages: list[list[dict[str, float | str]]] = []

    for page in (element for element in root.iter() if local_name(element.tag) == "page"):
        page_lines: list[dict[str, float | str]] = []
        for line in (element for element in page.iter() if local_name(element.tag) == "line"):
            words = [
                "".join(word.itertext()).strip()
                for word in line
                if local_name(word.tag) == "word" and "".join(word.itertext()).strip()
            ]
            if not words:
                continue
            x_min = float(line.attrib["xMin"])
            y_min = float(line.attrib["yMin"])
            x_max = float(line.attrib["xMax"])
            y_max = float(line.attrib["yMax"])
            page_lines.append(
                {
                    "text": " ".join(words),
                    "left": x_min,
                    "top": y_min,
                    "width": x_max - x_min,
                    "height": y_max - y_min,
                    "center": (x_min + x_max) / 2,
                }
            )
        pages.append(page_lines)

    return pages


def draw_invisible_line(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    font_size: float,
) -> None:
    if stringWidth(text, FONT_NAME, font_size) <= 0:
        return
    text_object = pdf.beginText()
    text_object.setTextRenderMode(3)
    text_object.setFont(FONT_NAME, font_size)
    text_object.setTextOrigin(x, y)
    text_object.textLine(text)
    pdf.drawText(text_object)


def draw_lines(
    pdf: canvas.Canvas,
    lines: list[dict[str, float | str]],
    page_height: float,
    x_offset: float = 0,
) -> None:
    for line in lines:
        text = str(line["text"])
        x = float(line["left"]) - x_offset
        line_height = float(line["height"])
        y = page_height - float(line["top"]) - (line_height * 0.88)
        target_width = float(line["width"])
        width_at_one_point = stringWidth(text, FONT_NAME, 1)
        fit_size = (target_width / width_at_one_point) * 0.98 if width_at_one_point else line_height
        font_size = max(2.5, min(14.0, line_height * 0.95, fit_size))
        draw_invisible_line(pdf, text, x, y, font_size)


def draw_image_page(
    pdf: canvas.Canvas,
    image_path: Path,
    page_width: float,
    page_height: float,
) -> None:
    pdf.setPageSize((page_width, page_height))
    pdf.drawImage(ImageReader(str(image_path)), 0, 0, width=page_width, height=page_height)


def draw_half_page(
    pdf: canvas.Canvas,
    image_path: Path,
    crop_box: tuple[int, int, int, int],
    lines: list[dict[str, float | str]],
    source_width: float,
    page_height: float,
    x_offset: float,
) -> None:
    half_width = source_width / 2
    with Image.open(image_path) as image:
        cropped = image.crop(crop_box)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_image:
            cropped.save(temp_image.name)
            cropped_path = Path(temp_image.name)

    try:
        draw_image_page(pdf, cropped_path, half_width, page_height)
    finally:
        cropped_path.unlink(missing_ok=True)

    draw_lines(pdf, lines, page_height, x_offset=x_offset)
    pdf.showPage()


def build_pdf(source_pdf: Path, output_pdf: Path, split_spreads: bool) -> None:
    load_pdf_deps()
    with tempfile.TemporaryDirectory(prefix="copyfriendly-ocr-") as temp_name:
        temp_dir = Path(temp_name)
        image_paths = render_pages(source_pdf, temp_dir)
        sizes = page_sizes(source_pdf)
        layout_pages = extract_layout_lines(source_pdf)

        if len(image_paths) != len(sizes) or len(layout_pages) != len(sizes):
            raise RuntimeError(
                f"Found {len(image_paths)} images and {len(layout_pages)} text pages for {len(sizes)} PDF pages"
            )

        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf = canvas.Canvas(str(output_pdf))
        suffix = "split" if split_spreads else "copyfriendly"
        pdf.setTitle(f"{source_pdf.stem}-{suffix}")
        pdf.setSubject("OCR text layer repaired for copy/paste")

        written_pages = 0
        for index, (image_path, (page_width, page_height), lines) in enumerate(
            zip(image_paths, sizes, layout_pages), 1
        ):
            if not split_spreads:
                draw_image_page(pdf, image_path, page_width, page_height)
                draw_lines(pdf, lines, page_height)
                pdf.showPage()
                written_pages += 1
                print(f"page {index}: {len(lines)} text lines")
                continue

            split_x = page_width / 2
            left_lines = [line for line in lines if float(line["center"]) < split_x]
            right_lines = [line for line in lines if float(line["center"]) >= split_x]

            with Image.open(image_path) as image:
                image_split_x = image.width // 2
                image_height = image.height
                image_width = image.width

            draw_half_page(
                pdf,
                image_path,
                (0, 0, image_split_x, image_height),
                left_lines,
                page_width,
                page_height,
                0,
            )
            written_pages += 1

            if right_lines:
                draw_half_page(
                    pdf,
                    image_path,
                    (image_split_x, 0, image_width, image_height),
                    right_lines,
                    page_width,
                    page_height,
                    split_x,
                )
                written_pages += 1

            print(f"spread {index}: left {len(left_lines)} lines, right {len(right_lines)} lines")

        pdf.save()
        print(f"wrote {written_pages} PDF pages")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_pdf", type=Path)
    parser.add_argument("output_pdf", type=Path)
    parser.add_argument(
        "--split-spreads",
        action="store_true",
        help="Split two-up scanned spreads into one printed page per PDF page.",
    )
    args = parser.parse_args()
    build_pdf(args.source_pdf, args.output_pdf, split_spreads=args.split_spreads)


if __name__ == "__main__":
    main()
