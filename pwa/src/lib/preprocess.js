// Photo -> 2:1 centre crop -> 512x256 (stored preview) -> 448x224 model canvas -> normalised CHW tensor.
// Mirrors the training pipeline (2:1 images resized to 512x256 then 448x224, ImageNet normalisation).
const MEAN = [0.485, 0.456, 0.406];
const STD = [0.229, 0.224, 0.225];
export const MODEL_W = 448, MODEL_H = 224;

export async function prepare(file) {
  const bmp = await createImageBitmap(file, { imageOrientation: 'from-image' });
  const aspect = bmp.width / bmp.height;
  let sx = 0, sy = 0, sw = bmp.width, sh = bmp.height;
  if (aspect > 2) { sw = bmp.height * 2; sx = (bmp.width - sw) / 2; } else { sh = bmp.width / 2; sy = (bmp.height - sh) / 2; }
  const big = new OffscreenCanvas(512, 256);
  const g = big.getContext('2d');
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
  g.drawImage(bmp, sx, sy, sw, sh, 0, 0, 512, 256);
  const small = new OffscreenCanvas(MODEL_W, MODEL_H);
  const g2 = small.getContext('2d', { willReadFrequently: true });
  g2.imageSmoothingEnabled = true; g2.imageSmoothingQuality = 'high';
  g2.drawImage(big, 0, 0, MODEL_W, MODEL_H);
  bmp.close?.();
  return { previewCanvas: big, imageData: g2.getImageData(0, 0, MODEL_W, MODEL_H), origSize: [bmp.width, bmp.height] };
}

export function toTensorData(imageData) {
  const { data } = imageData, n = MODEL_W * MODEL_H, out = new Float32Array(3 * n);
  for (let p = 0; p < n; p++) for (let c = 0; c < 3; c++) out[c * n + p] = (data[p * 4 + c] / 255 - MEAN[c]) / STD[c];
  return out;
}
