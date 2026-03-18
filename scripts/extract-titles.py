from pathlib import Path
import re

files = list(Path('.').rglob('*.md'))
exclude = {'_site', 'vendor', 'node_modules', '.git', 'scripts', 'impression'}
files = [f for f in files if not any(p in f.parts for p in exclude)]
files = [f for f in files if f.name not in ('index.md', 'README-lab.md')]

moved = 0
skipped = 0

for f in sorted(files):
    text = f.read_text(encoding='utf-8').replace('\r\n', '\n')

    # Parse frontmatter
    if not text.startswith('---\n'):
        continue
    close = text.find('\n---\n', 4)
    if close == -1:
        continue
    fm = text[4:close]
    body = text[close+5:]

    # Skip if title already in frontmatter
    if re.search(r'^title:', fm, re.MULTILINE):
        skipped += 1
        continue

    # Find first h1 in body
    h1_match = re.search(r'^# (.+)$', body, re.MULTILINE)
    if not h1_match:
        skipped += 1
        continue

    title = h1_match.group(1).strip()
    # Remove the h1 line from body (and any blank line immediately after)
    body = body[:h1_match.start()] + body[h1_match.end():]
    body = re.sub(r'^\n+', '\n', body)

    # Add title to frontmatter as first field
    new_fm = f'title: "{title}"\n' + fm
    new_text = f'---\n{new_fm}\n---\n{body}'
    f.write_text(new_text, encoding='utf-8')
    print(f'  moved title "{title}": {f}')
    moved += 1

print(f'\nDone. {moved} files updated, {skipped} skipped.')
