import * as ort from 'onnxruntime-web/wasm';
import { toTensorData, MODEL_W, MODEL_H } from './preprocess.js';

ort.env.wasm.wasmPaths = new URL('./ort/', document.baseURI).href;
ort.env.wasm.numThreads = 1;

let session = null, config = null;

export async function loadModel() {
  if (session) return config;
  config = await (await fetch(new URL('./models/model_config.json', document.baseURI))).json();
  const bytes = await (await fetch(new URL(`./models/${config.model_file}`, document.baseURI))).arrayBuffer();
  session = await ort.InferenceSession.create(bytes, { executionProviders: ['wasm'], graphOptimizationLevel: 'all' });
  return config;
}

function softmax(z, T) {
  const s = z.map((v) => v / T), m = Math.max(...s), e = s.map((v) => Math.exp(v - m)), t = e.reduce((a, b) => a + b, 0);
  return e.map((v) => v / t);
}

/** Returns calibrated probabilities, ranking, and the confidence tier (high / medium / low = abstain). */
export async function classify(imageData) {
  const t0 = performance.now();
  const input = new ort.Tensor('float32', toTensorData(imageData), [1, 3, MODEL_H, MODEL_W]);
  const out = await session.run({ input });
  const probs = softmax(Array.from(out.logits.data), config.temperature);
  const order = probs.map((p, i) => [p, i]).sort((a, b) => b[0] - a[0]);
  const [p1, i1] = order[0], [p2, i2] = order[1], margin = p1 - p2;
  const th = config.thresholds;
  const isOther = config.labels?.[i1] === 'other';   // 6th class: several/unknown problems -> never a diagnosis
  const tier = isOther ? 'low' : p1 >= th.high && margin >= th.margin ? 'high' : p1 >= th.medium ? 'medium' : 'low';
  return { probs, top1: i1, top2: i2, p1, p2, margin, tier, ms: Math.round(performance.now() - t0) };
}
