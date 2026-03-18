#!/usr/bin/env python3
"""
scripts/migrate-from-gitbook.py
────────────────────────────────────────────────────────────────────────────
Prepares Markdown files ported from GitBook for State B independence.

Performs three passes over every .md file in the repo:

  PASS 1 — Download GitBook CDN images and rewrite URLs to local paths.
    GitBook hosts images at URLs like:
      https://2135809782-files.gitbook.io/~/files/v0/b/.../image.png
    These break the moment GitBook access is removed.
    This script downloads each image into assets/images/ and rewrites
    the Markdown reference to a relative path.

  PASS 2 — Convert GitBook proprietary block syntax to plain HTML.
    {% hint style="info" %}...{% endhint %}
      → <div class="hint hint-info">...</div>
    {% hint style="warning" %}...{% endhint %}
      → <div class="hint hint-warning">...</div>
    {% tabs %}...{% endtabs %}
      → stripped, inner content preserved
    {% tab title="..." %}...{% endtab %}
      → <div class="tab">...</div>

  PASS 3 — Report any remaining {% %} tags that need manual review.

Usage:
  cd /path/to/repo/root
  python3 scripts/migrate-from-gitbook.py [--dry-run] [--dir PATH]

Options:
  --dry-run    Show what would change without writing files
  --dir PATH   Directory to scan (default: current directory)

Requirements:
  pip install requests
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
    sys.exit("Missing dependency: pip install requests")


# ── Config ────────────────────────────────────────────────────────────────────

GITBOOK_IMAGE_PATTERNS = [
    # Inline Markdown images with GitBook CDN URLs
    r'!\[([^\]]*)\]\((https?://[^\s)]*(?:gitbook\.io|gitbook-x-prod\.appspot\.com)[^\s)]*)\)',
    # HTML <img> tags with GitBook src
    r'<img([^>]*?)src="(https?://[^\s"]*(?:gitbook\.io|gitbook-x-prod\.appspot\.com)[^\s"]*)"([^>]*?)>',
]

HINT_STYLE_MAP = {
    "info":    "hint-info",
    "warning": "hint-warning",
    "danger":  "hint-danger",
    "success": "hint-success",
    "":        "hint-info",
}

IMAGE_DIR = Path("assets/images")


# ── Helpers ───────────────────────────────────────────────────────────────────

def url_to_local_filename(url: str) -> str:
    """Derive a stable local filename from a CDN URL."""
    parsed = urllib.parse.urlparse(url)
    # Use the last path segment if it has an extension, else hash the URL
    last = Path(parsed.path).name
    if "." in last and len(last) < 80:
        # Sanitise: keep only safe chars
        safe = re.sub(r"[^a-zA-Z0-9_.\-]", "_", last)
        return safe
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"gitbook-image-{url_hash}.png"


def download_image(url: str, dest: Path, dry_run: bool) -> Path | None:
    """Download a remote image to dest. Returns the local path or None on failure."""
    if dry_run:
        return dest
    try:
        resp = requests.get(url, timeout=15, stream=True)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return dest
    except Exception as e:
        print(f"  WARN: could not download {url}: {e}", file=sys.stderr)
        return None


# ── Pass 1: image migration ───────────────────────────────────────────────────

def migrate_images(content: str, md_path: Path, dry_run: bool) -> tuple[str, int]:
    """Replace GitBook CDN image URLs with local relative paths."""
    changes = 0
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    def replace_md_image(m):
        nonlocal changes
        alt, url = m.group(1), m.group(2)
        filename = url_to_local_filename(url)
        local_path = IMAGE_DIR / filename
        # Compute relative path from the Markdown file to assets/images/
        rel = os.path.relpath(local_path, md_path.parent)
        if not dry_run and not local_path.exists():
            result = download_image(url, local_path, dry_run)
            if result is None:
                print(f"  SKIP image (download failed): {url}")
                return m.group(0)
        print(f"  {'[dry]' if dry_run else ''} image: {url[:60]}... → {rel}")
        changes += 1
        return f"![{alt}]({rel})"

    def replace_html_img(m):
        nonlocal changes
        before, url, after = m.group(1), m.group(2), m.group(3)
        filename = url_to_local_filename(url)
        local_path = IMAGE_DIR / filename
        rel = os.path.relpath(local_path, md_path.parent)
        if not dry_run and not local_path.exists():
            result = download_image(url, local_path, dry_run)
            if result is None:
                return m.group(0)
        print(f"  {'[dry]' if dry_run else ''} <img>: {url[:60]}... → {rel}")
        changes += 1
        return f'<img{before}src="{rel}"{after}>'

    content = re.sub(GITBOOK_IMAGE_PATTERNS[0], replace_md_image, content)
    content = re.sub(GITBOOK_IMAGE_PATTERNS[1], replace_html_img, content)
    return content, changes


# ── Pass 2: proprietary syntax ────────────────────────────────────────────────

def migrate_syntax(content: str) -> tuple[str, int]:
    """Convert GitBook {% %} blocks to plain HTML."""
    changes = 0

    # {% hint style="X" %} ... {% endhint %}  (may span lines)
    def replace_hint(m):
        nonlocal changes
        style = m.group(1).strip().strip('"\'') or "info"
        css_class = HINT_STYLE_MAP.get(style, "hint-info")
        inner = m.group(2).strip()
        changes += 1
        return f'<div class="hint {css_class}">\n{inner}\n</div>'

    content = re.sub(
        r'\{%\s*hint\s+style=["\']?(\w*)["\']?\s*%\}(.*?)\{%\s*endhint\s*%\}',
        replace_hint, content, flags=re.DOTALL
    )

    # {% tabs %} wrapper — strip the wrapper tags, keep content
    def strip_tabs(m):
        nonlocal changes
        inner = m.group(1).strip()
        changes += 1
        return inner

    content = re.sub(
        r'\{%\s*tabs\s*%\}(.*?)\{%\s*endtabs\s*%\}',
        strip_tabs, content, flags=re.DOTALL
    )

    # {% tab title="X" %} ... {% endtab %}
    def replace_tab(m):
        nonlocal changes
        title = m.group(1).strip().strip('"\'')
        inner = m.group(2).strip()
        changes += 1
        return f'<div class="tab" data-title="{title}">\n{inner}\n</div>'

    content = re.sub(
        r'\{%\s*tab\s+title=["\']?([^"\'%]*)["\']?\s*%\}(.*?)\{%\s*endtab\s*%\}',
        replace_tab, content, flags=re.DOTALL
    )

    # {% content-ref url="..." %}...{% endcontent-ref %} → plain link
    def replace_content_ref(m):
        nonlocal changes
        url = m.group(1).strip().strip('"\'')
        inner = m.group(2).strip()
        changes += 1
        return f'[{inner}]({url})'

    content = re.sub(
        r'\{%\s*content-ref\s+url=["\']?([^"\'%]*)["\']?\s*%\}(.*?)\{%\s*endcontent-ref\s*%\}',
        replace_content_ref, content, flags=re.DOTALL
    )

    return content, changes


# ── Pass 3: audit remaining tags ──────────────────────────────────────────────

def audit_remaining(content: str, md_path: Path) -> list[str]:
    remaining = re.findall(r'\{%[^%]*%\}', content)
    if remaining:
        return [f"  {md_path}: unhandled tag: {t}" for t in set(remaining)]
    return []


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Migrate GitBook Markdown to Jekyll-ready plain Markdown")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--dir", default=".", help="Root directory to scan (default: current dir)")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    md_files = sorted(root.rglob("*.md"))

    # Exclude scaffold/vendor/build paths
    exclude = {"_site", "node_modules", "vendor", ".git", "scripts"}
    md_files = [f for f in md_files if not any(p in f.parts for p in exclude)]

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

        content, img_n = migrate_images(content, md_path, args.dry_run)
        content, syn_n = migrate_syntax(content)
        warnings = audit_remaining(content, md_path)

        total_image_changes += img_n
        total_syntax_changes += syn_n
        audit_warnings.extend(warnings)

        if content != original:
            print(f"  {md_path.relative_to(root)}: {img_n} images, {syn_n} syntax blocks")
            if not args.dry_run:
                md_path.write_text(content, encoding="utf-8")

    print(f"\n── Summary ──────────────────────────────────────")
    print(f"  Images rewritten:       {total_image_changes}")
    print(f"  Syntax blocks rewritten:{total_syntax_changes}")
    print(f"  Unhandled tags:         {len(audit_warnings)}")

    if audit_warnings:
        print("\n── Manual review needed ─────────────────────────")
        for w in audit_warnings:
            print(w)

    if args.dry_run:
        print("\nDry run complete — no files were modified.")
    else:
        print("\nDone. Review changes with: git diff")
        print("Then commit: git add -A && git commit -m 'migrate: remove GitBook dependencies'")


if __name__ == "__main__":
    main()
