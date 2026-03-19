from pathlib import Path
import re

chapters = [
    ("one-step-forward",           "one-step-forward.md"),
    ("artist-statement",           "artist-statement.md"),
    ("reading-guide",              "reading-guide.md"),
    ("introduction-to-the-photo-series", "introduction-to-the-photo-series.md"),
    ("beyond-pixels",              "beyond-pixels-a-stroll-into-nature.md"),
    ("mobile-studio",              "mobile-studio-and-digital-toolkit/README.md"),
    ("mobile-studio-on-the-go",    "mobile-studio-and-digital-toolkit/on-the-go-photography.md"),
    ("mobile-studio-cameras",      "mobile-studio-and-digital-toolkit/cameras-and-photo-editing.md"),
    ("mobile-studio-gaming",       "mobile-studio-and-digital-toolkit/gaming-laptop.md"),
    ("chronicle",                  "chronicle-of-milestones-navigation/README.md"),
    ("chronicle-parallel",         "chronicle-of-milestones-navigation/parallel-pathways.md"),
    ("chronicle-internet",         "chronicle-of-milestones-navigation/internet-footprints.md"),
    ("chronicle-blockchain",       "chronicle-of-milestones-navigation/blockchain-records.md"),
    ("evolution",                  "evolution-of-a-trek-on-platforms/README.md"),
    ("evolution-instagram",        "evolution-of-a-trek-on-platforms/instagram.md"),
    ("evolution-twitter",          "evolution-of-a-trek-on-platforms/x-twitter.md"),
    ("evolution-github",           "evolution-of-a-trek-on-platforms/github.md"),
    ("evolution-ethereum",         "evolution-of-a-trek-on-platforms/ethereum.md"),
    ("evolution-web",              "evolution-of-a-trek-on-platforms/web-gallery.md"),
    ("artists-proofs",             "artists-proofs-and-ethos/README.md"),
    ("artists-proofs-commits",     "artists-proofs-and-ethos/public-git-commits.md"),
    ("artists-proofs-oss",         "artists-proofs-and-ethos/open-source-software.md"),
    ("artists-proofs-git",         "artists-proofs-and-ethos/git-usage-history.md"),
    ("artist-profiling",           "artist-profiling/README.md"),
    ("artist-profiling-inception", "artist-profiling/project-inception.md"),
    ("artist-profiling-human",     "artist-profiling/human-identity.md"),
    ("artist-profiling-training",  "artist-profiling/training-ground.md"),
    ("contact",                    "contact.md"),
    ("imprint",                    "imprint.md"),
    ("catalogue",                  "catalogue.md"),
    ("appendix",                   "appendix.md"),
    ("postscript",                 "postscript.md"),
]

out_dir = Path("_chapters")
out_dir.mkdir(exist_ok=True)

def strip_frontmatter_and_get_meta(text):
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None, None, text
    close = text.find("\n---\n", 4)
    if close == -1:
        return None, None, text
    fm = text[4:close]
    body = text[close+5:]
    title_m = re.search(r'^title:\s*"?(.+?)"?\s*$', fm, re.MULTILINE)
    desc_m = re.search(r'^description:\s*"?(.+?)"?\s*$', fm, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else None
    desc = desc_m.group(1).strip() if desc_m else None
    return title, desc, body

written = 0
for slug, path in chapters:
    src = Path(path)
    if not src.exists():
        print(f"  MISSING: {path}")
        continue
    text = src.read_text(encoding="utf-8")
    title, desc, body = strip_frontmatter_and_get_meta(text)

    # Write as Markdown — title as h1, description as italic paragraph
    # markdownify in the impression page will process this correctly
    header = ""
    if title:
        header += f"# {title}\n\n"
    if desc:
        header += f"*{desc}*\n\n"

    # Write .md so markdownify processes it properly
    out_path = out_dir / f"{slug}.md"
    out_path.write_text(header + body, encoding="utf-8")
    print(f"  ok: {slug}")
    written += 1

print(f"\nWritten {written} chapter snippets to _chapters/ as .md files")
