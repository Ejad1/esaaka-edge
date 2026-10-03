"""Phase 2 (post-hoc): robust-augmentation recipe vs clean recipe. Applies the criterion frozen in docs/EXPERIMENTS.md."""
import json, os, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import analyse_run, softmax, macro_f1, PERTS

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
R = os.path.join(ROOT, "results"); RUNS = os.path.join(R, "runs"); PL = os.path.join(R, "plots")
ARCHS = ["mobilenetv3_small_100", "mobilenetv3_large_100", "efficientnet_b0", "efficientnet_lite0"]
SHORT = {"mobilenetv3_small_100": "MobileNetV3-S", "mobilenetv3_large_100": "MobileNetV3-L", "efficientnet_b0": "EfficientNet-B0", "efficientnet_lite0": "EfficientNet-Lite0"}
W = dict(f1=0.30, sel=0.20, rob=0.15, size=0.15, lat=0.20)
EXTRA = "bg_uniform"

summ = {(s["arch"], s["seed"]): s for s in json.load(open(os.path.join(R, "vision_runs_summary_rob.json")))}
rows, rob_rows = [], []
for a in ARCHS:
    for seed in (42, 1, 2):
        for phase, suffix in ((1, ""), (2, "_rob")):
            npz = np.load(os.path.join(RUNS, f"{a}_s{seed}{suffix}.npz"), allow_pickle=True)
            r = analyse_run(npz); yt = npz["test_y"]
            bu = macro_f1(yt, npz[f"pert_{EXTRA}"].argmax(1)) if f"pert_{EXTRA}" in npz.files else np.nan
            cw = [v["cov_hi"] * (1 - v["sel_acc_hi"]) for v in r["robust"].values() if not np.isnan(v["sel_acc_hi"])]
            rows.append({"phase": phase, "arch": a, "seed": seed, "precision": "fp32", "T": r["T"], "tau_hi": r["tau_hi"], "tau_lo": r["tau_lo"],
                         "acc": r["acc"], "macro_f1": r["macro_f1"], "ece_cal": r["ece_cal"], "acc_at_80cov": r["acc_at_80cov"],
                         "cov_hi": r["cov_hi"], "sel_acc_hi": r["sel_acc_hi"],
                         "robust_macro_f1": np.mean([v["macro_f1"] for v in r["robust"].values()]),
                         "combined_f1": r["robust"]["combined"]["macro_f1"], "bg_clutter_f1": r["robust"]["bg_clutter"]["macro_f1"], "bg_uniform_f1": bu,
                         "perturbed_conf_wrong_rate": float(np.mean(cw))})
            for n, v in r["robust"].items(): rob_rows.append({"phase": phase, "arch": a, "seed": seed, "perturbation": n, **v})
T = pd.DataFrame(rows)
T[T.phase == 2].drop(columns="phase").to_csv(os.path.join(R, "model_benchmark_rob.csv"), index=False)
pd.DataFrame(rob_rows).to_csv(os.path.join(R, "robustness_results_phase_compare.csv"), index=False)

# ---- recipe decision on VALIDATION, seed 42 (criterion frozen in EXPERIMENTS.md)
dec = []
for a in ARCHS:
    p1c = np.load(os.path.join(RUNS, f"{a}_s42.npz"), allow_pickle=True); p2 = np.load(os.path.join(RUNS, f"{a}_s42_rob.npz"), allow_pickle=True)
    p1v = np.load(os.path.join(RUNS, f"{a}_s42_valpert_phase1.npz"), allow_pickle=True) if os.path.exists(os.path.join(RUNS, f"{a}_s42_valpert_phase1.npz")) else None
    yv = p2["val_y"]
    clean1, clean2 = macro_f1(yv, p1c["val_logits"].argmax(1)), macro_f1(yv, p2["val_logits"].argmax(1))
    pert2 = np.mean([macro_f1(yv, p2[f"valpert_{n}"].argmax(1)) for n in PERTS])
    pert1 = np.mean([macro_f1(yv, p1v[f"valpert_{n}"].argmax(1)) for n in PERTS]) if p1v is not None else np.nan
    dec.append({"arch": a, "val_clean_f1_phase1": clean1, "val_clean_f1_phase2": clean2, "val_pert_f1_phase1": pert1, "val_pert_f1_phase2": pert2,
                "delta_pert": pert2 - pert1, "delta_clean": clean2 - clean1,
                "adopt_robust": bool((pert2 - pert1) >= 0.10 and (clean1 - clean2) <= 0.03)})
