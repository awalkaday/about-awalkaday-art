#!/usr/bin/env python3
"""
Make the 1200x630 social-sharing card (Open Graph / Twitter) from page 1 of the PDF.

    python3 scripts/make-share-image.py walking-memories.pdf [--out assets/social/share-1200x630.png]

The cover square (full height) is centred on the cover's board colour. Needs poppler (pdftoppm) and Pillow.
"""
import argparse, subprocess, tempfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("pdf")
ap.add_argument("--out", default="assets/social/share-1200x630.png")
ap.add_argument("--board", default="#E4E5E1")
a = ap.parse_args()
with tempfile.TemporaryDirectory() as d:
    subprocess.check_call(["pdftoppm", "-f", "1", "-l", "1", "-scale-to", "630", "-png", a.pdf, f"{d}/p"])
    cover = Image.open(next(Path(d).glob("p*.png"))).convert("RGB")
card = Image.new("RGB", (1200, 630), a.board)
card.paste(cover, ((1200 - cover.width) // 2, (630 - cover.height) // 2))
out = ROOT / a.out; out.parent.mkdir(parents=True, exist_ok=True)
card.save(out, optimize=True)
print("wrote", out.relative_to(ROOT), out.stat().st_size // 1024, "KB")
