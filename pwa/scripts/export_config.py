"""Assemble the shipped model + config from the experiment outputs (single source of truth).

    python export_config.py <arch> [--runs-suffix _s42] [--guard ../results/guard_bounds.json]
"""
import argparse, hashlib, json, os, shutil
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "..", "results")
PUB = os.path.join(HERE, "..", "public", "models")
NAMES = {"mobilenetv3_small_100": "MobileNetV3-Small", "mobilenetv3_large_100": "MobileNetV3-Large",
         "efficientnet_b0": "EfficientNet-B0", "efficientnet_lite0": "EfficientNet-Lite0"}

ap = argparse.ArgumentParser(); ap.add_argument("arch"); ap.add_argument("--runs-suffix", default="_s42")
ap.add_argument("--bench", default="model_benchmark.csv"); ap.add_argument("--guard", default=None); ap.add_argument("--six", action="store_true")
a = ap.parse_args()

bm = pd.read_csv(os.path.join(RES, a.bench))
row = bm[(bm.arch == a.arch) & (bm.seed == 42) & (bm.precision == "fp32")].iloc[0]
src = os.path.join(RES, "runs", f"{a.arch}{a.runs_suffix}", "model_fp32.onnx")
os.makedirs(PUB, exist_ok=True); dst = os.path.join(PUB, "model.onnx"); shutil.copy(src, dst)
sha = hashlib.sha256(open(dst, "rb").read()).hexdigest()
guard = json.load(open(a.guard)) if a.guard else None
cfg = {
    "display_name": NAMES[a.arch], "arch": a.arch, "model_file": "model.onnx", "model_mb": round(os.path.getsize(dst) / 1e6, 1),
    "model_sha256": sha, "model_version": f"{a.arch}{a.runs_suffix}",
    "labels": ["healthy", "miner", "rust", "phoma", "cercospora"] + (["other"] if a.six else []),
    "input": {"width": 448, "height": 224, "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
    "temperature": float(row["T"]),
    "thresholds": {"high": float(row["tau_hi"]), "medium": float(row["tau_lo"]), "margin": 0.20,
                   "note": "fixed on clean BRACOL validation only (docs/EXPERIMENTS.md section 5); never tuned on test or field data"},
    "guard": guard,
    "provenance": {"train_data": "BRACOL leaf images (CC BY 4.0), recovered subset, Brazil, plain background",
                   "test_clean": {"accuracy": float(row["acc"]), "macro_f1": float(row["macro_f1"])}},
}
json.dump(cfg, open(os.path.join(PUB, "model_config.json"), "w"), indent=1)
print(json.dumps({k: cfg[k] for k in ("display_name", "model_mb", "temperature", "thresholds", "model_version")}, indent=1))
