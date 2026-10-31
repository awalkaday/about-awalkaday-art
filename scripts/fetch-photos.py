#!/usr/bin/env python3
"""
Download the Arweave photographs used in the book into the repo, keep a
manifest that ties every file to its token and to the chain, and (optionally)
rewrite the chapters to embed the local copies.

    python3 scripts/fetch-photos.py                    # fetch the embedded photos
    python3 scripts/fetch-photos.py --rewrite          # ...and point chapters at local files
    python3 scripts/fetch-photos.py --no-chain         # skip the on-chain check
    python3 scripts/fetch-photos.py --dry-run          # list what would happen

Keys and names
  * The token ID is the key. Photo names are NOT unique (5 repeat, 30 are ".5"
    variants), so a name is only used to look a token up in the register
    (_chapters/postscript.md), and only when it matches exactly one row.
  * Anything ambiguous goes to data/photos-needs-review.csv. Settle it once in
    data/photo-overrides.csv  (columns: arweave_txid,token_id).

Ties to the chain (manifest columns)
  token_id, contract      from the register
  token_uri               tokenURI(id) read through an Ethereum RPC node
  metadata_image          the image address inside that metadata
  chain_check             "match" when metadata_image contains the txid we
                          downloaded; "mismatch" / "unreachable" otherwise
  sha256                  fixity of the bytes we stored (a txid is NOT a hash
                          of the file, so keep our own)

Only the Python standard library is required; Pillow, when installed, adds
pixel width/height and a square check.
"""
import argparse, csv, hashlib, json, re, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_DEFAULT = "0xE31801C2E58b151C3deD2cB29dA56147b7f27eB1"
IMG_RE = re.compile(r'<img\b[^>]*?>', re.I | re.S)
SRC_RE = re.compile(r'src="(https?://(?:[a-z0-9]+\.)?arweave\.net/([A-Za-z0-9_-]{43}))"')
ALT_RE = re.compile(r'alt="([^"]*)"')
FIELDS = ["token_id", "contract", "title", "date", "instagram_url", "foundation_url",
          "arweave_txid", "arweave_url", "token_uri", "metadata_image", "chain_check",
          "local_path", "sha256", "bytes", "width", "height", "fetched_at", "status"]


def read_register():
    """token_id -> dict(title, date, instagram_url, foundation_url, contract)"""
    text = (ROOT / "_chapters" / "postscript.md").read_text(encoding="utf-8")
    out = {}
    for row in re.findall(r"<tr>(.*?)</tr>", text, flags=re.S)[1:]:
        m = re.search(r'href="(https://foundation\.app/mint/eth/(0x[0-9a-fA-F]+)/(\d+))">([^<]+)<', row)
        if not m:
            continue
        d = re.search(r'href="([^"]*instagram[^"]*)">(\d{4}-\d\d-\d\d)<', row)
        out[int(m.group(3))] = dict(contract=m.group(2), title=m.group(4).strip(), foundation_url=m.group(1),
                                    instagram_url=d.group(1) if d else "", date=d.group(2) if d else "")
    return out


