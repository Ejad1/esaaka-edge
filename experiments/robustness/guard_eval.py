"""Learn the input-quality gate bounds on CLEAN VALIDATION rows only, then evaluate the gate and the whole system
(gate AND confidence tier) on perturbed test images and on external field photos.

Rule (declared before looking at any perturbed/external result):
  * one- or two-sided bounds per metric at quantile q / 1-q of the clean validation rows, starting q = 0.5%,
    reduced (bounds widened) until >= 95% of clean validation images pass;
  * floors so the gate is not hypersensitive: dark-fraction upper bound >= 0.01, bright-fraction upper bound >= 0.02.
Primary safety metric: "confident-wrong rate" = share of ALL images for which the system shows a HIGH-tier answer that is wrong
(or any HIGH disease answer on an out-of-scope image). Lower is better.
"""
import json, os, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
RES = os.path.join(ROOT, "results")
rows = json.load(open(os.path.join(RES, "system_eval_rows.json")))
py = json.load(open(os.path.join(RES, "_py_test_top1.json")))
df = pd.DataFrame([r for r in rows if "error" not in r])
M = pd.DataFrame(list(df.metrics)); df = pd.concat([df.drop(columns=["metrics"]), M], axis=1)
print("rows", len(df), "| errors dropped", len(rows) - len(df))

SIDES = {"sharp": "lo", "mean": "both", "contrast": "lo", "dark": "hi", "bright": "hi", "border": "hi", "leaf": "both"}
FLOORS = {"dark": 0.01, "bright": 0.02}
val = df[df.set == "val_clean"]


def make_bounds(q):
    b = {}
    for k, side in SIDES.items():
        lo = float(val[k].quantile(q)) if side in ("lo", "both") else None
        hi = float(val[k].quantile(1 - q)) if side in ("hi", "both") else None
        if hi is not None and k in FLOORS: hi = max(hi, FLOORS[k])
        b[k] = [lo, hi]
    return b


def reasons(row, b):
    r = []
    chk = lambda k: (-1 if b[k][0] is not None and row[k] < b[k][0] else (1 if b[k][1] is not None and row[k] > b[k][1] else 0))
    if chk("sharp") < 0: r.append("blur")
    if chk("mean") < 0 or chk("dark") > 0: r.append("too_dark")
    if chk("mean") > 0 or chk("bright") > 0: r.append("too_bright")
    if chk("contrast") < 0: r.append("low_contrast")
    if chk("border") > 0: r.append("busy_background")
    if chk("leaf") < 0: r.append("no_leaf")
    if chk("leaf") > 0: r.append("background_too_colourful")
    return r


q = 0.005
while True:
    bounds = make_bounds(q); val_pass = np.mean([not reasons(r, bounds) for _, r in val.iterrows()])
    if val_pass >= 0.95 or q < 1e-4: break
    q /= 1.5
print(f"bounds at q={q:.4f}: clean-validation pass rate {val_pass:.3f}")
json.dump({"bounds": bounds, "learned_on": "clean BRACOL validation (seed 42)", "quantile": q, "val_pass_rate": float(val_pass),
           "note": "Scale-dependent: tuned on BRACOL captures; recalibrate with field photos before real deployment."},
          open(os.path.join(RES, "guard_bounds.json"), "w"), indent=1)

df["gate_fail"] = [bool(reasons(r, bounds)) for _, r in df.iterrows()]
df["reason"] = [",".join(reasons(r, bounds)) for _, r in df.iterrows()]

CLS = {"healthy": 0, "rust": 2, "phoma": 3}
def truth(r):
    s, i = r["set"], r["id"]
    if s.startswith("test_"): return py[str(i)]["y"] if str(i) in py else None
    if s.startswith("uganda_"): return CLS[s.split("_", 1)[1]]
    if s.startswith("rocole_"):
        lab = s.split("_", 1)[1]; return 0 if lab == "healthy" else (-1 if lab == "red_spider_mite" else 2)
    return None
df["y"] = [truth(r) for _, r in df.iterrows()]      # -1 = out-of-scope disease (no correct class exists)

