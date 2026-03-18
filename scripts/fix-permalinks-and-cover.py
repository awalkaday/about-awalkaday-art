from pathlib import Path
import re

# ── Fix 1: restore permalinks to chapter README files ─────────────────────────
permalinks = {
    'chronicle-of-milestones-navigation/README.md': '/chronicle-of-milestones-navigation/',
    'evolution-of-a-trek-on-platforms/README.md':   '/evolution-of-a-trek-on-platforms/',
    'artists-proofs-and-ethos/README.md':           '/artists-proofs-and-ethos/',
    'artist-profiling/README.md':                   '/artist-profiling/',
}

for filepath, permalink in permalinks.items():
    f = Path(filepath)
    if not f.exists():
        print(f'NOT FOUND: {filepath}')
        continue
    text = f.read_text(encoding='utf-8').replace('\r\n', '\n')
    if 'permalink:' in text:
        print(f'already has permalink: {filepath}')
        continue
    # Insert permalink after opening ---
    text = text.replace('---\n', f'---\npermalink: {permalink}\n', 1)
    f.write_text(text, encoding='utf-8')
    print(f'restored permalink: {filepath}')

# ── Fix 2: remove duplicate h1 from index.md cover page ──────────────────────
index = Path('index.md')
text = index.read_text(encoding='utf-8').replace('\r\n', '\n')

# The layout renders page.title as h1 already — remove any # heading in body
# but only if title: is already in frontmatter
has_title_in_fm = bool(re.search(r'^title:', text, re.MULTILINE))
if has_title_in_fm:
    # Count h1 occurrences in body (after closing ---)
    fm_end = text.find('\n---\n', 4) + 5
    body = text[fm_end:]
    h1_matches = list(re.finditer(r'^# .+$', body, re.MULTILINE))
    if len(h1_matches) >= 1:
        # Remove the first h1 from body
        m = h1_matches[0]
        body = body[:m.start()] + re.sub(r'^\n+', '\n', body[m.end():])
        index.write_text(text[:fm_end] + body, encoding='utf-8')
        print('fixed: removed duplicate h1 from index.md')
    else:
        print('index.md: no h1 found in body, nothing to remove')
else:
    print('index.md: no title in frontmatter, skipping')

print('\nDone.')
