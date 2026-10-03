"""Validation-perturbed logits for the Phase 1 (clean-trained) FP32 ONNX models, seed 42.
Needed to compare recipes on VALIDATION data (Phase 2 runs produce theirs on Modal)."""
import os, sys, csv
import numpy as np, onnxruntime as ort
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "experiments", "robustness"))
import perturb
PREP = os.path.join("D:" + os.sep, "Esaaka", "hack_nation", "data", "prepared")
MEAN = np.array([0.485, 0.456, 0.406], np.float32); STD = np.array([0.229, 0.224, 0.225], np.float32)
ARCHS = ["mobilenetv3_small_100", "mobilenetv3_large_100", "efficientnet_b0", "efficientnet_lite0"]
ids = [r["id"] for r in csv.DictReader(open(os.path.join(PREP, "splits_seed42.csv"))) if r["split"] == "val"]
def tens(img): a = np.asarray(img.convert("RGB").resize((448, 224), Image.BILINEAR), np.float32) / 255.0; return ((a - MEAN) / STD).transpose(2, 0, 1)[None]
imgs = {i: Image.open(os.path.join(PREP, "images", i + ".jpg")).convert("RGB") for i in ids}
for arch in ARCHS:
    so = ort.SessionOptions(); so.intra_op_num_threads = 3
    s = ort.InferenceSession(os.path.join(ROOT, "results", "runs", f"{arch}_s42", "model_fp32.onnx"), so, providers=["CPUExecutionProvider"])
    out = {"val_ids": np.array(ids)}
    for name in perturb.NAMES + perturb.EXTRA_NAMES:
        out[f"valpert_{name}"] = np.stack([s.run(None, {"input": tens(perturb.apply(name, imgs[i], i))})[0][0] for i in ids])
    np.savez_compressed(os.path.join(ROOT, "results", "runs", f"{arch}_s42_valpert_phase1.npz"), **out); print(arch, "done", flush=True)
