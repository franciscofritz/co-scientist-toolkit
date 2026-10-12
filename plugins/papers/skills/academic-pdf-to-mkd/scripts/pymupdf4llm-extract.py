"""Fast PDF→Markdown extraction via pymupdf4llm.

For born-digital papers with clean layout where Docling's model load time is
not worth paying. Produces the same output tree shape so downstream consumers
do not branch on engine.

Output:
  {output_dir}/{paper_id}-fulltext.md
  {output_dir}/figures/{paper_id}-figure-NN.png + .md
  (no tables/ — pymupdf4llm emits tables inline in the markdown)
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import pymupdf4llm
    import pymupdf
except ImportError:
    print(
        "Error: pymupdf4llm not installed. Install with: pip install pymupdf4llm",
        file=sys.stderr,
    )
    sys.exit(1)


def extract(pdf_path: str, output_dir: str, paper_id: str) -> None:
    out_dir = Path(output_dir)
    figures_dir = out_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    md_text = pymupdf4llm.to_markdown(
        pdf_path,
        write_images=True,
        image_path=str(figures_dir),
        image_format="png",
    )

    frontmatter = f'---\ntitle: "{paper_id}"\ntype: "paper-fulltext"\nengine: "pymupdf4llm"\n---\n\n'
    (out_dir / f"{paper_id}-fulltext.md").write_text(frontmatter + md_text, encoding="utf-8")

    # Rename pymupdf4llm's auto-named images to the skill's convention
    raw_images = sorted(figures_dir.glob("*.png"))
    skill_images = [p for p in raw_images if p.name.startswith(f"{paper_id}-figure-")]
    raw_only = [p for p in raw_images if p not in skill_images]
    for idx, img in enumerate(raw_only, start=1):
        padded = f"{idx:02d}"
        new_img = figures_dir / f"{paper_id}-figure-{padded}.png"
        img.rename(new_img)
        meta = figures_dir / f"{paper_id}-figure-{padded}.md"
        meta.write_text(
            f'---\ntype: figure\nfigure_id: "{padded}"\npaper_key: "{paper_id}"\n'
            f'image_file: "{new_img.name}"\ncaption: ""\nengine: "pymupdf4llm"\n---\n\n'
            f"# Figure {padded}\n\n## Caption\n(pymupdf4llm does not extract captions; "
            "see surrounding text in the fulltext markdown)\n\n## Description\nTODO: Describe figure\n",
            encoding="utf-8",
        )
    print(f"pymupdf4llm: wrote fulltext and {len(raw_only)} figures")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: pymupdf4llm-extract.py <pdf_path> <output_dir> <paper_id>", file=sys.stderr)
        sys.exit(1)
    extract(sys.argv[1], sys.argv[2], sys.argv[3])
