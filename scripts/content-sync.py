#!/usr/bin/env python3
"""
Keep the three copies of the text honest:  GitBook (branch `book`)  ->  web pages  ->  print chapters.

    python3 scripts/content-sync.py incoming [--ref origin/book] [--patch]
        What GitBook changed since the last time `book` was merged into this branch, which web
        page and print chapter each change belongs to, and whether we also edited that page
        here (= a merge conflict is likely).  --patch prints the GitBook-side diffs.

    python3 scripts/content-sync.py drift [--min 0.98] [--diff CHAPTER]
        How far each print chapter (_chapters/*.md) has drifted from its web page.
        1.00 = same text.  Photos and front matter are ignored.  --diff shows the lines.

    python3 scripts/content-sync.py toc
        Cross-checks SUMMARY.md (GitBook's table of contents), _data/toc.yml (the web menu),
        data/chapters-map.csv and impression.md (what the PDF includes).

The page <-> chapter map lives in data/chapters-map.csv. Standard library only.
"""
import argparse, csv, difflib, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout


def chapter_map():
    with (ROOT / "data" / "chapters-map.csv").open(newline="", encoding="utf-8") as f:
        return [(r["chapter"], r["web_page"]) for r in csv.DictReader(f)]


def body_lines(text):
    text = re.sub(r"\A﻿?---.*?---\n", "", text.replace("\r\n", "\n"), count=1, flags=re.S)
    text = re.sub(r"<img[^>]*>", "<img>", text)               # photo paths differ by design
    return [l.strip() for l in text.split("\n") if l.strip()]


def cmd_incoming(a):
    base = git("merge-base", "HEAD", a.ref).strip()
    if not base:
        sys.exit(f"no common history with {a.ref} (shallow clone? run: git fetch --unshallow)")
    n = git("rev-list", "--count", f"{base}..{a.ref}").strip()
    last = git("log", "-1", "--format=%h %ad %s", "--date=short", base).strip()
    print(f"last import point : {last}\nnew on {a.ref}: {n} commit(s)")
    theirs = {l for l in git("diff", "--name-only", base, a.ref).split("\n") if l}
    ours = {l for l in git("diff", "--name-only", base, "HEAD").split("\n") if l}
    by_page = {w: c for c, w in chapter_map()}
    if not theirs:
        print("nothing to import."); return
    print(f"\n{'GitBook changed':45} {'print chapter':28} here too?")
    for f in sorted(theirs):
        stat = git("diff", "--numstat", base, a.ref, "--", f).split()
        chap = by_page.get(f, "-" if f.endswith(".md") else "(asset)")
        flag = "CONFLICT LIKELY" if f in ours else ""
        print(f"{f:45} {chap:28} +{stat[0]}/-{stat[1]} {flag}")
        if a.patch:
            print(git("diff", base, a.ref, "--", f))
    print("\nHow to import: git merge", a.ref, "-> for each conflicted page keep OUR version and port the\n"
          "wording changes by hand (GitBook syntax differs), then repeat in _chapters/<chapter>.md if it applies.")


def cmd_drift(a):
    rows = []
    for c, w in chapter_map():
        cp, wp = ROOT / "_chapters" / f"{c}.md", ROOT / w
        if not cp.exists() or not wp.exists():
            rows.append((0.0, c, w, "missing")); continue
        A, B = body_lines(cp.read_text(encoding="utf-8")), body_lines(wp.read_text(encoding="utf-8"))
        if a.diff == c:
            print("\n".join(difflib.unified_diff(B, A, f"web:{w}", f"print:_chapters/{c}.md", lineterm="", n=1)))
            return
        rows.append((difflib.SequenceMatcher(None, A, B, autojunk=False).ratio(), c, w, ""))
    for r, c, w, note in sorted(rows):
        if r < a.min:
            print(f"{r:5.2f}  {c:30} <- {w} {note}")
    print(f"\n{sum(1 for r in rows if r[0] < a.min)} of {len(rows)} chapters differ from their web page by more than {round((1-a.min)*100)}%")


def cmd_toc(a):
    summary = set(re.findall(r"\]\(([^)]+\.md)\)", (ROOT / "SUMMARY.md").read_text(encoding="utf-8")))
    toc = set(re.findall(r"url:\s*(\S+)", (ROOT / "_data" / "toc.yml").read_text(encoding="utf-8")))
    mapped = {w for _, w in chapter_map()}
    imp = (ROOT / "impression.md").read_text(encoding="utf-8")
    included = set(re.findall(r"include_relative _chapters/([\w\-]+)\.md", imp))
    pages = {p for p in summary}
    print("SUMMARY.md pages not in chapters-map:", sorted(p for p in pages if p not in mapped and p != "README.md") or "none")
    print("chapters-map pages not in SUMMARY.md:", sorted(mapped - pages) or "none")
    slug = lambda p: re.sub(r"(/README)?\.md$", "", p) if p != "README.md" else "/"
    print("SUMMARY.md pages missing from _data/toc.yml:", sorted(p for p in pages if slug(p) not in {t.strip("/") or "/" for t in toc} and slug(p) != "/") or "none")
    print("chapters in the map but not printed (impression.md):", sorted({c for c, _ in chapter_map()} - included) or "none")
    print("chapters printed but not in the map:", sorted(included - {c for c, _ in chapter_map()}) or "none")


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = ap.add_subparsers(dest="cmd", required=True)
p = sub.add_parser("incoming"); p.add_argument("--ref", default="origin/book"); p.add_argument("--patch", action="store_true"); p.set_defaults(f=cmd_incoming)
p = sub.add_parser("drift"); p.add_argument("--min", type=float, default=0.98); p.add_argument("--diff"); p.set_defaults(f=cmd_drift)
p = sub.add_parser("toc"); p.set_defaults(f=cmd_toc)
a = ap.parse_args(); a.f(a)
