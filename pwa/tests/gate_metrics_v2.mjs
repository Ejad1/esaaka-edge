// Image-quality metrics (computed by the shipped guard.js in the real browser) for the v2 validation + test images,
// so the gate bounds can be re-learned on the pooled v2 VALIDATION set (BRACOL + Uganda + RoCoLe) and judged on test.
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';

const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const RES = path.join(HERE, '../../results');
const BASE = 'D:/Esaaka/hack_nation/data';
const lines = fs.readFileSync(path.join(BASE, 'prepared_v2/splits_v2.csv'), 'utf8').trim().split('\n');
const head = lines[0].split(','); const ix = Object.fromEntries(head.map((h, i) => [h, i]));
const registry = new Map(); const items = [];
for (const l of lines.slice(1)) {
  const c = l.split(','); const split = c[ix.split];
  if (split !== 'val' && split !== 'test') continue;
  const src = c[ix.source], id = c[ix.id];
  const file = src === 'bracol' ? `${BASE}/prepared/images/${id}.jpg` : `${BASE}/prepared_v2/images/${id}`;
  const key = `${src}:${id}`; registry.set(key, file); items.push({ key, src, split, label: Number(c[ix.label]) });
}
const ctx = await chromium.launchPersistentContext(path.join(HERE, '.profile-gv2-' + Date.now()), { channel: 'msedge', headless: true });
await ctx.route('**/__g/**', (route) => {
  const key = decodeURIComponent(route.request().url().split('/__g/')[1]); const f = registry.get(key);
  f ? route.fulfill({ path: f, contentType: 'image/jpeg' }) : route.fulfill({ status: 404, body: 'nf' });
});
const page = await ctx.newPage();
await page.goto(process.env.BASE || 'http://localhost:4173/');
await page.waitForFunction(() => window.__esaaka?.state?.ready === true, null, { timeout: 120000 });
const rows = [];
for (let i = 0; i < items.length; i += 100) {
  const chunk = items.slice(i, i + 100);
  rows.push(...await page.evaluate(async (chunk) => {
    const o = [];
    for (const it of chunk) {
      try {
        const blob = await (await fetch(`/__g/${encodeURIComponent(it.key)}`)).blob();
        const r = await window.__esaaka.evalFile(new File([blob], 'x.jpg', { type: 'image/jpeg' }));
        o.push({ ...it, metrics: r.metrics });
      } catch (e) { o.push({ ...it, error: String(e) }); }
    }
    return o;
  }, chunk));
  if ((i / 100) % 4 === 0) console.log(`${rows.length}/${items.length}`);
}
fs.writeFileSync(path.join(RES, 'gate_v2_rows.json'), JSON.stringify(rows));
console.log('done', rows.length, 'errors', rows.filter((r) => r.error).length);
await ctx.close();
