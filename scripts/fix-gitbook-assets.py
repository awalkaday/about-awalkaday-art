from pathlib import Path
import re

files = list(Path('.').rglob('*.md'))
exclude = {'_site', 'vendor', 'node_modules', '.git', 'scripts', '_chapters'}
files = [f for f in files if not any(p in f.parts for p in exclude)]

fixed_total = 0
for f in files:
    text = f.read_text(encoding='utf-8')
    # Fix relative .gitbook paths to absolute
    # Matches: .gitbook/assets/... or ../.gitbook/assets/...
    cleaned = re.sub(
        r'(?<!\(/)(?:\.\.?/)*\.gitbook/assets/',
        '/.gitbook/assets/',
        text
    )
    # Also fix src= variants in HTML img tags
    cleaned = re.sub(
        r'src="(?:\.\.?/)*\.gitbook/assets/',
        'src="/.gitbook/assets/',
        cleaned
    )
    if cleaned != text:
        count = text.count('.gitbook/assets') - cleaned.count('/.gitbook/assets')
        # More reliable count
        orig_count = len(re.findall(r'(?<!\(/)(?:\.\.?/)*\.gitbook/assets/', text))
        f.write_text(cleaned, encoding='utf-8')
        print(f'  fixed {orig_count} paths: {f}')
        fixed_total += orig_count

print(f'\nDone. {fixed_total} paths rewritten to absolute /.gitbook/assets/')
