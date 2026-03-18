from pathlib import Path
import re
import subprocess

# ── Issue 1: restore postscript description ───────────────────────────────────
postscript = Path('postscript.md')
text = postscript.read_text(encoding='utf-8').replace('\r\n', '\n')
if 'description:' not in text:
    desc = 'An exhaustive table listing the 263 digital photographs with names, public timestamps and WALK token identifiers'
    text = text.replace('---\n', f'---\ndescription: "{desc}"\n', 1)
    postscript.write_text(text, encoding='utf-8')
    print('fixed: postscript.md description')
else:
    print('skipped: postscript.md already has description')

# ── Issue 2 & 3: re-migrate all .md files from book branch ───────────────────
# preserving caption content inside embed blocks this time

ARWEAVE_RE = re.compile(r'https://[a-zA-Z0-9]+\.arweave\.net/\S+|https://arweave\.net/\S+')

def is_arweave(url):
    return 'arweave.net/' in url

def convert_embed(url, caption):
    url = url.strip().strip('"\'')
    caption = caption.strip()
    if is_arweave(url):
        cap_html = f'\n  <figcaption>{caption}</figcaption>' if caption else ''
        return (
            f'\n<figure class="embed-media">\n'
            f'  <img src="{url}" alt="{caption}" loading="lazy">{cap_html}\n'
            f'</figure>\n'
        )
    else:
        import urllib.parse
        domain = urllib.parse.urlparse(url).netloc or url
        label = caption if caption else domain
        return (
            f'\n<div class="embed-link">\n'
            f'  <a href="{url}" rel="noopener" target="_blank">{label}</a>\n'
            f'</div>\n'
        )

def remigrate_file(f):
    # Get original from book branch
    result = subprocess.run(
        ['git', 'show', f'book:{f.as_posix()}'],
        capture_output=True, text=True, encoding='utf-8'
    )
    if result.returncode != 0:
        return False, 'not in book branch'

    original = result.stdout

    # Strip GitBook frontmatter, keep only description if visible
    def clean_frontmatter(text):
        match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
        if not match:
            return '---\n---\n', text
        fm = match.group(1)
        rest = text[match.end():]
        desc_match = re.search(r'description: >-\n((?:[ \t]+.+\n)+)', fm)
        desc_visible = not bool(re.search(r'description:\s*\n\s+visible:\s*false', fm))
        new_fm = ''
        if desc_match and desc_visible:
            desc = ' '.join(line.strip() for line in desc_match.group(1).splitlines())
            new_fm += f'description: "{desc}"\n'
        return f'---\n{new_fm}---\n', rest

    fm_block, body = clean_frontmatter(original)

    # Convert embed blocks preserving captions
    def replace_embed(m):
        attrs = m.group(1)
        inner = m.group(2).strip()
        url_match = re.search(r'url=["\']?([^\s"\'%>]+)["\']?', attrs)
        if not url_match:
            return ''
        url = url_match.group(1)
        # Clean markdown from caption: strip bold markers
        caption = re.sub(r'\*+', '', inner).strip()
        return convert_embed(url, caption)

    body = re.sub(
        r'\{%\s*embed\b([^%]*?)%\}(.*?)\{%\s*endembed\s*%\}',
        replace_embed, body, flags=re.DOTALL
    )
    # Standalone embeds (no closing tag)
    def replace_standalone(m):
        attrs = m.group(1)
        url_match = re.search(r'url=["\']?([^\s"\'%>]+)["\']?', attrs)
        if not url_match:
            return ''
        return convert_embed(url_match.group(1), '')
    body = re.sub(r'\{%\s*embed\b([^%]*?)%\}', replace_standalone, body)

    # Convert hint blocks
    HINT_MAP = {'info':'hint-info','warning':'hint-warning','danger':'hint-danger','success':'hint-success'}
    def replace_hint(m):
        attrs, inner = m.group(1), m.group(2).strip()
        style = re.search(r'style=["\']?(\w+)["\']?', attrs)
        css = HINT_MAP.get(style.group(1) if style else 'info', 'hint-info')
        return f'<div class="hint {css}">\n\n{inner}\n\n</div>'
    body = re.sub(r'\{%\s*hint\b([^%]*?)%\}(.*?)\{%\s*endhint\s*%\}', replace_hint, body, flags=re.DOTALL)

    # Convert code blocks
    def replace_code(m):
        attrs, inner = m.group(1), m.group(2)
        title = re.search(r'title=["\']?([^"\'%]+)["\']?', attrs)
        comment = f'<!-- {title.group(1).strip()} -->\n' if title else ''
        return f'\n{comment}```\n{inner.strip()}\n```\n'
    body = re.sub(r'\{%\s*code\b([^%]*)%\}(.*?)\{%\s*endcode\s*%\}', replace_code, body, flags=re.DOTALL)

    # Strip remaining GitBook tags
    body = re.sub(r'\{%[^%]*%\}', '', body)

    # Fix double-nested links
    body = re.sub(r'\[\[([^\]]+)\]\(([^)]+)\)\]\([^)]+\)', r'[\1](\2)', body)

    final = fm_block + body
    f.write_text(final, encoding='utf-8')
    return True, 'ok'

# Run on all content .md files
files = list(Path('.').rglob('*.md'))
exclude = {'_site', 'vendor', 'node_modules', '.git', 'scripts', 'impression'}
files = [f for f in files if not any(p in f.parts for p in exclude)]
files = [f for f in files if f.name != 'index.md' and f.name != 'README-lab.md']

print(f'\nRemigrating {len(files)} files from book branch...')
for f in sorted(files):
    ok, msg = remigrate_file(f)
    print(f'  {"ok" if ok else "SKIP"}: {f} ({msg})')

print('\nDone. Review with: git diff')