def scan_embeds():
    """[(file, txid, url, alt)] for every Arweave <img> in the chapters and impression.md"""
    files = sorted((ROOT / "_chapters").glob("*.md")) + [ROOT / "impression.md"]
    found = []
    for f in files:
        for tag in IMG_RE.findall(f.read_text(encoding="utf-8")):
            s = SRC_RE.search(tag)
            if s:
                a = ALT_RE.search(tag)
                found.append((f, s.group(2), s.group(1), a.group(1).strip() if a else ""))
    return found


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def http(url, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "walking-memories-fetch/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def retry(fn, tries=4):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # network, HTTP, timeout
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def token_uri(rpc, contract, token_id):
    """ERC-721 tokenURI(uint256) through eth_call; returns the decoded string."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_call",
               "params": [{"to": contract, "data": "0xc87b56dd" + format(token_id, "064x")}, "latest"]}
    body, _ = retry(lambda: http(rpc, json.dumps(payload).encode(), {"Content-Type": "application/json"}, 30))
    res = json.loads(body).get("result", "")
    return decode_abi_string(res)


def decode_abi_string(hexstr):
    raw = bytes.fromhex(hexstr[2:] if hexstr.startswith("0x") else hexstr)
    off = int.from_bytes(raw[0:32], "big")
    n = int.from_bytes(raw[off:off + 32], "big")
    return raw[off + 32: off + 32 + n].decode("utf-8")


def to_http(uri):
    if uri.startswith("ipfs://"):
        return "https://ipfs.io/ipfs/" + uri[7:].replace("ipfs/", "", 1)
    if uri.startswith("ar://"):
        return "https://arweave.net/" + uri[5:]
    return uri


def sniff_ext(data):
    if data[:3] == b"\xff\xd8\xff": return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n": return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP": return ".webp"
    return None


def image_size(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def load_manifest(path):
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {r["arweave_txid"]: r for r in csv.DictReader(f)}


def save_manifest(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in sorted(rows.values(), key=lambda r: (int(r.get("token_id") or 10**6), r["arweave_txid"])):
            w.writerow({k: r.get(k, "") for k in FIELDS})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="assets/photos", help="where to store photos (default assets/photos)")
    ap.add_argument("--manifest", default="data/photos.csv")
    ap.add_argument("--overrides", default="data/photo-overrides.csv")
    ap.add_argument("--rpc", default="https://ethereum-rpc.publicnode.com", help="Ethereum JSON-RPC endpoint")
    ap.add_argument("--no-chain", action="store_true", help="skip the tokenURI check")
    ap.add_argument("--gateway", action="append", default=[], help="extra Arweave gateway tried after the original URL (e.g. https://arweave.net)")
    ap.add_argument("--skip-original", action="store_true", help="use only --gateway addresses")
    ap.add_argument("--rewrite", action="store_true", help="rewrite chapters to embed the local files")
    ap.add_argument("--public-prefix", default="/assets/photos", help="URL path used in rewritten <img src> (baseurl is empty on this site)")
    ap.add_argument("--min-px", type=int, default=1000, help="warn when an image is smaller than this (px)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    out_dir, man_path = ROOT / a.out, ROOT / a.manifest
    register = read_register()
    by_title = {}
    for tid, r in register.items():
        by_title.setdefault(r["title"], []).append(tid)
    overrides = {}
    if (ROOT / a.overrides).exists():
        with (ROOT / a.overrides).open(newline="", encoding="utf-8") as f:
            overrides = {r["arweave_txid"]: int(r["token_id"]) for r in csv.DictReader(f)}

    embeds = scan_embeds()
    by_tx = {}
    for f, tx, url, alt in embeds:
        by_tx.setdefault(tx, dict(url=url, alts=set(), files=set()))
        by_tx[tx]["alts"].add(alt)
        by_tx[tx]["files"].add(f)
    print(f"register rows: {len(register)} | embeds: {len(embeds)} | distinct Arweave images: {len(by_tx)}")

    manifest = load_manifest(man_path)
    review = []
    for tx, info in sorted(by_tx.items()):
        row = manifest.get(tx, {"arweave_txid": tx})
        row["arweave_url"] = info["url"]
        tid = overrides.get(tx)
        if tid is None:
            cands = {t for alt in info["alts"] for t in by_title.get(alt, [])}
            if len(cands) == 1:
                tid = cands.pop()
            else:
                review.append((tx, "; ".join(sorted(info["alts"])), sorted(cands)))
        if tid is not None:
            row.update(token_id=str(tid), **{k: str(v) for k, v in register[tid].items()})
            row["status"] = row.get("status") or "pending"
        else:
            row["status"] = "needs-review"
        manifest[tx] = row

    if a.dry_run:
        for tx, r in manifest.items():
            print(f"  {r.get('token_id','?'):>4}  {r.get('title','(unmatched)'):<24} {tx}")
        print(f"needs review: {len(review)}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    problems = []
    try:
      for tx, row in sorted(manifest.items(), key=lambda kv: int(kv[1].get("token_id") or 10**6)):
          tid = row.get("token_id")
          if not tid:
              continue
          existing = [p for p in out_dir.glob(f"t{int(tid):04d}-*") if p.is_file()]
          if existing and row.get("sha256") and hashlib.sha256(existing[0].read_bytes()).hexdigest() == row["sha256"]:
              row["local_path"] = f"{a.out}/{existing[0].name}"
              print(f"  ok (cached)  t{int(tid):04d}")
          else:
              urls = ([] if a.skip_original else [row["arweave_url"]]) + [g.rstrip("/") + "/" + tx for g in a.gateway]
              if not a.skip_original and "arweave.net/" in row["arweave_url"] and not a.gateway:
                  urls.append("https://arweave.net/" + tx)
              data, err = None, None
              for u in urls:
                  try:
                      data, _ = retry(lambda: http(u, timeout=120))
                      break
                  except Exception as e:
                      err = f"{u}: {e}"
              if data is None:
                  row["status"] = "download-failed"
                  problems.append((tid, tx, err))
                  print(f"  FAILED       t{int(tid):04d}  {err}")
                  continue
              ext = sniff_ext(data)
              if not ext:
                  row["status"] = "not-an-image"
                  problems.append((tid, tx, "not a jpg/png/webp"))
                  continue
              name = f"t{int(tid):04d}-{slug(row['title'])}{ext}"
              tmp = out_dir / (name + ".part")
              tmp.write_bytes(data)
              tmp.replace(out_dir / name)
              row.update(local_path=f"{a.out}/{name}", sha256=hashlib.sha256(data).hexdigest(), bytes=str(len(data)),
                         fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
              print(f"  downloaded   t{int(tid):04d}  {len(data)//1024} KB")
          size = image_size(ROOT / row["local_path"])
          row["status"] = "ok"
          if size:
              row["width"], row["height"] = str(size[0]), str(size[1])
              if size[0] != size[1]:
                  row["status"] = "not-square"
              elif size[0] < a.min_px:
                  row["status"] = "small"
          if not a.no_chain and row.get("chain_check") != "match":
              try:
                  turi = token_uri(a.rpc, row.get("contract") or CONTRACT_DEFAULT, int(tid))
                  meta, _ = retry(lambda: http(to_http(turi), timeout=60))
                  img = json.loads(meta).get("image") or json.loads(meta).get("image_url") or ""
                  row.update(token_uri=turi, metadata_image=img, chain_check="match" if tx in img else "mismatch")
              except Exception as e:
                  row["chain_check"] = "unreachable"
                  print(f"  chain check unreachable for t{int(tid):04d}: {e}")
    finally:
        save_manifest(man_path, manifest)
    if review:
        p = ROOT / "data" / "photos-needs-review.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["arweave_txid", "alt_text_seen", "candidate_token_ids"])
            for tx, alts, c in review:
                w.writerow([tx, alts, " ".join(map(str, c))])
        print(f"{len(review)} image(s) need a token ID: see data/photos-needs-review.csv, answer in {a.overrides}")

    if a.rewrite:
        changed = 0
        for f in sorted((ROOT / "_chapters").glob("*.md")) + [ROOT / "impression.md"]:
            text = f.read_text(encoding="utf-8")
            def sub(m):
                tag = m.group(0)
                s = SRC_RE.search(tag)
                r = manifest.get(s.group(2)) if s else None
                if not r or not r.get("local_path") or r.get("status") in ("download-failed", "not-an-image"):
                    return tag
                attrs = f' data-token="{r["token_id"]}" data-arweave="{s.group(1)}"'
                new = tag.replace(s.group(0), f'src="{a.public_prefix}/{Path(r["local_path"]).name}"')
                return new.replace("<img", "<img" + attrs, 1) if "data-token=" not in new else new
            new_text = IMG_RE.sub(sub, text)
            if new_text != text:
                f.write_text(new_text, encoding="utf-8"); changed += 1
        print(f"rewrote {changed} file(s)")

    counts = {}
    for r in manifest.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("status:", counts, "| chain:", {c: sum(1 for r in manifest.values() if r.get("chain_check") == c) for c in ("match", "mismatch", "unreachable")})
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
