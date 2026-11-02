#!/usr/bin/env python3
"""
Point every web page's canonical link at the GitBook edition (book.awalkaday.art) while both sites exist.

    python3 scripts/set-canonical.py            # add / refresh  canonical_url: ...  in each page's front matter
    python3 scripts/set-canonical.py --check    # list pages whose canonical_url is missing or different (exit 1)
    python3 scripts/set-canonical.py --remove   # take the lines out again (the day printlab takes over)
    python3 scripts/set-canonical.py --host https://example.org

GitBook addresses follow the file path: index.md -> /, folder/README.md -> /folder,
folder/page.md -> /folder/page. jekyll-seo-tag reads `canonical_url` from the front matter.
The default host is canonical_host in _data/seo.yml. impression.md (noindex) is left alone.
"""
import argparse, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"_chapters", "node_modules", "vendor", ".git", ".github", ".photo-cache", "scripts", "_site", "docs", "_data", "_includes", "_layouts"}
SKIP_FILES = {"README.md", "README-lab.md", "SUMMARY.md", "impression.md"}

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--host")
ap.add_argument("--check", action="store_true")
ap.add_argument("--remove", action="store_true")
a = ap.parse_args()
host = a.host or re.search(r'canonical_host:\s*"?([^"\s]+)', (ROOT / "_data" / "seo.yml").read_text(encoding="utf-8")).group(1)
host = host.rstrip("/")


def pages():
    for f in sorted(ROOT.rglob("*.md")):
        rel = f.relative_to(ROOT)
        if rel.parts[0] in SKIP_DIRS or (len(rel.parts) == 1 and rel.name in SKIP_FILES):
            continue
        yield f, rel


def target(rel):
    p = rel.with_suffix("").as_posix()
    if p == "index":
        return host + "/"
    if p.endswith("/README"):
        p = p[: -len("/README")]
    return f"{host}/{p}"


bad, changed = [], 0
for f, rel in pages():
    text = f.read_text(encoding="utf-8")
    bom = text.startswith("﻿")
    body = text.lstrip("﻿")
    m = re.match(r"---\r?\n(.*?)\r?\n---", body, re.S)
    if not m:
        print("no front matter:", rel); continue
    fm = m.group(1)
    cur = re.search(r"^canonical_url:\s*\"?([^\"\r\n]+)\"?\s*$", fm, re.M)
    want = target(rel)
    if a.check:
        if not cur or cur.group(1) != want:
            bad.append(f"{rel}: {cur.group(1) if cur else '(none)'} -> {want}")
        continue
    nl = "\r\n" if "\r\n" in m.group(0) else "\n"
    fm2 = re.sub(r"^canonical_url:.*\r?\n?", "", fm + nl, flags=re.M).rstrip("\r\n")
    if not a.remove:
        fm2 += f'{nl}canonical_url: "{want}"'
    if fm2 != fm:
        new = "---" + nl + fm2 + nl + "---" + body[m.end():]
        f.write_text(("﻿" if bom else "") + new, encoding="utf-8"); changed += 1
if a.check:
    print("\n".join(bad) or "all canonical links as expected"); sys.exit(1 if bad else 0)
print(f"{'removed from' if a.remove else 'set on'} {changed} page(s); host {host}")
