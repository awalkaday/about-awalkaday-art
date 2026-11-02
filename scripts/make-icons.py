#!/usr/bin/env python3
"""
Build the favicon / app-icon set and the web manifest from the awalkaday walker logo.

    python3 scripts/make-icons.py [--src .gitbook/assets/awalkaday-logo-1x1.png] [--out assets/icons]

Writes favicon.ico (16/32/48), icon-32.png, icon-180.png (apple-touch), icon-192.png, icon-512.png and
site.webmanifest. The logo is cropped to its drawing and centred on white with a margin, so it stays
readable at 16 px. Needs Pillow.
"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--src", default=".gitbook/assets/awalkaday-logo-1x1.png")
ap.add_argument("--out", default="assets/icons")
ap.add_argument("--background", default="#E4E5E1")
a = ap.parse_args()

src = Image.open(ROOT / a.src).convert("L")
bbox = ImageChops.invert(src).point(lambda v: 255 if v > 40 else 0).getbbox()
art = src.crop(bbox)
side = max(art.size)
out = ROOT / a.out; out.mkdir(parents=True, exist_ok=True)


def canvas(px, margin=0.12):
    inner = int(px * (1 - 2 * margin))
    im = art.copy(); im.thumbnail((inner, inner), Image.LANCZOS)
    c = Image.new("RGB", (px, px), "white")
    c.paste(Image.merge("RGB", (im, im, im)), ((px - im.width) // 2, (px - im.height) // 2))
    return c


for px, name in ((32, "icon-32.png"), (180, "icon-180.png"), (192, "icon-192.png"), (512, "icon-512.png")):
    canvas(px, 0.08 if px <= 32 else 0.14).save(out / name, optimize=True)
canvas(48, 0.06).save(out / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
(out / "site.webmanifest").write_text(json.dumps({
    "name": "Walking Memories", "short_name": "Walking Memories",
    "description": "Open-source artist's book by Chris-Armel Iradukunda (daqhris)",
    "start_url": "/", "display": "browser",
    "background_color": "#FBFBF9", "theme_color": a.background,
    "icons": [{"src": "/assets/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
              {"src": "/assets/icons/icon-512.png", "sizes": "512x512", "type": "image/png"}],
}, indent=2) + "\n", encoding="utf-8")
print("wrote", ", ".join(sorted(p.name for p in out.iterdir())))
