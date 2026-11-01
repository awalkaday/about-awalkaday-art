# awalkaday — printlab branch

Experimental static-site rebuild of the artist's book, served at `printlab.awalkaday.art`.
The live GitBook at `book.awalkaday.art` remains untouched during the transition.

Zero dependency on GitBook infrastructure once `migrate-from-gitbook.py` has been run.

## Stack

| Layer | Tool |
|---|---|
| Content | Plain Markdown (migrated from GitBook `book` branch) |
| Static site generator | Jekyll |
| Web layout | `assets/css/screen.css` |
| Print / PDF layout | `assets/css/print.css` + Paged.js (vendored locally) |
| Hosting | GitHub Pages — Fastly CDN, free, no server to maintain |
| CI/CD | GitHub Actions `.github/workflows/deploy.yml` |

## First-time setup

```bash
# 1. Clone and switch to printlab
git clone https://github.com/awalkaday/about-awalkaday-art.git
cd about-awalkaday-art
git checkout printlab

# 2. Install Ruby dependencies
bundle install

# 3. Vendor Paged.js locally (run once, commit the result)
chmod +x scripts/vendor-pagedjs.sh
./scripts/vendor-pagedjs.sh
git add assets/js/paged.polyfill.js
git commit -m "vendor: add Paged.js locally"

# 4. Migrate content away from GitBook (images + block syntax)
python3 scripts/migrate-from-gitbook.py --dry-run
python3 scripts/migrate-from-gitbook.py
git add -A
git commit -m "migrate: remove all GitBook dependencies"
```

## Local development

```bash
bundle exec jekyll serve --livereload
open http://localhost:4000
open http://localhost:4000/impression/   # print view — use Chromium
```

## Generating the PDF

1. Open `http://localhost:4000/impression/` in Chrome or Chromium
2. Wait for Paged.js to finish rendering (page count appears top-left)
3. File → Print → Destination: Save as PDF
4. More settings: disable "Headers and footers", margins to None
5. Save

Headless (command line), with page counts and chapter start pages:
```bash
npm i -D playwright && npx playwright install chromium     # once
node scripts/make-pdf.js http://localhost:4000/impression/ walking-memories.pdf
node scripts/make-pdf.js https://printlab.awalkaday.art/impression/ live.pdf

# compare the page-saving switches without editing the layout:
node scripts/make-pdf.js http://localhost:4000/impression/ off.pdf --fx ""
node scripts/make-pdf.js http://localhost:4000/impression/ all.pdf --fx "fx-hide fx-inset fx-register"
```
`--fx` replaces the `fx-*` classes on `<body>` for that render only.
Add `--placeholder` to skip downloading the remote photos (each becomes a grey
square): much faster, and good enough to judge page flow.

Page breaks: every `<section class="chapter" …>` in `impression.md` starts a new
page. Add `sub` (`class="chapter sub"`) to let that one flow on from the section
before it.

## PDF on every push (GitHub Actions)

`.github/workflows/pdf.yml` builds the site with Jekyll, renders `/impression/` with
`scripts/make-pdf.js`, and attaches the result to the run (Actions tab, the run, then
**Artifacts**, `walking-memories-pdf`, kept 14 days):

- `walking-memories.pdf`, `summary.md` (pages, size, chapter start pages, remote images still referenced) and `sheets/contact-sheet-NN.png` (thumbnails of every spread).
- The run turns red when a chapter that should start a page does not (`--strict`), and the summary warns when the PDF passes 100 MB, which usually means photos are full size again.
- Run it by hand from the Actions tab with **Run workflow**; the optional `fx` input swaps the `fx-*` classes for that render only.
- The same checks locally: `node scripts/make-pdf.js http://localhost:4000/impression/ out.pdf --strict --summary summary.md` then `python3 scripts/contact-sheets.py out.pdf sheets/`.
- Images on other servers are replaced by grey squares in CI (`--placeholder`), so a slow or dead third-party server cannot break a build; the summary lists which ones are still remote. Mirror them with `python3 scripts/fetch-photos.py --external --rewrite`.

## Photos: local copies tied to the blockchain originals

The chapters embed photographs straight from Arweave, which makes rendering slow
and makes the PDF depend on an outside server. `scripts/fetch-photos.py` downloads
them into `assets/photos/`, keeps a manifest, and can rewrite the chapters:

```bash
python3 scripts/fetch-photos.py --dry-run     # what it found, nothing downloaded
python3 scripts/fetch-photos.py               # download, verify, write data/photos.csv
python3 scripts/fetch-photos.py --rewrite     # also point chapter <img> tags at the local files
```

- **Key = token ID**, taken from the register in `_chapters/postscript.md`. Photo names are not unique, so a name is only used to look a token up, and only when it matches exactly one row.
- **Needs a human:** images whose name matches zero or several tokens (or have no alt text) are listed in `data/photos-needs-review.csv`. Answer in `data/photo-overrides.csv` (`arweave_txid,token_id`) and re-run.
- **Ties kept:** each rewritten `<img>` keeps `data-token` and `data-arweave`. `data/photos.csv` records the txid, `tokenURI`, the image address inside the token metadata, a `chain_check` (`match` / `mismatch` / `unreachable`) and the SHA-256 of the stored file.
- **Re-runnable:** files whose SHA-256 already matches are skipped; failed downloads fall back to `https://arweave.net/<txid>`.
- Options: `--no-chain` (skip the Ethereum lookup), `--rpc URL`, `--gateway URL`, `--out DIR`, `--min-px N`.
- Needs network access to Arweave and an Ethereum RPC node; run it on your computer or in CI. Python 3 only; Pillow is optional (adds width/height and a square check).

## Deploying

```bash
git push origin printlab
```

GitHub Actions builds Jekyll and deploys to GitHub Pages automatically.
Live at https://printlab.awalkaday.art within ~90 seconds.

## DNS

Add one CNAME record at your DNS provider:
```
printlab.awalkaday.art  →  CNAME  →  awalkaday.github.io
```

GitHub Pages issues a free TLS certificate automatically.

## Resilience

- Static files on Fastly CDN via GitHub Pages — no origin server to attack or overload
- No database, no login surface, no dynamic execution
- Paged.js vendored in `assets/js/` — print layer works fully offline
- All content and history in Git — no vendor controls your source

## Screen book: local, light images

`python3 scripts/fetch-photos.py --max-px 1600 --external --rewrite` now also rewrites the web pages
(root and sub-folders, not `_chapters/`): Arweave photos become a local 800 px copy in `assets/photos/web/`
with a `srcset` to the 1600 px print copy; every web image gets `loading="lazy"` and `decoding="async"`
(the home cover photo is eager). `--web-px 0` skips the small copies.
`python3 scripts/shrink-assets.py --apply` shrinks oversized files in `.gitbook/assets` (originals go to `.photo-cache/gitbook/`).
