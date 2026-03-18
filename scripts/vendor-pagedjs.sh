#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/vendor-pagedjs.sh
# Downloads a pinned Paged.js build into assets/js/ so the print layer
# has zero runtime CDN dependency (State B independence requirement).
#
# Run once after cloning the repo:
#   chmod +x scripts/vendor-pagedjs.sh && ./scripts/vendor-pagedjs.sh
#
# To upgrade Paged.js, change PAGEDJS_VERSION and re-run.
# Commit the result — assets/js/paged.polyfill.js is intentionally tracked in git.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

PAGEDJS_VERSION="0.4.3"
TARGET="assets/js/paged.polyfill.js"
CDN_URL="https://unpkg.com/pagedjs@${PAGEDJS_VERSION}/dist/paged.polyfill.js"

# ── Go to repo root regardless of where the script is called from ────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

mkdir -p assets/js

echo "→ Downloading Paged.js ${PAGEDJS_VERSION} from unpkg..."
curl -fSL "${CDN_URL}" -o "${TARGET}"

BYTES=$(wc -c < "${TARGET}")
echo "✓ Saved ${TARGET} (${BYTES} bytes)"
echo ""
echo "Next step: commit the vendored file"
echo "  git add ${TARGET}"
echo "  git commit -m 'vendor: add Paged.js ${PAGEDJS_VERSION} locally'"

# ── Alternative: use npm if curl is unavailable ───────────────────────────────
# npm pack pagedjs@${PAGEDJS_VERSION}
# tar -xzf pagedjs-${PAGEDJS_VERSION}.tgz package/dist/paged.polyfill.js
# mv package/dist/paged.polyfill.js ${TARGET}
# rm -rf pagedjs-${PAGEDJS_VERSION}.tgz package/
