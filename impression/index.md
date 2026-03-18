---
layout: impression
permalink: /impression/
title: "Walking Memories — Print / PDF"
---

<!--
  /impression/index.md
  ─────────────────────────────────────────────────────────────────
  This single page is the print/PDF source. It concatenates every
  chapter in the order defined by _data/toc.yml and hands the full
  HTML stream to Paged.js, which renders it as a paginated document.

  TO ADD A CHAPTER: add it to _data/toc.yml and add an
  {% include_relative %} line here in matching order.

  GENERATING THE PDF:
    1. Open http://localhost:4000/impression/ in Chrome (or Chromium)
    2. Wait for Paged.js to finish rendering (page count appears top-left)
    3. File → Print → Destination: Save as PDF
    4. Disable "Headers and footers" in More settings
    5. Save

  Running headlessly (optional CI step):
    npx @pagedjs/cli impression/index.html -o walking-memories.pdf
  ─────────────────────────────────────────────────────────────────
-->

<div class="book-cover">
  <h1 class="book-title">Walking Memories</h1>
  <p class="book-subtitle">An open-source artist's book tracing the digital footprints<br>
  of an exiled wanderer and his Belgian pixels<br>
  during an eight-year odyssey</p>
  <p class="book-author">Chris-Armel Iradukunda (daqhris)</p>
  <p class="book-meta">awalkaday 251–2022</p>
</div>

<!--
  Include each chapter as a section with a page-break before it.
  Replace these placeholder paths with your actual Markdown file paths.
  The `relative_url` tag handles baseurl automatically.

  Example pattern (uncomment and adapt):

  <section class="chapter" id="one-step-forward">
  {% capture chapter %}{% include_relative ../one-step-forward.md %}{% endcapture %}
  {{ chapter | markdownify }}
  </section>

  <section class="chapter" id="artist-statement">
  {% capture chapter %}{% include_relative ../artist-statement.md %}{% endcapture %}
  {{ chapter | markdownify }}
  </section>

  NOTE: Jekyll's include_relative resolves relative to the calling file.
  If your .md files are at the repo root, use `../filename.md`.
  If they're in a `_pages/` folder, adjust accordingly.

  Until you wire up the actual includes, the Paged.js rendering
  will show only this cover page — that's expected during setup.
-->
