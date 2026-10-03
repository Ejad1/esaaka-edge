"""System-level evaluation of the SHIPPED model (MobileNetV3-Large, robust training, seed 42).

The gate decision depends only on image metrics, which were measured once in the real browser runtime
(results/system_eval_rows.json) and do not depend on the model. We combine them with the final model's logits
(clean + fixed perturbations on the held-out test split) and its calibration/thresholds fixed on clean validation.
External field photos are all rejected by the gate (model-independent), see guard_eval.py.
"""
import json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vision"))
from analyze import softmax, macro_f1

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
R = os.path.join(ROOT, "results")
cfg = json.load(open(os.path.join(ROOT, "pwa", "public", "models", "model_config.json")))
bounds = json.load(open(os.path.join(R, "guard_bounds.json")))["bounds"]
T, th = cfg["temperature"], cfg["thresholds"]
rows = json.load(open(os.path.join(R, "system_eval_rows.json")))
M = {(r["set"], str(r["id"])): r["metrics"] for r in rows if "error" not in r}
npz = np.load(os.path.join(R, "runs", "mobilenetv3_large_100_s42_rob.npz"), allow_pickle=True)
ids, y = [str(i) for i in npz["test_ids"]], npz["test_y"]


def gate_fail(m):
    chk = lambda k: (-1 if bounds[k][0] is not None and m[k] < bounds[k][0] else (1 if bounds[k][1] is not None and m[k] > bounds[k][1] else 0))
    return chk("sharp") < 0 or chk("mean") != 0 or chk("dark") > 0 or chk("bright") > 0 or chk("contrast") < 0 or chk("border") > 0 or chk("leaf") != 0


names = ["clean", "blur_mild", "blur_strong", "bright_dark", "bright_light", "contrast_low", "contrast_high", "jpeg_q12", "rotate15", "bg_clutter", "combined", "bg_uniform"]
out = []
for n in names:
    lg = npz["test_logits"] if n == "clean" else npz[f"pert_{n}"]
    p = softmax(lg, T); conf = p.max(1); s = np.sort(p, 1); marg = s[:, -1] - s[:, -2]; pred = p.argmax(1)
    high = (conf >= th["high"]) & (marg >= th["margin"])
    gf = np.array([gate_fail(M[(f"test_{n}", i)]) for i in ids]); ok = pred == y
    sysans = high & ~gf
    out.append({"condition": n, "macro_f1_all": macro_f1(y, pred), "model_high_rate": high.mean(), "model_conf_wrong": (high & ~ok).mean(),
                "gate_reject": gf.mean(), "system_answer_rate": sysans.mean(), "system_conf_wrong": (sysans & ~ok).mean(),
                "system_answer_accuracy": ok[sysans].mean() if sysans.any() else np.nan})
D = pd.DataFrame(out).set_index("condition"); D.round(4).to_csv(os.path.join(R, "system_eval_final.csv"))
pd.set_option("display.width", 200); print(D.round(3).to_string())
fixed = [n for n in names if n not in ("clean", "bg_uniform")]
print("\nmean over the 10 fixed perturbations: model-only confident-wrong %.3f -> system %.3f | gate rejects %.2f | system answers %.2f" % (
    D.loc[fixed, "model_conf_wrong"].mean(), D.loc[fixed, "system_conf_wrong"].mean(), D.loc[fixed, "gate_reject"].mean(), D.loc[fixed, "system_answer_rate"].mean()))
