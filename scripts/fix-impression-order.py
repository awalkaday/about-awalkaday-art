from pathlib import Path
import re

f = Path("impression.md")
text = f.read_text(encoding="utf-8")

# The correct order matching toc.yml exactly
correct_order = [
    ("one-step-forward",           "one-step-forward"),
    ("artist-statement",           "artist-statement"),
    ("reading-guide",              "reading-guide"),
    ("introduction-to-the-photo-series", "introduction-to-the-photo-series"),
    ("beyond-pixels",              "beyond-pixels"),
    ("mobile-studio",              "mobile-studio"),
    ("mobile-studio-on-the-go",    "mobile-studio-on-the-go"),
    ("mobile-studio-cameras",      "mobile-studio-cameras"),
    ("mobile-studio-gaming",       "mobile-studio-gaming"),
    ("chronicle",                  "chronicle"),
    ("chronicle-parallel",         "chronicle-parallel"),
    ("chronicle-internet",         "chronicle-internet"),
    ("chronicle-blockchain",       "chronicle-blockchain"),
    ("evolution",                  "evolution"),
    ("evolution-instagram",        "evolution-instagram"),
    ("evolution-github",           "evolution-github"),
    ("evolution-web",              "evolution-web"),
    ("evolution-twitter",          "evolution-twitter"),
    ("evolution-ethereum",         "evolution-ethereum"),
    ("artists-proofs",             "artists-proofs"),
    ("artists-proofs-commits",     "artists-proofs-commits"),
    ("artists-proofs-oss",         "artists-proofs-oss"),
    ("artists-proofs-git",         "artists-proofs-git"),
    ("artist-profiling",           "artist-profiling"),
    ("artist-profiling-human",     "artist-profiling-human"),
    ("artist-profiling-training",  "artist-profiling-training"),
    ("artist-profiling-inception", "artist-profiling-inception"),
    ("contact",                    "contact"),
    ("imprint",                    "imprint"),
    ("catalogue",                  "catalogue"),
    ("appendix",                   "appendix"),
    ("postscript",                 "postscript"),
]

# Build the new includes block
new_includes = ""
for slug, chapter_file in correct_order:
    new_includes += f"""
<section class="chapter" id="{slug}">
{{% capture chapter %}}{{% include_relative _chapters/{chapter_file}.md %}}{{% endcapture %}}
{{{{ chapter | markdownify }}}}
</section>
"""

# Find where the sections start and replace everything from first <section> onward
section_start = text.find('<section class="chapter"')
if section_start == -1:
    print("ERROR: could not find <section> blocks in impression.md")
else:
    cover_block = text[:section_start]
    f.write_text(cover_block + new_includes, encoding="utf-8")
    print("Done. impression.md rewritten with correct chapter order.")
    print("Evolution: instagram → github → web-gallery → x-twitter → ethereum")
    print("Artist Profiling: human-identity → training-ground → project-inception")
