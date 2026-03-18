#!/usr/bin/env python3
"""
scripts/migrate-from-gitbook.py
────────────────────────────────────────────────────────────────────────────
Prepares Markdown files ported from GitBook for State B independence.
No runtime dependency on GitBook infrastructure after this runs.

PASS 1 — Download GitBook CDN images and rewrite URLs to local paths.
PASS 2 — Convert all GitBook proprietary block syntax to plain HTML/Markdown.

Handled syntax:
  {% hint style="X" icon="Y" %}     → <div class="hint hint-X">
  {% embed url="arweave..." %}       → <figure class="embed-media"><img>
  {% embed url="other..." %}         → <div class="embed-link"><a>
  {% code title="X" ... %}           → fenced code block with title comment
  {% tabs %} / {% tab title="X" %}   → <div class="tab">
  {% content-ref url="X" %}          → plain Markdown link

SKIPPED files (contain intentional Jekyll Liquid):
  impression/index.md

Usage:
  python3 scripts/migrate-from-gitbook.py [--dry-run] [--dir PATH]
────────────────────────────────────────────────────────────────────────────
"""

import os
import re
import sys
import hashlib
import argparse
import urllib.parse
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: run  python3 -m pip install requests")


# ── Config ────────────────────────────────────────────────────────────────────

# Files that contain intentional Jekyll Liquid tags — never touch these
SKIP_FILES = {
    "impression/index.md",
    "impression\\index.md",
}

# URL prefixes that serve media files directly (render as <img>)
MEDIA_URL_PREFIXES = (
    "https://arweave.net/",
    "https://arweave.net/",
)
# Also catch long Arweave gateway subdomains like xxxx.arweave.net/
ARWEAVE_PATTERN = re.compile(r'https://[a-z0-9]+\.arweave\.net/', re.I)

GITBOOK_CDN_PATTERN = re.compile(
    r'!\[([^\]]*)\]\((https?://[^\s)]*(?:gitbook\.io|gitbook-x-prod\.appspot\.com)[^\s)]*)\)'
)
GITBOOK_IMG_TAG_PATTERN = re.compile(
    r'<img([^>]*?)src="(https?://[^\s"]*(?:gitbook\.io|gitbook-x-prod\.appspot\.com)[^\s"]*)"([^>]*?)>'
)

IMAGE_DIR = Path("assets/images")

