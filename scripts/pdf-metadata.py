#!/usr/bin/env python3
"""
Write proper document metadata into the PDF Chromium produced (it only knows the <title>).

    python3 scripts/pdf-metadata.py out/walking-memories.pdf [--out other.pdf]

Sets Title, Author, Subject, Keywords, Creator, a License entry, the document language (/Lang) and
"display the title in the window bar". Tags and bookmarks come from make-pdf.js (tagged + outline) and are kept.
Values are read from _config.yml and below. Needs pypdf (pip install pypdf).
"""
import argparse, re
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, DictionaryObject, NameObject, TextStringObject

ROOT = Path(__file__).resolve().parent.parent
cfg = (ROOT / "_config.yml").read_text(encoding="utf-8-sig")
get = lambda k: re.search(rf'^{k}:\s*"([^"]*)"', cfg, re.M).group(1)

ap = argparse.ArgumentParser()
ap.add_argument("pdf")
ap.add_argument("--out")
a = ap.parse_args()

reader = PdfReader(a.pdf)
w = PdfWriter(clone_from=reader)
w.add_metadata({
    "/Title": get("title"),
    "/Author": "Chris-Armel Iradukunda (daqhris)",
    "/Subject": get("description"),
    "/Keywords": "artist's book, photography, walking, Belgium, Ethereum, Arweave, open source, awalkaday, daqhris, Walking Memories",
    "/Creator": "printlab.awalkaday.art (Jekyll, Paged.js, Chromium)",
    "/License": "Photos and writings CC BY-NC-ND 4.0 (https://creativecommons.org/licenses/by-nc-nd/4.0/); source code EUPL-1.2",
    "/Source": "https://printlab.awalkaday.art/",
})
root = w._root_object
root[NameObject("/Lang")] = TextStringObject("en")
vp = root.get("/ViewerPreferences") or DictionaryObject()
vp[NameObject("/DisplayDocTitle")] = BooleanObject(True)
root[NameObject("/ViewerPreferences")] = vp
out = a.out or a.pdf
tmp = out + ".tmp"
with open(tmp, "wb") as f:
    w.write(f)
Path(tmp).replace(out)
r2 = PdfReader(out)
print(f"{out}: {len(r2.pages)} pages | tagged: {'/StructTreeRoot' in r2.trailer['/Root']} | "
      f"bookmarks: {len(r2.outline)} | lang: {r2.trailer['/Root'].get('/Lang')} | title: {r2.metadata.title}")
