from pathlib import Path

f = Path("assets/css/print.css")
text = f.read_text(encoding="utf-8")

# Fix 1: reduce orphans and widows from 3 to 2
text = text.replace(
    "  orphans: 3;   /* minimum lines at bottom of page */\n  widows: 3;    /* minimum lines at top of page */",
    "  orphans: 2;\n  widows: 2;"
)

# Fix 2: remove page-break-inside: avoid from standalone img rule
# (embed-media already handles image breaking — standalone img avoid causes conflicts)
text = text.replace(
    "img {\n  max-width: 100%;\n  height: auto;\n  display: block;\n  margin: 5mm auto;\n  page-break-inside: avoid;\n}",
    "img {\n  max-width: 100%;\n  height: auto;\n  display: block;\n  margin: 5mm auto;\n}"
)

# Fix 3: soften embed-media — allow break if content truly cannot fit
text = text.replace(
    ".embed-media {\n  margin: 5mm auto;\n  text-align: center;\n  page-break-inside: avoid;\n}",
    ".embed-media {\n  margin: 5mm auto;\n  text-align: center;\n  break-inside: avoid-page;\n}"
)

# Fix 4: reduce max-height slightly so images fit more reliably
# 110mm is pushing the limit on 165mm content area — 95mm gives more breathing room
text = text.replace(
    "  max-height: 110mm;",
    "  max-height: 95mm;"
)

# Fix 5: fix @page syntax — move running headers inside @page block
old_page = """@page {
  size: 210mm 210mm;
  margin: 20mm 18mm 25mm 22mm;
}

  /* Running header: book title on left pages, chapter title on right */
  @top-left {
    content: string(book-title);
    font-family: var(--font-ui);
    font-size: 8pt;
    color: var(--color-muted);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  @top-right {
    content: string(chapter-title);
    font-family: var(--font-ui);
    font-size: 8pt;
    color: var(--color-muted);
  }

  /* Page number centered at the bottom */
  @bottom-center {
    content: counter(page);
    font-family: var(--font-ui);
    font-size: 8pt;
    color: var(--color-muted);
  }
}"""

new_page = """@page {
  size: 210mm 210mm;
  margin: 20mm 18mm 25mm 22mm;

  @top-left {
    content: string(book-title);
    font-family: var(--font-ui);
    font-size: 8pt;
    color: var(--color-muted);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  @top-right {
    content: string(chapter-title);
    font-family: var(--font-ui);
    font-size: 8pt;
    color: var(--color-muted);
  }
  @bottom-center {
    content: counter(page);
    font-family: var(--font-ui);
    font-size: 8pt;
    color: var(--color-muted);
  }
}"""

if old_page in text:
    text = text.replace(old_page, new_page)
    print("fixed @page syntax")
else:
    print("@page pattern not found - check manually")

f.write_text(text, encoding="utf-8")
print("Done. All fixes applied.")
