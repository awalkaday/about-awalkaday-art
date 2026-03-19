from pathlib import Path

chapters = [
    "one-step-forward", "artist-statement", "reading-guide",
    "introduction-to-the-photo-series", "beyond-pixels",
    "mobile-studio", "mobile-studio-on-the-go", "mobile-studio-cameras",
    "mobile-studio-gaming", "chronicle", "chronicle-parallel",
    "chronicle-internet", "chronicle-blockchain", "evolution",
    "evolution-instagram", "evolution-twitter", "evolution-github",
    "evolution-ethereum", "evolution-web", "artists-proofs",
    "artists-proofs-commits", "artists-proofs-oss", "artists-proofs-git",
    "artist-profiling", "artist-profiling-inception", "artist-profiling-human",
    "artist-profiling-training", "contact", "imprint", "catalogue",
    "appendix", "postscript",
]

includes = ""
for slug in chapters:
    includes += f"""
<section class="chapter" id="{slug}">
{{% capture chapter %}}{{% include_relative _chapters/{slug}.md %}}{{% endcapture %}}
{{{{ chapter | markdownify }}}}
</section>
"""

content = """---
layout: impression
permalink: /impression/
title: "Walking Memories — Print / PDF"
---

<div class="book-cover">
  <h1 class="book-title">Walking Memories</h1>
  <p class="book-subtitle">An open-source artist\'s book tracing the digital footprints<br>
  of an exiled wanderer and his Belgian pixels<br>
  during an eight-year odyssey</p>
  <figure class="embed-media cover-photo">
    <img src="https://d72mm3yw6jhz7lrwgqqtnebzznwlcz27mbhyh4rvmcpirgouwwoa.arweave.net/H_TGbxbyT5-uNjQhNpA5y2yxZ19gT4PyNWCeiJnUtZw" alt="awalkaday 251-2022" loading="eager">
    <figcaption>awalkaday 251\u20132022</figcaption>
  </figure>
  <p class="book-author">Chris-Armel Iradukunda (daqhris)</p>
  <p class="book-meta">awalkaday 251\u20132022</p>
</div>
""" + includes

Path("impression.md").write_text(content, encoding="utf-8")
print("Written: impression.md using _chapters/*.md with markdownify")
