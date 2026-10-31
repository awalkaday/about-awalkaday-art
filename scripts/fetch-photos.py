#!/usr/bin/env python3
"""
Download the Arweave photographs used in the book into the repo, keep a
manifest that ties every file to its token and to the chain, and (optionally)
rewrite the chapters to embed the local copies.

    python3 scripts/fetch-photos.py                    # fetch the embedded photos
    python3 scripts/fetch-photos.py --rewrite          # ...and point chapters at local files
    python3 scripts/fetch-photos.py --no-chain         # skip the on-chain check
    python3 scripts/fetch-photos.py --dry-run          # list what would happen
    python3 scripts/fetch-photos.py --external --rewrite   # also mirror third-party images (logos...)
    python3 scripts/fetch-photos.py --max-px 1600      # store print-size copies (needs Pillow);
                                                       # originals stay in .photo-cache/ (git-ignored)

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
DATA_AR_RE = re.compile(r'data-arweave="(https?://(?:[a-z0-9]+\.)?arweave\.net/([A-Za-z0-9_-]{43}))"')
ALT_RE = re.compile(r'alt="([^"]*)"')
FIELDS = ["token_id", "contract", "title", "date", "instagram_url", "foundation_url",
          "arweave_txid", "arweave_url", "token_uri", "metadata_image", "chain_check",
          "local_path", "sha256", "bytes", "width", "height",
          "sha256_original", "bytes_original", "orig_width", "orig_height", "derived_px",
          "fetched_at", "status"]


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
            s = SRC_RE.search(tag) or DATA_AR_RE.search(tag)
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


EXT_SRC_RE = re.compile(r'src="(https?://[^"]+)"')


def sniff_ext(data):
    head = data[:512].lstrip()
    if head[:5] == b"<?xml" or head[:4] == b"<svg": return ".svg"
    if data[:4] == b"GIF8": return ".gif"
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


def derive(data, max_px, quality):
    """Return (bytes, ext, (orig_w, orig_h)). Never enlarges; small images are kept as they are."""
    import io
    from PIL import Image, ImageOps
    im = Image.open(io.BytesIO(data))
    orig = im.size
    if max(orig) <= max_px:
        return data, sniff_ext(data), orig
    im = ImageOps.exif_transpose(im)
    if im.mode not in ("L", "RGB"):
        im = im.convert("RGB")
    im.thumbnail((max_px, max_px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue(), ".jpg", orig


def image_size_bytes(data):
    try:
        import io
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
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
    ap.add_argument("--max-px", type=int, default=0, help="store copies no larger than N px on the long side (needs Pillow); 0 = keep originals")
    ap.add_argument("--quality", type=int, default=85, help="JPEG quality for --max-px copies")
    ap.add_argument("--cache", default=".photo-cache", help="where originals are kept when --max-px is used (git-ignored)")
    ap.add_argument("--external", action="store_true", help="also mirror third-party <img> images into assets/external/ (logos, QR codes...)")
    ap.add_argument("--prune", action="store_true", help="delete files in --out that the manifest no longer references")
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

    if a.max_px:
        try:
            import PIL  # noqa: F401
        except ImportError:
            sys.exit("--max-px needs Pillow:  pip install pillow")
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = ROOT / a.cache
    problems = []

    # a token can have several Arweave files (e.g. the minted one and a variant used in a
    # chapter): give each its own filename so they never overwrite each other
    txs_of = {}
    for tx, r in manifest.items():
        if r.get("token_id"):
            txs_of.setdefault(r["token_id"], []).append(tx)

    def target_name(row, tx, ext):
        base = f"t{int(row['token_id']):04d}-{slug(row['title'])}"
        if len(txs_of[row["token_id"]]) > 1:
            base += "-" + re.sub(r"[^A-Za-z0-9]", "", tx)[:6].lower()
        return base + ext

    sha = lambda b: hashlib.sha256(b).hexdigest()
    try:
        for tx, row in sorted(manifest.items(), key=lambda kv: int(kv[1].get("token_id") or 10**6)):
            tid = row.get("token_id")
            if not tid:
                continue
            tag = f"t{int(tid):04d}"
            lp = ROOT / row["local_path"] if row.get("local_path") else None
            # manifests from the first version had no *_original columns: sha256 WAS the original
            orig_sha = row.get("sha256_original") or (row.get("sha256") if not row.get("derived_px") else "")
            done = (lp and lp.is_file() and row.get("sha256") and sha(lp.read_bytes()) == row["sha256"]
                    and str(a.max_px) == (row.get("derived_px") or "0")
                    and lp.stem == Path(target_name(row, tx, lp.suffix)).stem)
            if done:
                print(f"  ok (cached)  {tag}")
            else:
                data = None
                for ext in (".jpg", ".png", ".webp"):          # 1. the originals cache
                    c = cache_dir / f"{tx}{ext}"
                    if c.is_file():
                        d = c.read_bytes()
                        if not orig_sha or sha(d) == orig_sha:
                            data = d
                            break
                if data is None and lp and lp.is_file() and orig_sha and sha(lp.read_bytes()) == orig_sha:
                    data = lp.read_bytes()                      # 2. the repo file IS the original (migration)
                if data is None:                                # 3. download
                    urls = ([] if a.skip_original else [row["arweave_url"]]) + [g.rstrip("/") + "/" + tx for g in a.gateway]
                    if not a.skip_original and "arweave.net/" in row["arweave_url"] and not a.gateway:
                        urls.append("https://arweave.net/" + tx)
                    err = None
                    for u in urls:
                        try:
                            data, _ = retry(lambda: http(u, timeout=120))
                            break
                        except Exception as e:
                            err = f"{u}: {e}"
                    if data is None:
                        row["status"] = "download-failed"
                        problems.append((tid, tx, err))
                        print(f"  FAILED       {tag}  {err}")
                        continue
                    row["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    print(f"  downloaded   {tag}  {len(data)//1024} KB")
                oext = sniff_ext(data)
                if not oext:
                    row["status"] = "not-an-image"
                    problems.append((tid, tx, "not a jpg/png/webp"))
                    continue
                row.update(sha256_original=sha(data), bytes_original=str(len(data)))
                final, ext, osize = data, oext, image_size_bytes(data)
                if a.max_px:
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    (cache_dir / f"{tx}{oext}").write_bytes(data)
                    final, ext, osize = derive(data, a.max_px, a.quality)
                name = target_name(row, tx, ext)
                tmp = out_dir / (name + ".part")
                tmp.write_bytes(final)
                tmp.replace(out_dir / name)
                row.update(local_path=f"{a.out}/{name}", sha256=sha(final), bytes=str(len(final)), derived_px=str(a.max_px))
                if osize:
                    row["orig_width"], row["orig_height"] = str(osize[0]), str(osize[1])
                if a.max_px:
                    print(f"  stored       {tag}  {len(data)//1024} KB -> {len(final)//1024} KB")
            size = image_size(ROOT / row["local_path"])
            row["status"] = "ok"
            if size:
                row["width"], row["height"] = str(size[0]), str(size[1])
            ow, oh = int(row.get("orig_width") or 0), int(row.get("orig_height") or 0)
            ow, oh = (ow, oh) if ow else (size or (0, 0))
            if ow and ow != oh:
                row["status"] = "not-square"
            elif ow and ow < a.min_px:
                row["status"] = "small"
            if not a.no_chain and row.get("chain_check") != "match":
                try:
                    turi = token_uri(a.rpc, row.get("contract") or CONTRACT_DEFAULT, int(tid))
                    meta, _ = retry(lambda: http(to_http(turi), timeout=60))
                    img = json.loads(meta).get("image") or json.loads(meta).get("image_url") or ""
                    row.update(token_uri=turi, metadata_image=img, chain_check="match" if tx in img else "mismatch")
                except Exception as e:
                    row["chain_check"] = "unreachable"
                    print(f"  chain check unreachable for {tag}: {e}")
    finally:
        save_manifest(man_path, manifest)

    keep = {Path(r["local_path"]).name for r in manifest.values() if r.get("local_path")}
    stale = sorted(p for p in out_dir.iterdir() if p.is_file() and p.name not in keep and p.suffix in (".jpg", ".png", ".webp"))
    for p in stale:
        if a.prune:
            p.unlink(); print(f"  pruned       {p.name}")
        else:
            print(f"  stale file (not in manifest; --prune removes it): {a.out}/{p.name}")
    if review:
        p = ROOT / "data" / "photos-needs-review.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["arweave_txid", "alt_text_seen", "candidate_token_ids"])
            for tx, alts, c in review:
                w.writerow([tx, alts, " ".join(map(str, c))])
        print(f"{len(review)} image(s) need a token ID: see data/photos-needs-review.csv, answer in {a.overrides}")

    if a.external:
        ext_dir, ext_path = ROOT / "assets" / "external", ROOT / "data" / "external-images.csv"
        ext_fields = ["url", "local_path", "sha256", "bytes", "status", "fetched_at"]
        ext_rows = {}
        if ext_path.exists():
            with ext_path.open(newline="", encoding="utf-8") as f:
                ext_rows = {r["url"]: r for r in csv.DictReader(f)}
        files = sorted((ROOT / "_chapters").glob("*.md")) + [ROOT / "impression.md"]
        urls = []
        for f in files:
            for tag in IMG_RE.findall(f.read_text(encoding="utf-8")):
                m = EXT_SRC_RE.search(tag)
                if m and "arweave.net/" not in m.group(1) and m.group(1) not in urls:
                    urls.append(m.group(1))
        print(f"third-party images: {len(urls)}")
        ext_dir.mkdir(parents=True, exist_ok=True)
        for u in urls:
            r = ext_rows.get(u, {"url": u})
            lp = ROOT / r["local_path"] if r.get("local_path") else None
            if lp and lp.is_file() and r.get("sha256") == hashlib.sha256(lp.read_bytes()).hexdigest():
                print(f"  ok (cached)  {u[:80]}")
            else:
                try:
                    data, _ = retry(lambda: http(u, timeout=60))
                    ext = sniff_ext(data)
                    if not ext:
                        raise ValueError("not an image")
                    if a.max_px and ext == ".jpg":              # never JPEG-ify PNG/SVG: logos need transparency
                        data, ext, _ = derive(data, a.max_px, a.quality)
                    base = slug(Path(u.split("?")[0]).stem)[:40] or "image"
                    h = hashlib.sha256(data).hexdigest()
                    name = f"{base}-{h[:8]}{ext}"
                    (ext_dir / name).write_bytes(data)
                    r.update(local_path=f"assets/external/{name}", sha256=h, bytes=str(len(data)),
                             status="ok", fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
                    print(f"  downloaded   {name}  {len(data)//1024} KB")
                except Exception as e:
                    r["status"] = "download-failed"
                    print(f"  FAILED       {u[:80]}: {e}")
            ext_rows[u] = r
        with ext_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=ext_fields); w.writeheader()
            for r in sorted(ext_rows.values(), key=lambda r: r["url"]):
                w.writerow({k: r.get(k, "") for k in ext_fields})
        if a.rewrite:
            changed = 0
            for f in files:
                text = f.read_text(encoding="utf-8")
                def sub_ext(m):
                    tag = m.group(0)
                    mm = EXT_SRC_RE.search(tag)
                    r = ext_rows.get(mm.group(1)) if mm else None
                    if not r or r.get("status") != "ok" or "arweave.net/" in mm.group(1):
                        return tag
                    return tag.replace(mm.group(0), f'src="/{r["local_path"]}"').replace("<img", f'<img data-src-original="{mm.group(1)}"', 1)
                new_text = IMG_RE.sub(sub_ext, text)
                if new_text != text:
                    f.write_text(new_text, encoding="utf-8"); changed += 1
            print(f"rewrote {changed} file(s) for third-party images")

    if a.rewrite:
        changed = 0
        for f in sorted((ROOT / "_chapters").glob("*.md")) + [ROOT / "impression.md"]:
            text = f.read_text(encoding="utf-8")
            def sub(m):
                tag = m.group(0)
                s = SRC_RE.search(tag) or DATA_AR_RE.search(tag)
                r = manifest.get(s.group(2)) if s else None
                if not r or not r.get("local_path") or r.get("status") in ("download-failed", "not-an-image"):
                    return tag
                local = f'src="{a.public_prefix}/{Path(r["local_path"]).name}"'
                if "data-arweave=" in tag:                       # already rewritten: just refresh src
                    return re.sub(r'src="[^"]*"', local, tag, count=1)
                attrs = f' data-token="{r["token_id"]}" data-arweave="{s.group(1)}"'
                return tag.replace(s.group(0), local).replace("<img", "<img" + attrs, 1)
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
