#!/usr/bin/env python3
"""
Turn a PDF into contact sheets: PNG grids of small page thumbnails, numbered,
so a 100+ page book can be reviewed at a glance.

    python3 scripts/contact-sheets.py walking-memories.pdf sheets/
    python3 scripts/contact-sheets.py book.pdf sheets/ --cols 8 --rows 4 --dpi 30

Facing pages are drawn as spreads (page 1 alone on the right, then 2|3, 4|5 ...),
the way the printed book is opened. Use --single for one thumbnail per cell.

Needs: pdftoppm (poppler-utils) and Pillow.
"""
import argparse, glob, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf"); ap.add_argument("outdir")
    ap.add_argument("--cols", type=int, default=4, help="cells per row (a cell is a spread, or a page with --single)")
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--dpi", type=int, default=36, help="thumbnail resolution")
    ap.add_argument("--single", action="store_true", help="one page per cell instead of spreads")
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", str(a.dpi), "-png", a.pdf, os.path.join(tmp, "p")], check=True)
        files = sorted(glob.glob(os.path.join(tmp, "p-*.png")))
        if not files:
            sys.exit("no pages rendered")
        pages = [Image.open(f).convert("RGB") for f in files]
        w, h = pages[0].size
        # cells: list of [(page_number, image), ...]
        if a.single:
            cells = [[(i + 1, im)] for i, im in enumerate(pages)]
        else:
            cells = [[(1, pages[0])]]                      # page 1 (cover) sits alone on the right
            rest = list(enumerate(pages[1:], start=2))
            cells += [rest[i:i + 2] for i in range(0, len(rest), 2)]
        pad, label_h = 8, 14
        cell_w = (2 * w if not a.single else w)
        per_sheet = a.cols * a.rows
        n_sheets = (len(cells) + per_sheet - 1) // per_sheet
        for s in range(n_sheets):
            chunk = cells[s * per_sheet:(s + 1) * per_sheet]
            sheet = Image.new("RGB", (a.cols * (cell_w + pad) + pad, a.rows * (h + label_h + pad) + pad), (228, 229, 225))
            d = ImageDraw.Draw(sheet)
            for k, cell in enumerate(chunk):
                x = pad + (k % a.cols) * (cell_w + pad)
                y = pad + (k // a.cols) * (h + label_h + pad)
                x0 = x + (w if (not a.single and len(cell) == 1 and cell[0][0] == 1) else 0)   # lone cover -> right half
                for j, (num, im) in enumerate(cell):
                    sheet.paste(im, (x0 + j * w, y + label_h))
                d.text((x, y), "–".join(str(n) for n, _ in cell), fill=(19, 19, 19))
            path = os.path.join(a.outdir, f"contact-sheet-{s + 1:02d}.png")
            sheet.save(path, optimize=True)
            print(path)
    print(f"{len(pages)} pages -> {n_sheets} sheet(s)")


if __name__ == "__main__":
    main()
