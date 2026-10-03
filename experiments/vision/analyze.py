"""Turn the saved logits into the benchmark tables and plots (CSV in results/, PNG in results/plots/).

Inputs  : results/runs/{arch}_s{seed}.npz (+ results/runs/{arch}_s42/int8_logits.npz for the primary seed)
Policy  : temperature scaling fit on VAL only; thresholds fixed on clean VAL (see docs/EXPERIMENTS.md section 5).
"""
import glob, json, os, sys
import numpy as np, pandas as pd
from sklearn.metrics import f1_score, precision_recall_fscore_support, confusion_matrix
from scipy.optimize import minimize_scalar

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results")
LABELS = ["healthy", "miner", "rust", "phoma", "cercospora"]
PERTS = ["blur_mild", "blur_strong", "bright_dark", "bright_light", "contrast_low", "contrast_high",
         "jpeg_q12", "rotate15", "bg_clutter", "combined"]
MARGIN = 0.20


def softmax(z, T=1.0):
    z = z / T; z = z - z.max(1, keepdims=True); e = np.exp(z); return e / e.sum(1, keepdims=True)


def fit_T(logits, y):
    nll = lambda T: -np.log(softmax(logits, T)[np.arange(len(y)), y] + 1e-12).mean()
    return float(minimize_scalar(nll, bounds=(0.05, 10), method="bounded").x)


