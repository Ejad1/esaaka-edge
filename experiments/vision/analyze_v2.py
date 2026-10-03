"""Field-adapted v2 (BRACOL + Uganda + RoCoLe, 6 classes): per-source evaluation on HELD-OUT GROUPS.

Temperature and thresholds are fixed on validation (all sources pooled), never on test.
IMPORTANT: Uganda and RoCoLe test images come from the same datasets/farms as the training images (separated by
perceptual-hash group / plant), so these numbers are OPTIMISTIC and are NOT independent field validation.
"""
import json, os, sys
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, f1_score
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import softmax, fit_T, pick_thresholds, ece

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
R = os.path.join(ROOT, "results")
ARCHS = sys.argv[1:] or ["mobilenetv3_large_100", "mobilenetv3_small_100"]
NAMES = ["healthy", "miner", "rust", "phoma", "cercospora", "other"]
PERTS = ["blur_mild", "blur_strong", "bright_dark", "bright_light", "contrast_low", "contrast_high", "jpeg_q12", "rotate15", "bg_clutter", "combined"]
MARGIN = 0.20
rows = []
for a in ARCHS:
    z = np.load(os.path.join(R, "runs", f"{a}_s42_rob_v2.npz"), allow_pickle=True)
    yv, yt, sv, st = z["val_y"], z["test_y"], z["val_src"], z["test_src"]
    T = fit_T(z["val_logits"], yv); pv, pt = softmax(z["val_logits"], T), softmax(z["test_logits"], T)
    thr = pick_thresholds(pv, yv)
    pred = pt.argmax(1); conf = pt.max(1); s = np.sort(pt, 1); marg = s[:, -1] - s[:, -2]
    other = pred == 5
    high = (conf >= thr["hi"]) & (marg >= MARGIN) & ~other
    print(f"\n== {a}: T={T:.3f} tau_hi={thr['hi']:.3f} (95% reached: {thr['hi_reached_95']}) tau_lo={thr['lo']:.3f} | val ECE {ece(pv, yv):.3f}")
    for src in ("bracol", "uganda", "rocole"):
        m = st == src; y, p, h, o = yt[m], pred[m], high[m], other[m]
        r = {"arch": a, "source": src, "n_test": int(m.sum()), "accuracy_6class": float((p == y).mean()), "high_rate": float(h.mean()),
             "conf_wrong_rate": float((h & (p != y)).mean()), "answered_accuracy": float((p[h] == y[h]).mean()) if h.any() else np.nan,
             "predicted_other_rate": float(o.mean())}
        lab = [c for c in range(6) if (y == c).any()]
        r["macro_f1"] = float(f1_score(y, p, labels=lab, average="macro", zero_division=0))
        for c in range(6):
            if (y == c).any(): r[f"recall_{NAMES[c]}"] = float((p[y == c] == c).mean())
        if src == "rocole":
            sub = np.isin(y, [0, 2]); r["auroc_rust_vs_healthy"] = float(roc_auc_score(y[sub] == 2, (pt[m][sub, 2] - pt[m][sub, 0])))
            mite = y == 5; r["mite_confident_disease_rate"] = float((h & mite & (p != 5)).sum() / max(1, mite.sum())); r["mite_no_diagnosis_rate"] = float((~h)[mite].mean()) if mite.any() else np.nan
        rows.append(r)
    # synthetic robustness on the BRACOL test subset (clean vs perturbed), same 10 fixed perturbations
    idx = z["pert_idx"]; yb = yt[idx]; keep = yb != 5
    f = lambda lg: f1_score(yb[keep], softmax(lg, T).argmax(1)[keep], labels=[0, 1, 2, 3, 4], average="macro", zero_division=0)
    clean = f(z["test_logits"][idx]); pf = {n: f(z[f"pert_{n}"]) for n in PERTS}
    print(f"BRACOL test macro-F1 clean {clean:.3f} | mean over 10 perturbations {np.mean(list(pf.values())):.3f} | combined {pf['combined']:.3f} | bg_clutter {pf['bg_clutter']:.3f}")
    rows.append({"arch": a, "source": "bracol_synthetic", "macro_f1": clean, "perturbed_mean_macro_f1": float(np.mean(list(pf.values()))), "T": T, "tau_hi": thr["hi"], "tau_lo": thr["lo"], "hi_reached_95": thr["hi_reached_95"]})
D = pd.DataFrame(rows); D.round(4).to_csv(os.path.join(R, "field_v2_results.csv"), index=False)
# benchmark-style file for pwa/scripts/export_config.py (T and thresholds fixed on pooled v2 validation)
bm = []
for a in ARCHS:
    g = D[(D.arch == a) & (D.source == "bracol_synthetic")].iloc[0]; b = D[(D.arch == a) & (D.source == "bracol")].iloc[0]
    bm.append({"arch": a, "seed": 42, "precision": "fp32", "T": g["T"], "tau_hi": g["tau_hi"], "tau_lo": g["tau_lo"], "acc": b["accuracy_6class"], "macro_f1": b["macro_f1"]})
pd.DataFrame(bm).to_csv(os.path.join(R, "model_benchmark_v2.csv"), index=False)
pd.set_option("display.width", 240); pd.set_option("display.max_columns", 30)
print(D[D.source != "bracol_synthetic"].drop(columns=["T", "tau_hi", "tau_lo", "hi_reached_95", "perturbed_mean_macro_f1"], errors="ignore").round(3).to_string(index=False))