HINT_STYLE_MAP = {
    "info":    "hint-info",
    "warning": "hint-warning",
    "danger":  "hint-danger",
    "success": "hint-success",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_arweave_url(url: str) -> bool:
    return (
        url.startswith("https://arweave.net/")
        or bool(ARWEAVE_PATTERN.match(url))
    )

def url_to_local_filename(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    last = Path(parsed.path).name
    if "." in last and len(last) < 80:
        return re.sub(r"[^a-zA-Z0-9_.\-]", "_", last)
    return f"gitbook-image-{hashlib.md5(url.encode()).hexdigest()[:12]}.jpg"

def download_image(url: str, dest: Path, dry_run: bool) -> bool:
    if dry_run:
        return True
    try:
        resp = requests.get(url, timeout=20, stream=True)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  WARN: could not download {url[:70]}: {e}", file=sys.stderr)
        return False

def short_url(url: str, length: int = 60) -> str:
    return url if len(url) <= length else url[:length] + "..."


# ── Pass 1: GitBook CDN images ────────────────────────────────────────────────

def migrate_gitbook_cdn_images(content: str, md_path: Path, dry_run: bool) -> tuple[str, int]:
    changes = 0

    def replace_md(m):
        nonlocal changes
        alt, url = m.group(1), m.group(2)
        filename = url_to_local_filename(url)
        local_path = IMAGE_DIR / filename
        rel = os.path.relpath(local_path, md_path.parent).replace("\\", "/")
        if not dry_run and not local_path.exists():
            if not download_image(url, local_path, dry_run):
                return m.group(0)
        print(f"  {'[dry] ' if dry_run else ''}cdn-img: {short_url(url)} → {rel}")
        changes += 1
        return f"![{alt}]({rel})"

    def replace_img_tag(m):
        nonlocal changes
        before, url, after = m.group(1), m.group(2), m.group(3)
        filename = url_to_local_filename(url)
        local_path = IMAGE_DIR / filename
        rel = os.path.relpath(local_path, md_path.parent).replace("\\", "/")
        if not dry_run and not local_path.exists():
            if not download_image(url, local_path, dry_run):
                return m.group(0)
        print(f"  {'[dry] ' if dry_run else ''}cdn-img-tag: {short_url(url)} → {rel}")
        changes += 1
        return f'<img{before}src="{rel}"{after}>'

    content = GITBOOK_CDN_PATTERN.sub(replace_md, content)
    content = GITBOOK_IMG_TAG_PATTERN.sub(replace_img_tag, content)
    return content, changes


# ── Pass 2: proprietary syntax ────────────────────────────────────────────────

def migrate_syntax(content: str, dry_run: bool) -> tuple[str, int]:
    changes = 0

    # ── hint (with optional icon= attribute) ─────────────────────────────────
    # Matches: {% hint style="info" %} or {% hint style="info" icon="pencil" %}
    def replace_hint(m):
        nonlocal changes
        attrs = m.group(1)          # everything between "hint" and "%}"
        inner = m.group(2).strip()
        style_match = re.search(r'style=["\']?(\w+)["\']?', attrs)
        style = style_match.group(1) if style_match else "info"
        css_class = HINT_STYLE_MAP.get(style, "hint-info")
        changes += 1
        return f'<div class="hint {css_class}">\n\n{inner}\n\n</div>'

    content = re.sub(
        r'\{%\s*hint\b([^%]*?)%\}(.*?)\{%\s*endhint\s*%\}',
        replace_hint, content, flags=re.DOTALL
    )

    # ── embed — Arweave media → <figure><img> ─────────────────────────────────
    def replace_embed(m):
        nonlocal changes
        attrs = m.group(1)
        url_match = re.search(r'url=["\']?([^\s"\'%>]+)["\']?', attrs)
        if not url_match:
            changes += 1
            return ""   # malformed embed — drop it
        url = url_match.group(1).strip().strip("\"'")
        changes += 1
        if is_arweave_url(url):
            # Permanent media storage — render as image
            return (
                f'\n<figure class="embed-media">\n'
                f'  <img src="{url}" alt="" loading="lazy">\n'
                f'  <figcaption><a href="{url}" rel="noopener">'
                f'{url[:55]}{"..." if len(url) > 55 else ""}'
                f'</a></figcaption>\n'
                f'</figure>\n'
            )
        else:
            # External URL — render as a linked card
            domain = urllib.parse.urlparse(url).netloc or url
            return (
                f'\n<div class="embed-link">\n'
                f'  <a href="{url}" rel="noopener" target="_blank">'
                f'{domain}</a>\n'
                f'</div>\n'
            )

    content = re.sub(
        r'\{%\s*embed\b([^%]*?)%\}.*?\{%\s*endembed\s*%\}',
        replace_embed, content, flags=re.DOTALL
    )

    # ── standalone embed (no closing endembed — stacked or self-closing) ──
    # Second pass: catches any {% embed %} left over after the paired pass.
    content = re.sub(
        r'\{%\s*embed\b([^%]*?)%\}',
        replace_embed, content
    )

    # ── code blocks with title ────────────────────────────────────────────────
    def replace_code(m):
        nonlocal changes
        attrs = m.group(1)
        inner = m.group(2)
        title_match = re.search(r'title=["\']?([^"\'%]+)["\']?', attrs)
        title = title_match.group(1).strip() if title_match else ""
        changes += 1
        title_comment = f"<!-- {title} -->\n" if title else ""
        return f"\n{title_comment}```\n{inner.strip()}\n```\n"

    content = re.sub(
        r'\{%\s*code\b([^%]*)%\}(.*?)\{%\s*endcode\s*%\}',
        replace_code, content, flags=re.DOTALL
    )

    # ── tabs wrapper — strip outer tags, keep content ─────────────────────────
    def strip_tabs(m):
        nonlocal changes
        changes += 1
        return m.group(1).strip()

    content = re.sub(
        r'\{%\s*tabs\s*%\}(.*?)\{%\s*endtabs\s*%\}',
        strip_tabs, content, flags=re.DOTALL
    )

    # ── individual tab ────────────────────────────────────────────────────────
    def replace_tab(m):
        nonlocal changes
        title = m.group(1).strip().strip("\"'")
        inner = m.group(2).strip()
        changes += 1
        return f'\n<div class="tab" data-title="{title}">\n\n{inner}\n\n</div>\n'

    content = re.sub(
        r'\{%\s*tab\s+title=["\']?([^"\'%]*)["\']?\s*%\}(.*?)\{%\s*endtab\s*%\}',
        replace_tab, content, flags=re.DOTALL
    )

    # ── content-ref → plain Markdown link ────────────────────────────────────
    def replace_content_ref(m):
        nonlocal changes
        url = m.group(1).strip().strip("\"'")
        inner = m.group(2).strip()
        changes += 1
        return f'[{inner or url}]({url})'

    content = re.sub(
        r'\{%\s*content-ref\s+url=["\']?([^"\'%]*)["\']?\s*%\}(.*?)\{%\s*endcontent-ref\s*%\}',
        replace_content_ref, content, flags=re.DOTALL
    )

    return content, changes


# ── Pass 3: audit remaining tags ──────────────────────────────────────────────

def audit_remaining(content: str, md_path: Path) -> list[str]:
    remaining = re.findall(r'\{%[^%]*%\}', content)
    if remaining:
        return [f"  {md_path}: unhandled tag: {t}" for t in dict.fromkeys(remaining)]
    return []


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Migrate GitBook Markdown to plain Jekyll-compatible Markdown"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing files")
    parser.add_argument("--dir", default=".",
                        help="Root directory to scan (default: current dir)")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    md_files = sorted(root.rglob("*.md"))

    exclude_dirs = {"_site", "node_modules", "vendor", ".git", "scripts"}
    md_files = [f for f in md_files if not any(p in f.parts for p in exclude_dirs)]

    # Exclude intentional Jekyll Liquid files
    def should_skip(f: Path) -> bool:
        rel = str(f.relative_to(root))
        return any(rel == s or rel.replace("\\", "/") == s.replace("\\", "/")
                   for s in SKIP_FILES)

    md_files = [f for f in md_files if not should_skip(f)]

    if not md_files:
        print(f"No .md files found under {root}")
        return

    total_image_changes = 0
    total_syntax_changes = 0
    audit_warnings = []

    print(f"Scanning {len(md_files)} Markdown files under {root}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'WRITE'}\n")

    for md_path in md_files:
        original = md_path.read_text(encoding="utf-8")
        content = original

        content, img_n = migrate_gitbook_cdn_images(content, md_path, args.dry_run)
        content, syn_n = migrate_syntax(content, args.dry_run)
        warnings = audit_remaining(content, md_path)

        total_image_changes += img_n
        total_syntax_changes += syn_n
        audit_warnings.extend(warnings)

        if content != original:
            rel = md_path.relative_to(root)
            print(f"  {rel}: {img_n} cdn-images, {syn_n} syntax blocks converted")
            if not args.dry_run:
                md_path.write_text(content, encoding="utf-8")

    print(f"\n── Summary ──────────────────────────────────────")
    print(f"  CDN images rewritten:     {total_image_changes}")
    print(f"  Syntax blocks converted:  {total_syntax_changes}")
    print(f"  Unhandled tags remaining: {len(audit_warnings)}")

    if audit_warnings:
        print("\n── Still needs manual review ────────────────────")
        for w in audit_warnings:
            print(w)

    if args.dry_run:
        print("\nDry run complete — no files were modified.")
        if total_syntax_changes > 0:
            print(f"Run without --dry-run to apply {total_syntax_changes} conversions.")
    else:
        print("\nDone. Review with:  git diff")
        print("Then commit:  git add -A && git commit -m 'migrate: remove GitBook syntax'")


if __name__ == "__main__":
    main()
