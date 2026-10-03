// Run the SHIPPED pipeline (crop -> quality metrics -> model -> tiers) in the browser on every evaluation family and
// store raw metrics + model outputs. The gate bounds are applied afterwards in Python (guard_eval.py), because they
// must be learned from the clean-validation rows produced here.
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';

const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const RES = path.join(HERE, '../../results');
const BASE = 'D:/Esaaka/hack_nation/data';
const URL_BASE = process.env.BASE || 'http://localhost:4173/';
const NAMES = ['clean', 'blur_mild', 'blur_strong', 'bright_dark', 'bright_light', 'contrast_low', 'contrast_high', 'jpeg_q12', 'rotate15', 'bg_clutter', 'combined', 'bg_uniform'];

const splits = fs.readFileSync(path.join(BASE, 'prepared/splits_seed42.csv'), 'utf8').trim().split('\n').slice(1).map((l) => l.split(','));
const idsOf = (sp) => splits.filter((r) => r[3].trim() === sp).map((r) => r[0]);
const registry = new Map(); const sets = {};
const add = (set, id, file) => { registry.set(`${set}/${id}`, file); (sets[set] ||= []).push(id); };
for (const id of idsOf('val')) add('val_clean', id, `${BASE}/prepared/images/${id}.jpg`);
for (const id of idsOf('holdout_multi')) add('multi_clean', id, `${BASE}/prepared/images/${id}.jpg`);
for (const n of NAMES) for (const id of idsOf('test')) add(`test_${n}`, id, n === 'clean' ? `${BASE}/prepared/images/${id}.jpg` : `${BASE}/guard_eval/${n}/${id}.jpg`);
// external field sets: same seeded subset logic as experiments/datasets/eval_external.py
let seed = 0; const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
for (const c of ['healthy', 'rust', 'phoma']) {
  const d = `${BASE}/external/uganda/${c}`;
  const fs_ = fs.readdirSync(d).filter((f) => fs.statSync(path.join(d, f)).size > 0).sort();
  for (let i = fs_.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [fs_[i], fs_[j]] = [fs_[j], fs_[i]]; }
  for (const f of fs_.slice(0, 600)) add(`uganda_${c}`, f, path.join(d, f));
}
const roc = fs.readFileSync(path.join(BASE, 'external/rocole/sample.csv'), 'utf8').trim().split('\n').slice(1).map((l) => l.split(','));
for (const [file, label] of roc) { const p = `${BASE}/external/rocole/images/${file}`; if (fs.existsSync(p) && fs.statSync(p).size > 0) add(`rocole_${label.trim()}`, file, p); }

const ctx = await chromium.launchPersistentContext(path.join(HERE, '.profile-sys-' + Date.now()), { channel: 'msedge', headless: true });
await ctx.route('**/__s/**', (route) => {
  const key = decodeURIComponent(route.request().url().split('/__s/')[1]);
  const f = registry.get(key); f ? route.fulfill({ path: f, contentType: 'image/jpeg' }) : route.fulfill({ status: 404, body: 'nf' });
});
const page = await ctx.newPage();
await page.goto(URL_BASE); await page.waitForFunction(() => window.__esaaka?.state?.ready === true, null, { timeout: 120000 });
const rows = []; let n = 0; const total = [...registry.keys()].length;
for (const [set, ids] of Object.entries(sets)) {
  for (let i = 0; i < ids.length; i += 150) {
    const chunk = ids.slice(i, i + 150);
    const out = await page.evaluate(async ({ set, chunk }) => {
      const o = [];
      for (const id of chunk) {
        try {
          const blob = await (await fetch(`/__s/${encodeURIComponent(set + '/' + id)}`)).blob();
          const r = await window.__esaaka.evalFile(new File([blob], id, { type: blob.type || 'image/jpeg' }));
          o.push({ set, id, metrics: r.metrics, tier: r.res?.tier ?? 'guard', top1: r.res?.top1 ?? null, p1: r.res?.p1 ?? null, p2: r.res?.p2 ?? null, margin: r.res?.margin ?? null, ms: r.res?.ms ?? null });
        } catch (e) { o.push({ set, id, error: String(e) }); }
      }
      return o;
    }, { set, chunk });
    rows.push(...out); n += chunk.length;
    if (n % 600 < 150) console.log(`${n}/${total}  (${set})`);
  }
}
fs.writeFileSync(path.join(RES, 'system_eval_rows.json'), JSON.stringify(rows));
console.log('rows', rows.length, 'errors', rows.filter((r) => r.error).length, 'sets', Object.keys(sets).length);
await ctx.close();
