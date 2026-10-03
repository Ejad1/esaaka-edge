// Copy the onnxruntime-web WASM runtime next to the app so it is served same-origin and pre-cached for offline use.
import { copyFileSync, mkdirSync } from 'node:fs';
mkdirSync('public/ort', { recursive: true });
for (const f of ['ort-wasm-simd-threaded.wasm', 'ort-wasm-simd-threaded.mjs']) copyFileSync(`node_modules/onnxruntime-web/dist/${f}`, `public/ort/${f}`);
console.log('ort runtime copied');
