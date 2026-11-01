import re
import sys
from pathlib import Path

CONTRACT = "0xe31801c2e58b151c3ded2cb29da56147b7f27eb1"
MANIFOLD_REF = "1785897200"

# Match complete Foundation mint URLs.
foundation_url = re.compile(
    r"https?://(?:www\.)?foundation\.app/mint/eth/"
    r"(0x[a-fA-F0-9]{40})/(\d+)"
)

# Match ordinary Markdown links whose target is a Foundation mint URL.
markdown_link = re.compile(
    r"\[([^\]]*)\]\("
    r"(https?://(?:www\.)?foundation\.app/mint/eth/"
    r"(0x[a-fA-F0-9]{40})/(\d+))"
    r"\)"
)

counts = {"markdown_links": 0, "plain_urls": 0}

def manifold_url(token_id):
    return f"https://manifold.xyz/@daqhris/contract/{MANIFOLD_REF}/{token_id}"

def etherscan_url(token_id):
    return f"https://etherscan.io/nft/{CONTRACT}/{token_id}"

def replace_markdown_link(match):
    label, _url, address, token_id = match.groups()
    if address.lower() != CONTRACT:
        return match.group(0)

    counts["markdown_links"] += 1
    if "foundation" in label.lower():
        label = re.sub("foundation", "Manifold", label, flags=re.IGNORECASE)
    elif not label:
        label = "Manifold"

    return (
        f"[{label}]({manifold_url(token_id)})"
        f" · [Etherscan]({etherscan_url(token_id)})"
    )

def replace_plain_url(match):
    address, token_id = match.groups()
    if address.lower() != CONTRACT:
        return match.group(0)

    counts["plain_urls"] += 1
    return manifold_url(token_id)

if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 convert_links.py postscript.md")

source = Path(sys.argv[1])
text = source.read_text(encoding="utf-8")

# Convert Markdown links first so the secondary Etherscan link can be added.
text = markdown_link.sub(replace_markdown_link, text)
text = foundation_url.sub(replace_plain_url, text)

output = source.with_name(source.stem + ".manifold" + source.suffix)
output.write_text(text, encoding="utf-8")

print(f"Wrote: {output}")
print(f"Converted Markdown links: {counts['markdown_links']}")
print(f"Converted plain URLs: {counts['plain_urls']}")

# Show any remaining Foundation mint URLs for review.
remaining = sorted(set(re.findall(
    r"https?://(?:www\.)?foundation\.app/mint/eth/[^\s)>]+", text
)))
if remaining:
    print("\nFoundation URLs left for manual review:")
    for url in remaining:
        print(url)
