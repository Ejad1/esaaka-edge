"""EXTERNAL evaluation on field datasets never used for training or threshold selection.

    python eval_external.py [suffix]      # suffix: _s42 (Phase 1, default) or _s42_rob (Phase 2)

Datasets : Uganda (Mendeley k36wnd6knb, CC BY 4.0, farm photos, 256x256, AUGMENTED copies present)
           RoCoLe (Mendeley c5yvn32dzg, CC BY 4.0, Robusta, smartphone field photos)
Protocol : image -> pad (default) or stretch to 2:1 -> 448x224 -> ImageNet normalisation (same as training eval)
           temperature T and thresholds tau_hi/tau_lo are the ones fixed on clean BRACOL validation. Nothing is tuned here.
"""
import csv, json, os, random, sys, collections
import numpy as np, pandas as pd
import onnxruntime as ort
from PIL import Image, ImageOps
from sklearn.metrics import roc_auc_score

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
RUNS, RES = os.path.join(ROOT, "results", "runs"), os.path.join(ROOT, "results")
EXT = r"D:\Esaaka\hack_nation\data\external"
ARCHS = ["mobilenetv3_small_100", "mobilenetv3_large_100", "efficientnet_b0", "efficientnet_lite0"]
LAB = ["healthy", "miner", "rust", "phoma", "cercospora"]
MEAN = np.array([0.485, 0.456, 0.406], np.float32); STD = np.array([0.229, 0.224, 0.225], np.float32)
MARGIN = 0.20
suffix = sys.argv[1] if len(sys.argv) > 1 else "_s42"
if os.environ.get("ONLY_ARCH"): ARCHS = [a for a in ARCHS if a == os.environ["ONLY_ARCH"]]
CAP_PER_CLASS = 600


def to_tensor(img, mode):
    img = img.convert("RGB")
    if mode == "pad":
        edge = np.concatenate([np.asarray(img)[0], np.asarray(img)[-1], np.asarray(img)[:, 0], np.asarray(img)[:, -1]])
        img = ImageOps.pad(img, (512, 256), color=tuple(int(v) for v in np.median(edge, axis=0)))
    else:
        img = img.resize((512, 256), Image.LANCZOS)
    a = np.asarray(img.resize((448, 224), Image.BILINEAR), np.float32) / 255.0
    return ((a - MEAN) / STD).transpose(2, 0, 1)[None]


def softmax(z, T): z = z / T; z = z - z.max(1, keepdims=True); e = np.exp(z); return e / e.sum(1, keepdims=True)


def dihedral_hash(path):
    """Canonical perceptual hash invariant to flips/rotations (to estimate unique originals among augmented copies)."""
    g = np.asarray(Image.open(path).convert("L").resize((9, 9), Image.LANCZOS), np.float32)
    best = None
    for k in range(4):
        for f in (False, True):
            x = np.rot90(g, k); x = np.fliplr(x) if f else x
            h = (x[:, 1:] > x[:, :-1]).tobytes()
            best = h if best is None or h < best else best
    return best


def load_models():
    bm = pd.read_csv(os.path.join(RES, "model_benchmark.csv" if suffix == "_s42" else "model_benchmark_rob.csv"))
    out = {}
    for a in ARCHS:
        row = bm[(bm.arch == a) & (bm.seed == 42) & (bm.precision == "fp32")]
        if row.empty: continue
        row = row.iloc[0]
        so = ort.SessionOptions(); so.intra_op_num_threads = 6
        out[a] = {"sess": ort.InferenceSession(os.path.join(RUNS, f"{a}{suffix}", "model_fp32.onnx"), so, providers=["CPUExecutionProvider"]),
                  "T": float(row["T"]), "hi": float(row["tau_hi"]), "lo": float(row["tau_lo"])}
    return out


def readable(items):
    """Drop files that cannot be fully decoded (truncated/empty at source). Same filter for every model."""
    ok, dropped = [], 0
    for p, c in items:
        try:
            Image.open(p).convert("RGB").load(); ok.append((p, c))
        except Exception:
            dropped += 1
    print(f"  readable: kept {len(ok)}, dropped {dropped} unreadable/truncated files", flush=True)
    return ok


def run(items, models, mode):
    """items: list of (path, true_label_name). Returns dict arch -> logits [N,5]."""
    logits = {a: [] for a in models}
    for k, (p, _) in enumerate(items):
        x = to_tensor(Image.open(p), mode)
        for a, m in models.items(): logits[a].append(m["sess"].run(None, {"input": x})[0][0])
        if k % 200 == 0: print(f"  {mode}: {k}/{len(items)}", flush=True)
    return {a: np.stack(v) for a, v in logits.items()}


