// Browser latency / parity / memory benchmark for the candidate ONNX models.
// onnxruntime-web (WASM, 1 thread, SIMD) in Microsoft Edge driven by Playwright. CPU throttling is EMULATED via CDP.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { chromium } from 'playwright-core';

const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm', '.json': 'application/json', '.onnx': 'application/octet-stream', '.bin': 'application/octet-stream', '.jpg': 'image/jpeg' };
const ROUTES = { '/dist/': path.join(HERE, 'node_modules/onnxruntime-web/dist/'), '/models/': path.join(HERE, 'models/'), '/data/': path.join(HERE, 'data/') };

const server = http.createServer((req, res) => {
  const url = decodeURIComponent(req.url.split('?')[0]);
  let file = url === '/' ? path.join(HERE, 'bench.html') : null;
  for (const [prefix, dir] of Object.entries(ROUTES)) if (url.startsWith(prefix)) file = path.join(dir, url.slice(prefix.length));
  if (!file || !fs.existsSync(file)) { res.writeHead(404); return res.end('nf'); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' }); fs.createReadStream(file).pipe(res);
}).listen(8123);

const profile = path.join(HERE, '.edge-profile');
const wsMB = () => {   // working set of the Edge processes launched with our private profile
  try {
    const out = execSync(`powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \\"Name='msedge.exe'\\" | Where-Object { $_.CommandLine -like '*edge-profile*' } | ForEach-Object { (Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue).WorkingSet64 } | Measure-Object -Sum).Sum"`, { encoding: 'utf8' }).trim();
    return Number(out) / 1e6;
  } catch { return NaN; }
};

const models = process.argv.slice(2).length ? process.argv.slice(2) : JSON.parse(fs.readFileSync(path.join(HERE, 'data/meta.json'))).models && Object.keys(JSON.parse(fs.readFileSync(path.join(HERE, 'data/meta.json'))).models);
const results = [];
const browser = await chromium.launchPersistentContext(profile, { channel: 'msedge', headless: true });
for (const key of models) {
  const page = await browser.newPage();
  await page.goto('http://localhost:8123/');
  const cdp = await browser.newCDPSession(page);
  await page.evaluate(() => window.inputs());
  await page.evaluate((k) => { window.currentKey = k; }, key);
  const mem0 = wsMB();
  const load = await page.evaluate((k) => window.loadSession(k), key);
  const parity = await page.evaluate((k) => window.parity(k), key);
  const canvasParity = await page.evaluate(() => window.canvasParity());
  const row = { model: key, bytes: load.bytes, loadMs: Math.round(load.loadMs), parity, canvasParity };
  for (const rate of [1, 4, 6]) {
    await cdp.send('Emulation.setCPUThrottlingRate', { rate });
    row[`latency_x${rate}`] = await page.evaluate((n) => window.timeRuns(3, n), rate === 1 ? 25 : 12);
  }
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 });
  row.memDeltaMB = Math.round(wsMB() - mem0);
  results.push(row);
  console.log(key, 'x1 median', row.latency_x1.median.toFixed(1), 'ms | x4', row.latency_x4.median.toFixed(1), '| x6', row.latency_x6.median.toFixed(1), '| load', row.loadMs, 'ms | parity maxdiff', row.parity.maxAbsDiff.toExponential(2), 'agree', row.parity.argmaxAgree + '/' + row.parity.n, '| canvas agree', row.canvasParity.argmaxAgree + '/' + row.canvasParity.n, 'maxdiff', row.canvasParity.maxAbsDiff.toFixed(2), '| memΔ', row.memDeltaMB, 'MB');
  await page.close();
}
await browser.close(); server.close();
fs.writeFileSync(path.join(HERE, '../../../results/browser_latency.json'), JSON.stringify({ env: { browser: 'Microsoft Edge (headless, Playwright)', ort: 'onnxruntime-web 1.30.0', ep: 'wasm', threads: 1, note: 'Dev laptop CPU; x4/x6 = EMULATED CPU throttling, not a real phone' }, results }, null, 2));
