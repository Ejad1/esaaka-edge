// Input-quality gate (Remedy B). Pure functions on RGBA pixel data of the 448x224 model canvas.
// The same file runs in the PWA and in the evaluation harness, so measured behaviour == shipped behaviour.
// Bounds are LEARNED ON CLEAN VALIDATION IMAGES ONLY (experiments/robustness/guard_eval.py) and shipped in model_config.json.

export const GUARD_W = 448;
export const GUARD_H = 224;
const SAT_LEAF = 0.22; // same saturation threshold as the synthetic-background masks

/** @param {{data: Uint8ClampedArray, width: number, height: number}} img RGBA pixels */
export function guardMetrics(img) {
  const { data, width: w, height: h } = img;
  const n = w * h;
  const lum = new Float32Array(n);
  let sum = 0, dark = 0, bright = 0, leaf = 0;
  for (let i = 0; i < n; i++) {
    const r = data[4 * i], g = data[4 * i + 1], b = data[4 * i + 2];
    const y = 0.299 * r + 0.587 * g + 0.114 * b;
    lum[i] = y; sum += y;
    if (y < 10) dark++;
    if (y > 245) bright++;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
    if ((mx - mn) / (mx + 1e-6) > SAT_LEAF) leaf++;
  }
  const mean = sum / n;
  let v = 0;
  for (let i = 0; i < n; i++) { const d = lum[i] - mean; v += d * d; }
  const contrast = Math.sqrt(v / n);

  // sharpness: variance of the 4-neighbour Laplacian
  let ls = 0, ls2 = 0, c = 0;
  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      const i = y * w + x;
      const lap = lum[i - w] + lum[i + w] + lum[i - 1] + lum[i + 1] - 4 * lum[i];
      ls += lap; ls2 += lap * lap; c++;
    }
  }
  const sharp = ls2 / c - (ls / c) * (ls / c);

  // background busyness: mean |dx|+|dy| over the outer 12% frame (plain sheet => low, soil/foliage/fabric => high)
  const bx = Math.round(w * 0.12), by = Math.round(h * 0.12);
  let g = 0, gc = 0;
  for (let y = 0; y < h - 1; y++) {
    for (let x = 0; x < w - 1; x++) {
      if (x >= bx && x < w - bx && y >= by && y < h - by) continue;
      const i = y * w + x;
      g += Math.abs(lum[i + 1] - lum[i]) + Math.abs(lum[i + w] - lum[i]); gc++;
    }
  }
  return { sharp, mean, contrast, dark: dark / n, bright: bright / n, leaf: leaf / n, border: g / gc };
}

/**
 * @param {ReturnType<typeof guardMetrics>} m
 * @param {Record<string, [number|null, number|null]>} bounds metric -> [min, max] (null = unbounded)
 * @returns {string[]} reasons the photo should be retaken (empty = OK to analyse)
 */
export function guardReasons(m, bounds) {
  const out = (k) => { const b = bounds[k]; return !b ? 0 : (b[0] != null && m[k] < b[0]) ? -1 : (b[1] != null && m[k] > b[1]) ? 1 : 0; };
  const r = [];
  if (out('sharp') < 0) r.push('blur');
  if (out('mean') < 0 || out('dark') > 0) r.push('too_dark');
  if (out('mean') > 0 || out('bright') > 0) r.push('too_bright');
  if (out('contrast') < 0) r.push('low_contrast');
  if (out('border') > 0) r.push('busy_background');
  if (out('leaf') < 0) r.push('no_leaf');
  if (out('leaf') > 0) r.push('background_too_colourful');
  return r;
}
