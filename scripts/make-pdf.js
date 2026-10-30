#!/usr/bin/env node
/**
 * Render /impression/ to a PDF from the command line (Chromium + Paged.js).
 *
 *   node scripts/make-pdf.js [url] [out.pdf] [--fx "fx-sub fx-hide"] [--timeout 300]
 *
 *   url      default http://localhost:4000/impression/  (or the live
 *            https://printlab.awalkaday.art/impression/)
 *   out.pdf  default walking-memories.pdf
 *   --fx     replace the flow-control classes on <body> for this render only,
 *            e.g. --fx ""                         all page-saving switches off
 *                 --fx "fx-sub"                   only subchapters flow on
 *                 --fx "fx-sub fx-hide fx-inset fx-register"   all on
 *            Omit it to keep whatever _layouts/impression.html sets.
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
const timeout = Number(opt('--timeout', 300)) * 1000;
const url = args[0] || 'http://localhost:4000/impression/';
const out = args[1] || 'walking-memories.pdf';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const problems = [];
  page.on('pageerror', e => problems.push(e.message));
  page.on('requestfailed', r => problems.push('failed: ' + r.url()));

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
  await page.waitForFunction(() => document.querySelectorAll('.pagedjs_page').length > 0, null, { timeout });

  // wait until the page count stops growing for 5 s in a row
  let last = -1, still = 0;
  const t0 = Date.now();
  while (still < 5 && Date.now() - t0 < timeout) {
    await page.waitForTimeout(1000);
    const n = await page.evaluate(() => document.querySelectorAll('.pagedjs_page').length);
    still = n === last ? still + 1 : 0;
    last = n;
  }
  await page.evaluate(() => document.fonts.ready);

  const info = await page.evaluate(() => {
    const pages = [...document.querySelectorAll('.pagedjs_page')];
    const seen = new Set(), starts = [];
    pages.forEach((pg, i) => pg.querySelectorAll('section.chapter').forEach(s => {
      const id = s.dataset.id || s.id;
      if (id && !seen.has(id)) { seen.add(id); starts.push(id + ' → p' + (i + 1)); }
    }));
    return { bodyClass: document.body.className, starts };
  });

  await page.pdf({ path: out, preferCSSPageSize: true, printBackground: true });
  console.log(`wrote ${out}: ${last} pages`);
  console.log('body classes:', info.bodyClass);
  console.log('chapter starts:\n  ' + info.starts.join('\n  '));
  if (problems.length) console.log('warnings:\n  ' + problems.slice(0, 10).join('\n  '));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
