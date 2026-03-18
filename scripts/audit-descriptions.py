from pathlib import Path
import re

files = list(Path('.').rglob('*.md'))
exclude = {'_site', 'vendor', 'node_modules', '.git', 'scripts', 'impression'}
files = [f for f in files if not any(p in f.parts for p in exclude)]

missing = []
for f in files:
    text = f.read_text(encoding='utf-8').replace('\r\n', '\n')
    if not text.startswith('---'):
        continue
    rest = text[4:]
    close = rest.find('\n---')
    if close == -1:
        continue
    fm = rest[:close]
    if 'description:' not in fm:
        missing.append(str(f))

print(f"Files missing description: {len(missing)}")
for m in missing:
    print(f"  {m}")