def tiers(p, m):
    conf, marg = p.max(1), np.sort(p, 1)[:, -1] - np.sort(p, 1)[:, -2]
    high = (conf >= m["hi"]) & (marg >= MARGIN); medium = (conf >= m["lo"]) & ~high
    return high, medium


def main():
    models = load_models()
    rng = random.Random(0)
    # ---- Uganda
    ug = []
    for c in ("healthy", "rust", "phoma"):
        d = os.path.join(EXT, "uganda", c); fs = [f for f in sorted(os.listdir(d)) if os.path.getsize(os.path.join(d, f)) > 0]
        rng.shuffle(fs); ug += [(os.path.join(d, f), c) for f in fs[:CAP_PER_CLASS]]
    ug = readable(ug)
    hashes = collections.Counter(dihedral_hash(p) for p, _ in ug)
    uniq = len(hashes)
    # ---- RoCoLe
    ro = [(os.path.join(EXT, "rocole", "images", r["file"]), r["label"]) for r in csv.DictReader(open(os.path.join(EXT, "rocole", "sample.csv")))
          if os.path.exists(os.path.join(EXT, "rocole", "images", r["file"]))]
    ro = readable(ro)
    rows, detail = [], {}
    for mode in ("pad", "stretch"):
        ug_log = run(ug, models, mode); ro_log = run(ro, models, mode)
        for a, m in models.items():
            # Uganda: 3 true classes {healthy=0, rust=2, phoma=3}
            y = np.array([{"healthy": 0, "rust": 2, "phoma": 3}[c] for _, c in ug]); p = softmax(ug_log[a], m["T"]); pred = p.argmax(1)
            high, med = tiers(p, m)
            from sklearn.metrics import f1_score
            f1 = f1_score(y, pred, labels=[0, 2, 3], average="macro", zero_division=0)
            rec = {c: float((pred[y == v] == v).mean()) for c, v in (("healthy", 0), ("rust", 2), ("phoma", 3))}
            rows.append({"dataset": "uganda", "mode": mode, "arch": a, "n": len(y), "approx_unique_originals": uniq,
                         "accuracy": float((pred == y).mean()), "macro_f1_3class": float(f1), **{f"recall_{k}": v for k, v in rec.items()},
                         "coverage_high": float(high.mean()), "sel_acc_high": float((pred[high] == y[high]).mean()) if high.any() else np.nan,
                         "abstain_rate": float((~high & ~med).mean())})
            detail[f"uganda_{mode}_{a}"] = {"confusion_true_by_pred": [[int(((y == t) & (pred == q)).sum()) for q in range(5)] for t in (0, 2, 3)]}
            # RoCoLe
            lab = np.array([c for _, c in ro]); p = softmax(ro_log[a], m["T"]); pred = p.argmax(1); high, med = tiers(p, m)
            isr = np.array([c.startswith("rust") for c in lab]); ish = lab == "healthy"; ism = lab == "red_spider_mite"
            sub = isr | ish
            auroc = float(roc_auc_score(isr[sub], p[sub, 2] - p[sub, 0]))
            rows.append({"dataset": "rocole", "mode": mode, "arch": a, "n": len(lab),
                         "recall_healthy": float((pred[ish] == 0).mean()), "recall_rust": float((pred[isr] == 2).mean()),
                         "recall_rust_level1": float((pred[lab == "rust_level_1"] == 2).mean()),
                         "recall_rust_level2plus": float((pred[np.isin(lab, ["rust_level_2", "rust_level_3", "rust_level_4"])] == 2).mean()),
                         "auroc_rust_vs_healthy": auroc,
                         "mite_high_conf_disease_rate": float((high & ism & (pred != 0)).sum() / ism.sum()),
                         "mite_abstain_rate": float((~high & ~med)[ism].sum() / ism.sum()),
                         "coverage_high": float(high.mean()), "abstain_rate": float((~high & ~med).mean()),
                         "high_conf_wrong_rate_rust_healthy": float((high[sub] & (np.where(isr[sub], 2, 0) != pred[sub])).sum() / sub.sum())})
            detail[f"rocole_{mode}_{a}"] = {"mite_pred_counts": {LAB[k]: int((pred[ism] == k).sum()) for k in range(5)},
                                            "healthy_pred_counts": {LAB[k]: int((pred[ish] == k).sum()) for k in range(5)},
                                            "rust_pred_counts": {LAB[k]: int((pred[isr] == k).sum()) for k in range(5)}}
    df = pd.DataFrame(rows); out = os.path.join(RES, f"external_eval{'' if suffix == '_s42' else '_rob'}.csv")
    df.to_csv(out, index=False); json.dump(detail, open(out.replace(".csv", "_detail.json"), "w"), indent=2)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(df[df["dataset"] == "uganda"].round(3).to_string(index=False)); print(df[df["dataset"] == "rocole"].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