lab = df[df.y.notna()].copy()
lab["high"] = lab.tier == "high"
lab["correct"] = (lab.top1 == lab.y) & (lab.y >= 0)
lab["model_conf_wrong"] = lab.high & ~lab.correct
lab["sys_answer"] = lab.high & ~lab.gate_fail
lab["sys_conf_wrong"] = lab.sys_answer & ~lab.correct
rows_out = []
for s, g in lab.groupby("set"):
    ans = g[g.high]; sans = g[g.sys_answer]
    rows_out.append({"set": s, "n": len(g), "gate_reject_rate": g.gate_fail.mean(),
                     "model_high_rate": g.high.mean(), "model_conf_wrong_rate": g.model_conf_wrong.mean(),
                     "model_high_accuracy": ans.correct.mean() if len(ans) else np.nan,
                     "system_answer_rate": g.sys_answer.mean(), "system_conf_wrong_rate": g.sys_conf_wrong.mean(),
                     "system_answer_accuracy": sans.correct.mean() if len(sans) else np.nan})
other = df[df.y.isna()]
for s, g in other.groupby("set"):
    rows_out.append({"set": s, "n": len(g), "gate_reject_rate": g.gate_fail.mean(), "model_high_rate": (g.tier == "high").mean(),
                     "system_answer_rate": ((g.tier == "high") & ~g.gate_fail).mean()})
R = pd.DataFrame(rows_out).set_index("set"); R.round(4).to_csv(os.path.join(RES, "guard_results.csv"))
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 20)
print(R.round(3).to_string())

fixed = [f"test_{n}" for n in ["blur_mild", "blur_strong", "bright_dark", "bright_light", "contrast_low", "contrast_high", "jpeg_q12", "rotate15", "bg_clutter", "combined"]]
summ = {"perturbed_test_mean": {k: float(R.loc[fixed, k].mean()) for k in ("gate_reject_rate", "model_conf_wrong_rate", "system_conf_wrong_rate", "system_answer_rate")}}
ext = [s for s in R.index if s.startswith(("uganda_", "rocole_"))]
summ["external_pooled"] = {"n": int(R.loc[ext, "n"].sum()),
    "gate_reject_rate": float((R.loc[ext, "gate_reject_rate"] * R.loc[ext, "n"]).sum() / R.loc[ext, "n"].sum()),
    "model_conf_wrong_rate": float((R.loc[ext, "model_conf_wrong_rate"] * R.loc[ext, "n"]).sum() / R.loc[ext, "n"].sum()),
    "system_conf_wrong_rate": float((R.loc[ext, "system_conf_wrong_rate"] * R.loc[ext, "n"]).sum() / R.loc[ext, "n"].sum())}
summ["clean_test"] = {k: float(R.loc["test_clean", k]) for k in ("gate_reject_rate", "model_high_accuracy", "system_answer_rate", "system_answer_accuracy", "model_conf_wrong_rate", "system_conf_wrong_rate")}
json.dump(summ, open(os.path.join(RES, "guard_summary.json"), "w"), indent=1); print(json.dumps(summ, indent=1))
reasons_ext = df[df.set.str.startswith(("uganda_", "rocole_")) & df.gate_fail].reason.str.split(",").explode().value_counts().head(6)
print("most common rejection reasons on external field photos:\n", reasons_ext.to_string())

# plot: confident-wrong rate, model-only vs system, per condition
sets = ["test_clean"] + fixed + ["uganda_healthy", "uganda_rust", "uganda_phoma", "rocole_healthy", "rocole_rust_level_1", "rocole_red_spider_mite"]
sets = [s for s in sets if s in R.index]
fig, ax = plt.subplots(figsize=(11, 4.2)); x = np.arange(len(sets)); w = 0.4
ax.bar(x - w / 2, 100 * R.loc[sets, "model_conf_wrong_rate"], w, color="#b5651d", label="model only (confidence tier HIGH)")
ax.bar(x + w / 2, 100 * R.loc[sets, "system_conf_wrong_rate"], w, color="#1b6e3f", label="system = quality gate + confidence tier")
ax.set_xticks(x); ax.set_xticklabels([s.replace("test_", "").replace("rocole_", "RoCoLe:\n").replace("uganda_", "Uganda:\n") for s in sets], rotation=40, ha="right", fontsize=8)
ax.set(ylabel="Confident-wrong answers (% of all images)", title="Does the quality gate reduce confidently wrong answers? (SYNTHETIC perturbations and external field photos)")
ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False, fontsize=8); fig.tight_layout()
os.makedirs(os.path.join(RES, "plots"), exist_ok=True); fig.savefig(os.path.join(RES, "plots", "gate_confident_wrong.png"), dpi=170)
