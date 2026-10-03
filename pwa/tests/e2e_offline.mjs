// End-to-end OFFLINE test of the shipped PWA (Edge via Playwright, mobile viewport).
//   1) load while online -> service worker precaches everything
//   2) force the browser OFFLINE, reload, run a real photo through the UI (result, saved observation, history)
//   3) push all 202 held-out test images through the exact shipped pipeline, still offline, and compare with Python
// Run:  npx vite preview --port 4173   (in another shell)   then   node tests/e2e_offline.mjs
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';

const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const RES = path.join(HERE, '../../results');
const PREP = 'D:/Esaaka/hack_nation/data/prepared';
const RAW = 'D:/Esaaka/hack_nation/data/bracol/coffee-datasets/coffee-datasets/leaf/images';
const BASE = process.env.BASE || 'http://localhost:4173/';
const py = JSON.parse(fs.readFileSync(path.join(RES, '_py_test_top1.json'), 'utf8'));
const ids = Object.keys(py);
fs.mkdirSync(path.join(RES, 'plots'), { recursive: true });

const ctx = await chromium.launchPersistentContext(path.join(HERE, '.profile-' + Date.now()), {
  channel: 'msedge', headless: true, viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, hasTouch: true,
});
const page = await ctx.newPage();
const failed = [], consoleErrors = [];
page.on('requestfailed', (r) => failed.push(r.url()));
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
const out = { base: BASE, steps: {} };

// 1) online load + precache
await page.goto(BASE); await page.waitForSelector('#take', { timeout: 60000 });
await page.evaluate(() => navigator.serviceWorker.ready);
await page.waitForFunction(async () => { for (const k of await caches.keys()) { if ((await (await caches.open(k)).keys()).length >= 14) return true; } return false; }, null, { timeout: 120000 });
out.steps.precached = await page.evaluate(async () => { const r = {}; for (const k of await caches.keys()) r[k] = (await (await caches.open(k)).keys()).length; return r; });

// 2) OFFLINE
await ctx.setOffline(true);
await page.reload(); await page.waitForSelector('#take', { timeout: 60000 });
out.steps.offline_loaded = { onLine: await page.evaluate(() => navigator.onLine), badge: await page.textContent('#net') };
await page.screenshot({ path: path.join(RES, 'plots/e2e_1_home_offline.png') });
await page.waitForFunction(() => window.__esaaka?.state?.ready === true, null, { timeout: 60000 });   // model loaded from cache

const uiImages = [['rust', ids.find((i) => py[i].y === 2)], ['healthy', ids.find((i) => py[i].y === 0)]];
out.steps.ui = [];
for (const [label, id] of uiImages) {
  await page.click('nav button:first-child');
  await page.setInputFiles('#gallery', path.join(RAW, id + '.jpg'));
  await page.waitForSelector('#tier-high, #tier-medium, #tier-low, #tier-guard', { timeout: 90000 });
  const tier = await page.evaluate(() => [...document.querySelectorAll('[id^=tier-]')].map((e) => e.id)[0]);
  const text = (await page.textContent('main')).replace(/\s+/g, ' ').slice(0, 260);
  await page.screenshot({ path: path.join(RES, `plots/e2e_2_result_${label}.png`), fullPage: true });
  out.steps.ui.push({ truth: label, id, tier, text });
}
await page.click('nav button:last-child'); await page.waitForSelector('.obs');
out.steps.history_count = await page.locator('.obs').count();
await page.screenshot({ path: path.join(RES, 'plots/e2e_3_history.png'), fullPage: true });
const stored = await page.evaluate(async () => (await window.indexedDB.databases()).map((d) => d.name));
out.steps.indexeddb = stored;

// 3) all held-out test images through the exact shipped pipeline, offline
await ctx.route('**/__t/*', (route) => {
  const id = route.request().url().split('/__t/')[1].replace('.jpg', '');
  route.fulfill({ path: path.join(PREP, 'images', id + '.jpg'), contentType: 'image/jpeg' });
});
const rows = await page.evaluate(async (list) => {
  const o = [];
  for (const id of list) {
    const blob = await (await fetch('/__t/' + id + '.jpg')).blob();
    const r = await window.__esaaka.evalFile(new File([blob], id + '.jpg', { type: 'image/jpeg' }));
    o.push({ id, reasons: r.reasons, tier: r.res?.tier ?? 'guard', top1: r.res?.top1 ?? null, p1: r.res?.p1 ?? null, ms: r.res?.ms ?? null, metrics: r.metrics });
  }
  return o;
}, ids);
fs.writeFileSync(path.join(RES, 'e2e_batch_rows.json'), JSON.stringify(rows));
const scored = rows.filter((r) => r.top1 !== null);
const acc = scored.filter((r) => r.top1 === py[r.id].y).length / scored.length;
const agree = scored.filter((r) => r.top1 === py[r.id].top1).length / scored.length;
const f1 = (() => { let s = 0; for (let c = 0; c < 5; c++) { const tp = scored.filter((r) => r.top1 === c && py[r.id].y === c).length, fp = scored.filter((r) => r.top1 === c && py[r.id].y !== c).length, fn = scored.filter((r) => r.top1 !== c && py[r.id].y === c).length; s += tp + fp + fn ? (2 * tp) / (2 * tp + fp + fn) : 0; } return s / 5; })();
const ms = scored.map((r) => r.ms).sort((a, b) => a - b);
out.steps.batch_offline = { n: rows.length, scored: scored.length, guard_rejected: rows.length - scored.length, accuracy_in_browser: acc, macro_f1_in_browser: f1,
  top1_agreement_with_python: agree, tiers: Object.fromEntries(['high', 'medium', 'low', 'guard'].map((t) => [t, rows.filter((r) => r.tier === t).length])),
  inference_ms_median: ms[Math.floor(ms.length / 2)], inference_ms_p95: ms[Math.floor(ms.length * 0.95)] };
out.requests_failed_while_testing = failed.filter((u) => !u.includes('/__t/'));
out.console_errors = consoleErrors.slice(0, 5);
fs.writeFileSync(path.join(RES, 'e2e_offline.json'), JSON.stringify(out, null, 2));
console.log(JSON.stringify(out.steps.batch_offline, null, 1), '\nui:', JSON.stringify(out.steps.ui.map((u) => [u.truth, u.tier])), '| history', out.steps.history_count, '| failed', out.requests_failed_while_testing.length);
await ctx.close();