def ece(p, y, bins=15):
    conf, pred = p.max(1), p.argmax(1); acc = (pred == y).astype(float); e = 0.0
    for lo, hi in zip(np.linspace(0, 1, bins + 1)[:-1], np.linspace(0, 1, bins + 1)[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any(): e += m.mean() * abs(acc[m].mean() - conf[m].mean())
    return float(e)


def macro_f1(y, pred): return float(f1_score(y, pred, average="macro", labels=range(5), zero_division=0))


def margin_of(p): s = np.sort(p, 1); return s[:, -1] - s[:, -2]


def pick_thresholds(pv, yv):
    """tau_hi: smallest conf with accepted-accuracy >= 95% on VAL; tau_lo: >= 85% (fixed protocol)."""
    conf, pred = pv.max(1), pv.argmax(1); ok = pred == yv
    cands = np.unique(np.round(conf, 4)); res = {}
    for name, target in (("hi", 0.95), ("lo", 0.85)):
        best = None
        for t in np.sort(cands):
            m = conf >= t
            if m.sum() >= 5 and ok[m].mean() >= target: best = float(t); break
        res[name] = best
    reached = res["hi"] is not None
    if res["hi"] is None: res["hi"] = float(conf.max())
    if res["lo"] is None: res["lo"] = res["hi"]
    res["hi_reached_95"] = reached
    return res


def selective(p, y, tau, margin=0.0):
    conf, pred = p.max(1), p.argmax(1); acc = pred == y
    m = (conf >= tau) & (margin_of(p) >= margin)
    cov = float(m.mean()); sel = float(acc[m].mean()) if m.any() else float("nan")
    return cov, sel


def acc_at_coverage(p, y, coverage=0.8):
    conf, pred = p.max(1), p.argmax(1); order = np.argsort(-conf); k = max(1, int(round(coverage * len(y))))
    return float((pred[order[:k]] == y[order[:k]]).mean())


def bootstrap_ci(y, pred, n=1000, seed=0):
    rng = np.random.default_rng(seed); vals = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y)); vals.append(macro_f1(y[i], pred[i]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def analyse_run(npz, prefix=""):
    """Metrics for one set of logits. prefix '' = FP32 torch, 'int8_' = INT8 ORT (primary seed only)."""
    g = lambda k: npz[prefix + k]
    yv, yt = npz["val_y"], npz["test_y"]
    lv, lt = g("val_logits"), g("test_logits")
    T = fit_T(lv, yv)
    pv, pt = softmax(lv, T), softmax(lt, T)
    thr = pick_thresholds(pv, yv)
    pred = pt.argmax(1)
    out = {"T": T, "tau_hi": thr["hi"], "tau_lo": thr["lo"], "hi_reached_95": thr["hi_reached_95"],
           "acc": float((pred == yt).mean()), "macro_f1": macro_f1(yt, pred),
           "nll_raw": float(-np.log(softmax(lt)[np.arange(len(yt)), yt] + 1e-12).mean()),
           "nll_cal": float(-np.log(pt[np.arange(len(yt)), yt] + 1e-12).mean()),
           "ece_raw": ece(softmax(lt), yt), "ece_cal": ece(pt, yt),
           "mean_conf": float(pt.max(1).mean()), "mean_margin": float(margin_of(pt).mean()),
           "acc_at_80cov": acc_at_coverage(pt, yt, 0.8)}
    out["f1_ci_lo"], out["f1_ci_hi"] = bootstrap_ci(yt, pred)
    out["cov_hi"], out["sel_acc_hi"] = selective(pt, yt, thr["hi"], MARGIN)
    out["cov_lo"], out["sel_acc_lo"] = selective(pt, yt, thr["lo"])
    rob = {}
    for n in PERTS:
        k = f"pert_{n}"
        if prefix + k not in npz.files: continue
        pp = softmax(npz[prefix + k], T); pr = pp.argmax(1)
        c, s = selective(pp, yt, thr["hi"], MARGIN)
        rob[n] = {"acc": float((pr == yt).mean()), "macro_f1": macro_f1(yt, pr), "cov_hi": c, "sel_acc_hi": s}
    out["robust"] = rob
    mm = npz[prefix + "multi_logits"] if prefix + "multi_logits" in npz.files else None
    if mm is not None and len(mm):
        pm = softmax(mm, T); c, _ = selective(pm, np.zeros(len(pm), int), thr["hi"], MARGIN)
        out["multi_abstain_rate_hi"] = 1 - c
    out["_pt"], out["_pv"], out["_pred"], out["_T"] = pt, pv, pred, T
    return out


def main():
    os.makedirs(os.path.join(OUT, "plots"), exist_ok=True)
    summ = {(s["arch"], s["seed"]): s for s in json.load(open(os.path.join(OUT, "vision_runs_summary.json")))}
    rows, per_class, robust_rows, sel_rows = [], [], [], []
    store = {}
    for (arch, seed), s in sorted(summ.items()):
        npz = np.load(os.path.join(RUNS, f"{arch}_s{seed}.npz"), allow_pickle=True)
        variants = [("fp32", "", npz)]
        i8p = os.path.join(RUNS, f"{arch}_s{seed}", "int8_logits.npz")
        if os.path.exists(i8p):
            i8 = np.load(i8p, allow_pickle=True)
            class _N(dict):
                files = property(lambda self: list(self.keys()))
            nn = _N({"val_y": npz["val_y"], "test_y": npz["test_y"]})
            nn["int8_val_logits"] = i8["int8_val_logits"]; nn["int8_test_logits"] = i8["int8_test_logits"]
            nn["int8_multi_logits"] = i8["int8_multi_logits"]
            for n in PERTS: nn[f"int8_pert_{n}"] = i8[f"int8_pert_{n}"]
            variants.append(("int8", "int8_", nn))
        for tag, prefix, nz in variants:
            r = analyse_run(nz, prefix)
            store[(arch, seed, tag)] = r
            rows.append({"arch": arch, "seed": seed, "precision": tag, "params": s["params"],
                         "onnx_fp32_MB": round(s.get("onnx_fp32_bytes", 0) / 1e6, 2) or None,
                         "onnx_int8_MB": round(s.get("int8_bytes", 0) / 1e6, 2) or None,
                         **{k: v for k, v in r.items() if not k.startswith("_") and k != "robust"}})
            for n, v in r["robust"].items():
                robust_rows.append({"arch": arch, "seed": seed, "precision": tag, "perturbation": n, **v})
            # per-class
            pr, rc, f1, sup = precision_recall_fscore_support(nz["test_y"], r["_pred"], labels=range(5), zero_division=0)
            for c in range(5):
                per_class.append({"arch": arch, "seed": seed, "precision": tag, "class": LABELS[c],
                                  "precision_": pr[c], "recall": rc[c], "f1": f1[c], "support": int(sup[c])})
            # selective curve on clean test
            order = np.argsort(-r["_pt"].max(1)); ok = (r["_pred"] == nz["test_y"])[order]
            for k in range(5, len(ok) + 1, 5):
                sel_rows.append({"arch": arch, "seed": seed, "precision": tag, "coverage": k / len(ok), "selective_accuracy": float(ok[:k].mean())})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "model_benchmark.csv"), index=False)
    pd.DataFrame(per_class).to_csv(os.path.join(OUT, "per_class_metrics.csv"), index=False)
    pd.DataFrame(robust_rows).to_csv(os.path.join(OUT, "robustness_results.csv"), index=False)
    pd.DataFrame(sel_rows).to_csv(os.path.join(OUT, "selective_prediction.csv"), index=False)
    import pickle
    pickle.dump({k: {kk: vv for kk, vv in v.items()} for k, v in store.items()}, open(os.path.join(OUT, "_analysis_store.pkl"), "wb"))
    print(pd.DataFrame(rows)[["arch", "seed", "precision", "acc", "macro_f1", "ece_cal", "cov_hi", "sel_acc_hi", "acc_at_80cov"]].round(3).to_string())


if __name__ == "__main__":
    main()
