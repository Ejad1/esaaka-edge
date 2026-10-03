"""Prepare models + parity inputs for the browser benchmark.

- copies each primary-seed ONNX (FP32 and best INT8 variant) into models/
- writes 8 real test images as a Float32 tensor (PIL pipeline) + expected logits from onnxruntime (Python)
- copies the 8 prepared JPEGs so the browser can test its own canvas pre-processing
"""
import csv, json, os, shutil
import numpy as np
from PIL import Image
import onnxruntime as ort

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "..", "..", "results", "runs")
PREP = r"D:\Esaaka\hack_nation\data\prepared"
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32); STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
ARCHS = ["mobilenetv3_small_100", "mobilenetv3_large_100", "efficientnet_b0", "efficientnet_lite0"]


def tensor_of(img):
    a = np.asarray(img.convert("RGB").resize((448, 224), Image.BILINEAR), dtype=np.float32) / 255.0
    return ((a - MEAN) / STD).transpose(2, 0, 1)


def main():
    os.makedirs(os.path.join(HERE, "models"), exist_ok=True); os.makedirs(os.path.join(HERE, "data", "img"), exist_ok=True)
    rows = [r for r in csv.DictReader(open(os.path.join(PREP, "splits_seed42.csv"))) if r["split"] == "test"]
    pick, seen = [], {}
    for r in rows:
        if seen.get(r["label_name"], 0) < 2 and len(pick) < 8: pick.append(r); seen[r["label_name"]] = seen.get(r["label_name"], 0) + 1
    X = np.stack([tensor_of(Image.open(os.path.join(PREP, "images", r["id"] + ".jpg"))) for r in pick]).astype(np.float32)
    X.tofile(os.path.join(HERE, "data", "inputs.bin"))
    for r in pick: shutil.copy(os.path.join(PREP, "images", r["id"] + ".jpg"), os.path.join(HERE, "data", "img", r["id"] + ".jpg"))
    meta = {"shape": list(X.shape), "ids": [r["id"] for r in pick], "labels": [int(r["label"]) for r in pick], "models": {}}
    for arch in ARCHS:
        d = os.path.join(RUNS, f"{arch}_s42"); s = json.load(open(os.path.join(d, "summary.json")))
        files = {"fp32": os.path.join(d, "model_fp32.onnx"), "int8": os.path.join(d, f"model_int8_{s['int8_variant']}.onnx")}
        for prec, src in files.items():
            dst = os.path.join(HERE, "models", f"{arch}_{prec}.onnx"); shutil.copy(src, dst)
            sess = ort.InferenceSession(dst, providers=["CPUExecutionProvider"])
            logits = np.stack([sess.run(None, {"input": x[None]})[0][0] for x in X])
            meta["models"][f"{arch}_{prec}"] = {"bytes": os.path.getsize(dst), "expected_logits": logits.tolist()}
            print(arch, prec, round(os.path.getsize(dst) / 1e6, 2), "MB")
    json.dump(meta, open(os.path.join(HERE, "data", "meta.json"), "w"))


if __name__ == "__main__":
    main()
