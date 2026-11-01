#!/usr/bin/env node
/**
 * Render /impression/ to a PDF from the command line (Chromium + Paged.js).
 *
 *   node scripts/make-pdf.js [url] [out.pdf] [--fx "fx-hide fx-inset"] [--timeout 600] [--placeholder]
 *
 *   url      default http://localhost:4000/impression/  (or the live
 *            https://printlab.awalkaday.art/impression/)
 *   out.pdf  default walking-memories.pdf
 *   --fx     replace the flow-control classes on <body> for this render only,
 *            e.g. --fx ""                         all page-saving switches off
 *                 --fx "fx-inset"                 only inset photos
 *                 --fx "fx-hide fx-inset fx-register"   all on
 *            Omit it to keep whatever _layouts/impression.html sets.
 *
 *   --placeholder  do not download remote images (Arweave etc.): each one is
 *            replaced by a grey 1:1 square. Much faster, and the layout stays
 *            representative because the photos are square.
 *
 *   --strict       exit with code 2 when a chapter that should start a page does not
 *                  (sections with class "sub" are allowed to flow on)
 *   --summary F    also write a short Markdown report to F (used by CI)
 *
 *   Waits for Paged.js itself to report that layout is finished (not just
 *   for the page count to stop growing), so slow image loads cannot cut the
 *   PDF short.
 *
 * Needs:  npm i -D playwright && npx playwright install chromium
 * Prints: the page count, the loaded fonts, and where each chapter starts.
 */
const { chromium } = require('playwright');

const args = process.argv.slice(2);
const opt = (name, dflt) => {
  const i = args.indexOf(name);
  if (i === -1) return dflt;
  return args.splice(i, 2)[1];
};
const fx = opt('--fx', null);
const timeout = Number(opt('--timeout', 600)) * 1000;
const summaryPath = opt('--summary', null);
const si = args.indexOf('--strict');
const strict = si !== -1; if (strict) args.splice(si, 1);
const replaced = [];
const pi = args.indexOf('--placeholder');
const placeholder = pi !== -1; if (placeholder) args.splice(pi, 1);
const url = args[0] || 'http://localhost:4000/impression/';
const out = args[1] || 'walking-memories.pdf';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const problems = [];
  page.on('pageerror', e => problems.push(e.message));
  page.on('requestfailed', r => problems.push('failed: ' + r.url()));

  if (placeholder) {
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000"><rect width="1000" height="1000" fill="#cfcfca"/></svg>';
    const here = new URL(url).host;
    await page.route('**/*', route => {
      const r = route.request();
      if (r.resourceType() === 'image' && new URL(r.url()).host !== here) {
        replaced.push(r.url());
        return route.fulfill({ status: 200, contentType: 'image/svg+xml', body: svg });
      }
      return route.continue();
    });
  }

  // Paged.js calls this when the whole document is laid out
  await page.addInitScript(() => {
    window.PagedConfig = Object.assign(window.PagedConfig || {}, {
      auto: true,
      after: flow => { window.__pagedDone = (flow && flow.total) || true; }
    });
  });

  if (fx !== null) {
    // run before Paged.js starts (it waits for the window load event)
    await page.addInitScript(classes => {
      document.addEventListener('DOMContentLoaded', () => {
        const keep = [...document.body.classList].filter(c => !c.startsWith('fx-'));
        document.body.className = keep.concat(classes.split(/\s+/).filter(Boolean)).join(' ');
      });
    }, fx);
  }

  await page.goto(url, { waitUntil: 'load', timeout });
  await page.waitForFunction(() => window.__pagedDone !== undefined, null, { timeout, polling: 1000 });
  const last = await page.evaluate(() => document.querySelectorAll('.pagedjs_page').length);
  await page.evaluate(() => document.fonts.ready);

  const info = await page.evaluate(() => {
    const pages = [...document.querySelectorAll('.pagedjs_page')];
    const seen = new Set(), starts = [];
    pages.forEach((pg, i) => pg.querySelectorAll('section.chapter').forEach(s => {
      const id = s.dataset.id || s.id;
      if (id && !seen.has(id)) { seen.add(id); starts.push(id + ' → p' + (i + 1)); }
    }));
    // a chapter (not marked "sub") whose first fragment is not at the top of its page
    const notAtTop = [], seen2 = new Set();
    pages.forEach((pg, i) => pg.querySelectorAll('section.chapter').forEach(sec => {
      const id = sec.dataset.id || sec.id;
      if (!id || seen2.has(id) || sec.hasAttribute('data-split-from')) return;
      seen2.add(id);
      if (sec.classList.contains('sub')) return;
      const area = pg.querySelector('.pagedjs_page_content');
      if (sec.getBoundingClientRect().top - area.getBoundingClientRect().top >= 6) notAtTop.push(id + ' (p' + (i + 1) + ')');
    }));
    return { bodyClass: document.body.className, starts, notAtTop };
  });

  await page.pdf({ path: out, preferCSSPageSize: true, printBackground: true });
  console.log(`wrote ${out}: ${last} pages`);
  console.log('body classes:', info.bodyClass);
  console.log('chapter starts:\n  ' + info.starts.join('\n  '));
  if (problems.length) console.log('warnings:\n  ' + problems.slice(0, 10).join('\n  '));
  const mb = require('fs').statSync(out).size / 1048576;
  const remote = [...new Set(replaced)];
  console.log(`size: ${mb.toFixed(1)} MB | chapters not at top of a page: ${info.notAtTop.length}` + (remote.length ? ` | remote images replaced: ${remote.length}` : ''));
  if (info.notAtTop.length) console.log('  ' + info.notAtTop.join('\n  '));
  if (summaryPath) {
    const lines = [`### PDF render`, `- **${last} pages**, ${mb.toFixed(1)} MB${mb > 100 ? ' ⚠️ over 100 MB: are the photos still full size?' : ''}`,
      `- body classes: \`${info.bodyClass}\``,
      `- chapters not starting a page: ${info.notAtTop.length ? info.notAtTop.map(x => '`' + x + '`').join(', ') : 'none'}`,
      `- remote images still referenced: ${remote.length ? '\n' + remote.map(u => '  - ' + u).join('\n') : 'none'}`,
      '', '<details><summary>Chapter start pages</summary>', '', ...info.starts.map(x => '- ' + x), '', '</details>'];
    require('fs').writeFileSync(summaryPath, lines.join('\n') + '\n');
  }
  await browser.close();
  if (strict && info.notAtTop.length) process.exit(2);
})().catch(e => { console.error(e); process.exit(1); });