D = pd.DataFrame(dec); D.round(4).to_csv(os.path.join(R, "phase2_recipe_decision_validation.csv"), index=False)

# ---- test-set comparison, mean over 3 seeds
cmp_ = T.groupby(["arch", "phase"]).agg(macro_f1=("macro_f1", "mean"), robust_f1=("robust_macro_f1", "mean"), combined_f1=("combined_f1", "mean"),
                                         bg_clutter_f1=("bg_clutter_f1", "mean"), bg_uniform_f1=("bg_uniform_f1", "mean"),
                                         conf_wrong=("perturbed_conf_wrong_rate", "mean"), sel80=("acc_at_80cov", "mean")).reset_index()
cmp_.round(4).to_csv(os.path.join(R, "phase2_comparison.csv"), index=False)

# ---- Phase 2 selection with the same weighted rule (only meaningful for architectures where the recipe is adopted)
sel1 = pd.read_csv(os.path.join(R, "model_selection.csv")).set_index("arch")
p2 = cmp_[cmp_.phase == 2].set_index("arch").loc[ARCHS]
mm = lambda s, inv=False: ((s.max() - s) if inv else (s - s.min())) / ((s.max() - s.min()) or 1)
N = pd.DataFrame({"f1": mm(p2.macro_f1), "sel": mm(p2.sel80), "rob": mm(p2.robust_f1), "size": mm(sel1.loc[ARCHS, "onnx_fp32_MB"], True), "lat": mm(sel1.loc[ARCHS, "lat_ms_x4"], True)})
p2["score"] = sum(W[k] * N[k] for k in W); p2["rank"] = p2.score.rank(ascending=False).astype(int)
p2.round(4).to_csv(os.path.join(R, "model_selection_rob.csv"))

pd.set_option("display.width", 220); pd.set_option("display.max_columns", 20)
print("RECIPE DECISION (validation, seed 42):"); print(D.round(3).to_string(index=False))
print("\nTEST, mean of 3 seeds (phase 1 clean-trained vs phase 2 robust-aug):"); print(cmp_.round(3).to_string(index=False))
print("\nPHASE 2 SELECTION (same weighted rule):"); print(p2[["macro_f1", "sel80", "robust_f1", "score", "rank"]].round(3).to_string())

# plot: per-perturbation macro-F1, phase 1 vs phase 2, for the architectures
RB = pd.DataFrame(rob_rows).groupby(["phase", "arch", "perturbation"]).macro_f1.mean().reset_index()
fig, axes = plt.subplots(1, 4, figsize=(15, 3.8), sharey=True)
for ax, a in zip(axes, ARCHS):
    for ph, col, lab in ((1, "#b5651d", "clean-trained"), (2, "#1b6e3f", "robust augmentation")):
        g = RB[(RB.arch == a) & (RB.phase == ph)].set_index("perturbation").loc[PERTS]
        ax.plot(range(len(PERTS)), 100 * g.macro_f1.values, "o-", color=col, label=lab, lw=1.4, ms=4)
    ax.set_title(SHORT[a], fontsize=10); ax.set_xticks(range(len(PERTS))); ax.set_xticklabels(PERTS, rotation=60, ha="right", fontsize=7); ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("Test macro-F1 (%)  (mean of 3 splits)"); axes[0].legend(frameon=False, fontsize=8)
fig.suptitle("SYNTHETIC ROBUSTNESS TEST: effect of robust augmentation (in-family perturbations, NOT field validation)", fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(PL, "phase1_vs_phase2_robustness.png"), dpi=170)
