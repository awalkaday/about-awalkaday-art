from pathlib import Path
import re
import subprocess

ARWEAVE_RE = re.compile(r'https://[a-zA-Z0-9]+\.arweave\.net/\S+|https://arweave\.net/\S+')

def is_arweave(url):
    return 'arweave.net/' in url

def convert_embed(url, caption):
    import urllib.parse
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
        domain = urllib.parse.urlparse(url).netloc or url
        label = caption if caption else domain
        return (
            f'\n<div class="embed-link">\n'
            f'  <a href="{url}" rel="noopener" target="_blank">{label}</a>\n'
            f'</div>\n'
        )

def clean_frontmatter(text):
    """Strip GitBook frontmatter. Extract description and title into clean YAML."""
    match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    if not match:
        return '---\n---\n', text
    fm = match.group(1)
    rest = text[match.end():]

    new_fm = ''

    # Extract description if marked visible (or visibility not set)
    desc_match = re.search(r'description: >-\n((?:[ \t]+.+\n)+)', fm)
    desc_visible = not bool(re.search(r'description:\s*\n\s+visible:\s*false', fm))
    if desc_match and desc_visible:
        desc = ' '.join(line.strip() for line in desc_match.group(1).splitlines())
        new_fm += f'description: "{desc}"\n'

    return f'---\n{new_fm}---\n', rest

def extract_title_from_body(body):
    """Remove first h1 from body, return (title_string, cleaned_body)."""
    h1_match = re.search(r'^# (.+)$', body, re.MULTILINE)
    if not h1_match:
        return None, body
    title = h1_match.group(1).strip()
    # Remove the h1 line
    before = body[:h1_match.start()]
    after = body[h1_match.end():]
    # Collapse any resulting leading blank lines
    cleaned = before + re.sub(r'^\n+', '\n', after)
    return title, cleaned

def get_printlab_fields(f):
    """Preserve printlab-specific frontmatter fields that book branch lacks."""
    preserve = {}
    if not f.exists():
        return preserve
    text = f.read_text(encoding='utf-8').replace('\r\n', '\n')
    for field in ('permalink',):
        m = re.search(rf'^{field}:\s*(.+)$', text, re.MULTILINE)
        if m:
            preserve[field] = m.group(1).strip()
    return preserve

def remigrate_file(f):
    preserved = get_printlab_fields(f)
    result = subprocess.run(
        ['git', 'show', f'book:{f.as_posix()}'],
        capture_output=True, text=True, encoding='utf-8'
    )
    if result.returncode != 0:
        return False, 'not in book branch'

    original = result.stdout.replace('\r\n', '\n')

    # Step 1: clean GitBook frontmatter → description only
    fm_block, body = clean_frontmatter(original)

    # Step 2: extract h1 title from body → move to frontmatter
    title, body = extract_title_from_body(body)

    # Step 3: rebuild frontmatter with title first, then description, then preserved fields
    inner_fm = ''
    if title:
        inner_fm += f'title: "{title}"\n'
    desc_match = re.search(r'description: "(.+)"', fm_block)
    if desc_match:
        inner_fm += f'description: "{desc_match.group(1)}"\n'
    for field, value in preserved.items():
        if field not in inner_fm:
            inner_fm += f'{field}: {value}\n'
    fm_block = f'---\n{inner_fm}---\n' 

    # Step 4: convert embed blocks preserving captions
    def replace_embed(m):
        attrs = m.group(1)
        inner = m.group(2).strip()
        url_match = re.search(r'url=["\']?([^\s"\'%>]+)["\']?', attrs)
        if not url_match:
            return ''
        url = url_match.group(1)
        caption = re.sub(r'\*+', '', inner).strip()
        return convert_embed(url, caption)

    body = re.sub(
        r'\{%\s*embed\b([^%]*?)%\}(.*?)\{%\s*endembed\s*%\}',
        replace_embed, body, flags=re.DOTALL
    )

    def replace_standalone(m):
        attrs = m.group(1)
        url_match = re.search(r'url=["\']?([^\s"\'%>]+)["\']?', attrs)
        if not url_match:
            return ''
        return convert_embed(url_match.group(1), '')
    body = re.sub(r'\{%\s*embed\b([^%]*?)%\}', replace_standalone, body)

    # Step 5: convert hint blocks
    HINT_MAP = {'info':'hint-info','warning':'hint-warning','danger':'hint-danger','success':'hint-success'}
    def replace_hint(m):
        attrs, inner = m.group(1), m.group(2).strip()
        style = re.search(r'style=["\']?(\w+)["\']?', attrs)
        css = HINT_MAP.get(style.group(1) if style else 'info', 'hint-info')
        return f'<div class="hint {css}">\n\n{inner}\n\n</div>'
    body = re.sub(r'\{%\s*hint\b([^%]*?)%\}(.*?)\{%\s*endhint\s*%\}', replace_hint, body, flags=re.DOTALL)

    # Step 6: convert code blocks
    def replace_code(m):
        attrs, inner = m.group(1), m.group(2)
        title_attr = re.search(r'title=["\']?([^"\'%]+)["\']?', attrs)
        comment = f'<!-- {title_attr.group(1).strip()} -->\n' if title_attr else ''
        return f'\n{comment}```\n{inner.strip()}\n```\n'
    body = re.sub(r'\{%\s*code\b([^%]*)%\}(.*?)\{%\s*endcode\s*%\}', replace_code, body, flags=re.DOTALL)

    # Step 7: strip any remaining GitBook tags
    body = re.sub(r'\{%[^%]*%\}', '', body)

    # Step 8: fix double-nested links
    body = re.sub(r'\[\[([^\]]+)\]\(([^)]+)\)\]\([^)]+\)', r'[\1](\2)', body)

    f.write_text(fm_block + body, encoding='utf-8')
    return True, title or 'no title found'

# ── Run ───────────────────────────────────────────────────────────────────────
files = list(Path('.').rglob('*.md'))
exclude = {'_site', 'vendor', 'node_modules', '.git', 'scripts', 'impression'}
files = [f for f in files if not any(p in f.parts for p in exclude)]
files = [f for f in files if f.name not in ('index.md', 'README-lab.md')]

print(f'Remigrating {len(files)} files from book branch...')
for f in sorted(files):
    ok, msg = remigrate_file(f)
    print(f'  {"ok" if ok else "SKIP"}: {f} ({msg})')

print('\nDone. Review with: git diff')
print('Then commit: git add -A && git commit -m "refactor: unified remigration with title extraction"')
