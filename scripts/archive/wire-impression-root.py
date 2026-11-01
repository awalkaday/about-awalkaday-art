from pathlib import Path

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

# Build include blocks — file is at repo root so paths are direct
includes = ""
for slug, path in chapters:
    includes += f"""
<section class="chapter" id="{slug}">
{{% capture chapter %}}{{% include_relative {path} %}}{{% endcapture %}}
{{{{ chapter | markdownify }}}}
</section>
"""

content = """---
layout: impression
permalink: /impression/
title: "Walking Memories \u2014 Print / PDF"
---

<div class="book-cover">
  <h1 class="book-title">Walking Memories</h1>
  <p class="book-subtitle">An open-source artist\'s book tracing the digital footprints<br>
  of an exiled wanderer and his Belgian pixels<br>
  during an eight-year odyssey</p>
  <p class="book-author">Chris-Armel Iradukunda (daqhris)</p>
  <p class="book-meta">awalkaday 251\u20132022</p>
</div>
""" + includes

# Write to repo root, not impression/ subfolder
Path("impression.md").write_text(content, encoding="utf-8")
print("Written: impression.md at repo root")
print(f"Chapters wired: {len(chapters)}")
print("Next: delete impression/index.md and commit impression.md")
