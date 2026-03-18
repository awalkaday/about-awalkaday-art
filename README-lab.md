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

Headless alternative:
```bash
npx @pagedjs/cli http://localhost:4000/impression/ -o walking-memories.pdf
```

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
