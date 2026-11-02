#!/usr/bin/env python3
"""
Publish the register of photographs as machine-readable data: photographs.json (schema.org JSON-LD).

    python3 scripts/build-jsonld.py [--base https://printlab.awalkaday.art] [--out photographs.json]

One `Photograph` per token (all 263, from the register in _chapters/postscript.md): token ID, title,
publication date, token and Instagram links, the contract address; and, for the photographs mirrored in
this repo (data/photos.csv), the Arweave original, the local copies (print 1600 px / web 800 px), pixel
size and SHA-256. Re-run after fetch-photos.py. Standard library only.
"""
import argparse, csv, importlib.util, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--base")
ap.add_argument("--out", default="photographs.json")
a = ap.parse_args()
cfg = (ROOT / "_config.yml").read_text(encoding="utf-8-sig")
base = (a.base or re.search(r'^url:\s*"([^"]+)"', cfg, re.M).group(1)).rstrip("/")

spec = importlib.util.spec_from_file_location("fp", ROOT / "scripts" / "fetch-photos.py")
fp = importlib.util.module_from_spec(spec); sys.argv = ["x"]; spec.loader.exec_module(fp)
register = fp.read_register()
mirrored = {}
with (ROOT / "data" / "photos.csv").open(newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r.get("token_id") and r.get("local_path") and r.get("status") not in ("download-failed", "not-an-image"):
            mirrored[int(r["token_id"])] = r

LICENSE = "https://creativecommons.org/licenses/by-nc-nd/4.0/"
creator = {"@type": "Person", "name": "Chris-Armel Iradukunda", "alternateName": "daqhris", "url": "https://daqhris.com"}
graph = []
for tid in sorted(register):
    r = register[tid]
    node = {"@type": "Photograph", "@id": f"{base}/photographs.json#token-{tid}", "name": r["title"],
            "identifier": {"@type": "PropertyValue", "propertyID": "ERC-721 token ID", "value": str(tid)},
            "creator": creator, "license": LICENSE, "isPartOf": {"@id": f"{base}/photographs.json#series"}}
    if r["date"]:
        node["datePublished"] = r["date"]
    same = [u for u in (r["foundation_url"], r["instagram_url"]) if u]
    if same:
        node["sameAs"] = same
    node["contentLocation"] = {"@type": "Country", "name": "Belgium"}
    m = mirrored.get(tid)
    if m:
        name = Path(m["local_path"]).name
        node["contentUrl"] = f"{base}/assets/photos/{name}"
        node["thumbnailUrl"] = f"{base}/assets/photos/web/{name}"
        node["encodingFormat"] = "image/jpeg"
        if m.get("orig_width"):
            node["width"] = {"@type": "QuantitativeValue", "value": int(m["orig_width"]), "unitCode": "E37"}
            node["height"] = {"@type": "QuantitativeValue", "value": int(m["orig_height"]), "unitCode": "E37"}
        if m.get("arweave_url"):
            node["isBasedOn"] = m["arweave_url"]
        if m.get("sha256"):
            node["identifier"] = [node["identifier"], {"@type": "PropertyValue", "propertyID": "SHA-256 of the local copy", "value": m["sha256"]}]
        if m.get("chain_check") == "match":
            node["description"] = "Image verified against the token's on-chain metadata."
    graph.append(node)
doc = {"@context": "https://schema.org",
       "@graph": [{"@type": "CreativeWorkSeries", "@id": f"{base}/photographs.json#series", "name": "awalkaday",
                   "description": "263 photographs shot on walks across Belgium, 2017–2024, minted as tokens on Ethereum.",
                   "creator": creator, "license": LICENSE,
                   "identifier": {"@type": "PropertyValue", "propertyID": "Ethereum contract", "value": fp.CONTRACT_DEFAULT}}] + graph}
out = ROOT / a.out
out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"wrote {a.out}: {len(graph)} photographs, {len(mirrored)} with local copies, {out.stat().st_size // 1024} KB")
