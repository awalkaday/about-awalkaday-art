#!/usr/bin/env python3
"""
Shrink oversized images under .gitbook/assets (phone photos, screenshots) so the
screen book and the print book stop carrying 5 MB files that are shown at ~190 px.

    python3 scripts/shrink-assets.py             # report only
    python3 scripts/shrink-assets.py --apply     # replace in place, same file names
    python3 scripts/shrink-assets.py --max-px 1600 --min-kb 300 --apply

Originals are copied to .photo-cache/gitbook/ (git-ignored) first, and stay in git
history, so nothing is lost. JPEGs keep their name; PNGs are only touched when they
are larger than --max-px (they may be logos with transparency).
Needs Pillow.
"""
import argparse, shutil
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--dir", default=".gitbook/assets")
ap.add_argument("--max-px", type=int, default=1600)
ap.add_argument("--min-kb", type=int, default=300, help="leave files smaller than this alone")
ap.add_argument("--quality", type=int, default=85)
ap.add_argument("--cache", default=".photo-cache/gitbook")
ap.add_argument("--apply", action="store_true")
a = ap.parse_args()

total_before = total_after = 0
for p in sorted((ROOT / a.dir).iterdir()):
    if p.suffix.lower() not in (".jpg", ".jpeg", ".png") or p.stat().st_size < a.min_kb * 1024:
        continue
    with Image.open(p) as im:
        im = ImageOps.exif_transpose(im)             # phone photos: bake the rotation in
        w, h = im.size
        is_png = p.suffix.lower() == ".png"
        if max(w, h) <= a.max_px:
            continue
        before = p.stat().st_size
        im.thumbnail((a.max_px, a.max_px), Image.LANCZOS)
        print(f"{p.name}: {w}x{h} {before//1024} KB -> {im.size[0]}x{im.size[1]}", end="")
        if a.apply:
            cache = ROOT / a.cache; cache.mkdir(parents=True, exist_ok=True)
            if not (cache / p.name).exists():
                shutil.copy2(p, cache / p.name)
            if is_png:
                im.save(p, "PNG", optimize=True)
            else:
                im.convert("RGB").save(p, "JPEG", quality=a.quality, optimize=True, progressive=True)
            after = p.stat().st_size
            print(f" {after//1024} KB")
            total_before += before; total_after += after
        else:
            print("  (dry run)")
if a.apply:
    print(f"saved {(total_before - total_after)//1024} KB")
