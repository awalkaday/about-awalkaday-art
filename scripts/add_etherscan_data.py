import re
import sys
from pathlib import Path

MANIFOLD_REF = "1785897200"
CONTRACT = "0xe31801c2e58b151c3ded2cb29da56147b7f27eb1"

opening_tag = re.compile(r"<a\b[^>]*>", re.IGNORECASE)
manifold_href = re.compile(
    rf'\bhref\s*=\s*(["\'])'
    rf'https://manifold\.xyz/@daqhris/contract/{MANIFOLD_REF}/(\d+)'
    rf'\1',
    re.IGNORECASE,
)
etherscan_attribute = re.compile(
    r'\bdata-etherscan\s*=\s*(["\']).*?\1',
    re.IGNORECASE,
)

if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 add_etherscan_data.py postscript.md")

source = Path(sys.argv[1])
text = source.read_text(encoding="utf-8")
updated = 0

def add_or_update_attribute(match):
    global updated

    tag = match.group(0)
    href_match = manifold_href.search(tag)
    if not href_match:
        return tag

    token_id = href_match.group(2)
    etherscan_url = f"https://etherscan.io/nft/{CONTRACT}/{token_id}"
    attribute = f'data-etherscan="{etherscan_url}"'

    if etherscan_attribute.search(tag):
        new_tag = etherscan_attribute.sub(attribute, tag, count=1)
    else:
        # Insert the attribute before the closing angle bracket.
        new_tag = tag[:-1] + f" {attribute}>"

    if new_tag != tag:
        updated += 1
    return new_tag

text = opening_tag.sub(add_or_update_attribute, text)

output = source.with_name(source.stem + ".with-etherscan-data" + source.suffix)
output.write_text(text, encoding="utf-8")

print(f"Added or updated Etherscan data attributes: {updated}")
print(f"Wrote: {output}")
