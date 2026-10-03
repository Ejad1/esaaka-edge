"""Re-learn the quality-gate bounds for the field-adapted model, on the pooled v2 VALIDATION set only.
Same rule as guard_eval.py (quantile q=0.5%, widened until >= 95% of validation images pass; floors on dark/bright fractions).
CORRECTION (made after a first run showed a 41% pass rate): ALL bounds and the 95% pass-rate target use only the
phone-resolution validation sources (BRACOL, RoCoLe). Uganda images are 256 px by construction (upscaled => low Laplacian
variance, not defocus), so they are reported separately and do not set the bounds. The first version let Uganda drive the
widening loop, which was a flaw in the rule, not a result.
"""
import json, os
import numpy as np, pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
R = os.path.join(ROOT, "results")
rows = [r for r in json.load(open(os.path.join(R, "gate_v2_rows.json"))) if "error" not in r]
df = pd.concat([pd.DataFrame(rows).drop(columns=["metrics"]), pd.DataFrame([r["metrics"] for r in rows])], axis=1)
val, test = df[df.split == "val"], df[df.split == "test"]
SIDES = {"sharp": "lo", "mean": "both", "contrast": "lo", "dark": "hi", "bright": "hi", "border": "hi", "leaf": "both"}
FLOORS = {"dark": 0.01, "bright": 0.02}


def bounds_at(q):
    b = {}
    for k, side in SIDES.items():
        ref = val[val.src.isin(["bracol", "rocole"])]
        lo = float(ref[k].quantile(q)) if side in ("lo", "both") else None
        hi = float(ref[k].quantile(1 - q)) if side in ("hi", "both") else None
        if hi is not None and k in FLOORS: hi = max(hi, FLOORS[k])
        b[k] = [lo, hi]
    return b


def fails(row, b):
    for k in SIDES:
        lo, hi = b[k]
        if lo is not None and row[k] < lo: return True
        if hi is not None and row[k] > hi: return True
    return False


q = 0.005
while True:
    b = bounds_at(q); vp = np.mean([not fails(r, b) for _, r in val[val.src.isin(["bracol", "rocole"])].iterrows()])
    if vp >= 0.95 or q < 1e-4: break
    q /= 1.5
json.dump({"bounds": b, "learned_on": "v2 validation, phone-resolution sources only (BRACOL + RoCoLe)", "quantile": q, "val_pass_rate": float(vp),
           "note": "Scale-dependent; recalibrate with photos from the target phones before real deployment."}, open(os.path.join(R, "guard_bounds_v2.json"), "w"), indent=1)
print(f"q={q:.4f}  pooled-validation pass rate {vp:.3f}")
print({k: [None if v is None else round(v, 3) for v in x] for k, x in b.items()})
test = test.assign(fail=[fails(r, b) for _, r in test.iterrows()])
print("\nGate rejection on held-out TEST, by source:"); print(test.groupby("src").fail.mean().round(3).to_string())
print("by source and class label (0 healthy,2 rust,3 phoma,5 other):"); print(test.groupby(["src", "label"]).fail.mean().round(3).to_string())
