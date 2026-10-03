"""Apply the PRE-REGISTERED selection rule (docs/EXPERIMENTS.md section 6) and draw the plots.

Quality terms use the mean over the 3 split seeds. Edge terms come from the primary-seed ONNX files and the
browser benchmark. INT8 failed the pre-registered viability rule for every candidate (see EXPERIMENTS.md),
so the deployed file is FP32 and its size is what is penalised.
"""
import json, os, pickle
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
R = os.path.join(ROOT, "results"); PL = os.path.join(R, "plots"); os.makedirs(PL, exist_ok=True)
ARCHS = ["mobilenetv3_small_100", "mobilenetv3_large_100", "efficientnet_b0", "efficientnet_lite0"]
SHORT = {"mobilenetv3_small_100": "MobileNetV3-S", "mobilenetv3_large_100": "MobileNetV3-L", "efficientnet_b0": "EfficientNet-B0", "efficientnet_lite0": "EfficientNet-Lite0"}
COL = {"mobilenetv3_small_100": "#1b6e3f", "mobilenetv3_large_100": "#4c9f70", "efficientnet_b0": "#b5651d", "efficientnet_lite0": "#2a6fb0"}
W = dict(f1=0.30, sel=0.20, rob=0.15, size=0.15, lat=0.20)

bm = pd.read_csv(os.path.join(R, "model_benchmark.csv")); rob = pd.read_csv(os.path.join(R, "robustness_results.csv"))
lat = {r["model"]: r for r in json.load(open(os.path.join(R, "browser_latency.json")))["results"]}
summ = {(s["arch"], s["seed"]): s for s in json.load(open(os.path.join(R, "vision_runs_summary.json")))}

fp = bm[bm.precision == "fp32"]
rows = []
for a in ARCHS:
    d = fp[fp.arch == a]; rb = rob[(rob.arch == a) & (rob.precision == "fp32")]
    i8 = bm[(bm.arch == a) & (bm.precision == "int8")].iloc[0]; f32p = fp[(fp.arch == a) & (fp.seed == 42)].iloc[0]
    rows.append({"arch": a, "params_M": summ[(a, 42)]["params"] / 1e6, "acc_mean": d.acc.mean(), "acc_sd": d.acc.std(),
                 "macro_f1_mean": d.macro_f1.mean(), "macro_f1_sd": d.macro_f1.std(),
                 "sel_acc_at_80cov": d.acc_at_80cov.mean(), "cov_hi": d.cov_hi.mean(), "sel_acc_hi": d.sel_acc_hi.mean(),
                 "ece_cal": d.ece_cal.mean(), "robust_macro_f1": rb.groupby("seed").macro_f1.mean().mean(),
                 "onnx_fp32_MB": summ[(a, 42)]["onnx_fp32_bytes"] / 1e6, "onnx_int8_MB": summ[(a, 42)]["int8_bytes"] / 1e6,
                 "int8_macro_f1_drop_pts(py-ort)": 100 * (f32p.macro_f1 - i8.macro_f1),
                 "lat_ms_x1": lat[f"{a}_fp32"]["latency_x1"]["median"], "lat_ms_x4": lat[f"{a}_fp32"]["latency_x4"]["median"],
                 "lat_ms_x6": lat[f"{a}_fp32"]["latency_x6"]["median"], "lat_int8_ms_x1": lat[f"{a}_int8"]["latency_x1"]["median"],
                 "int8_browser_parity_agree": f"{lat[f'{a}_int8']['parity']['argmaxAgree']}/{lat[f'{a}_int8']['parity']['n']}",
                 "mem_delta_MB": lat[f"{a}_fp32"]["memDeltaMB"]})
T = pd.DataFrame(rows).set_index("arch")
mm = lambda s, inv=False: ((s.max() - s) if inv else (s - s.min())) / ((s.max() - s.min()) or 1)
N = pd.DataFrame({"f1": mm(T.macro_f1_mean), "sel": mm(T.sel_acc_at_80cov), "rob": mm(T.robust_macro_f1),
                  "size": mm(T.onnx_fp32_MB, inv=True), "lat": mm(T.lat_ms_x4, inv=True)})
T["score"] = sum(W[k] * N[k] for k in W)
T["rank"] = T.score.rank(ascending=False).astype(int)

# stability: per-seed quality terms, with fixed edge terms
stab = {a: 0 for a in ARCHS}
for seed in (42, 1, 2):
    d = fp[fp.seed == seed].set_index("arch"); rb = rob[(rob.seed == seed) & (rob.precision == "fp32")].groupby("arch").macro_f1.mean()
    Ns = pd.DataFrame({"f1": mm(d.macro_f1.loc[ARCHS]), "sel": mm(d.acc_at_80cov.loc[ARCHS]), "rob": mm(rb.loc[ARCHS]), "size": N["size"], "lat": N["lat"]})
    stab[sum(W[k] * Ns[k] for k in W).idxmax()] += 1
T["top1_in_seeds_of_3"] = pd.Series(stab)
# sensitivity: random weights around the pre-registered ones
rng = np.random.default_rng(0); wins = {a: 0 for a in ARCHS}; base = np.array([W[k] for k in W])
for _ in range(5000):
    w = rng.dirichlet(base * 20); wins[ARCHS[int((N[list(W)].values @ w).argmax())]] += 1
T["win_share_random_weights"] = pd.Series({a: wins[a] / 5000 for a in ARCHS})
T.round(4).to_csv(os.path.join(R, "model_selection.csv"))
print(T[["params_M", "macro_f1_mean", "macro_f1_sd", "sel_acc_at_80cov", "robust_macro_f1", "onnx_fp32_MB", "lat_ms_x4", "score", "rank", "top1_in_seeds_of_3", "win_share_random_weights"]].round(3).to_string())

# ---- plots
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
for a in ARCHS:
    ax[0].errorbar(T.loc[a, "onnx_fp32_MB"], 100 * T.loc[a, "acc_mean"], yerr=100 * T.loc[a, "acc_sd"], fmt="o", color=COL[a], capsize=3, label=SHORT[a])
    ax[1].errorbar(T.loc[a, "lat_ms_x4"], 100 * T.loc[a, "macro_f1_mean"], yerr=100 * T.loc[a, "macro_f1_sd"], fmt="o", color=COL[a], capsize=3)
ax[0].set(xlabel="FP32 ONNX size (MB)", ylabel="Test accuracy (%) — mean ± SD over 3 splits", title="Accuracy vs model size"); ax[0].legend(frameon=False, fontsize=8)
ax[1].set(xlabel="Browser latency (ms, WASM, 4x CPU throttle — emulated)", ylabel="Test macro-F1 (%) — mean ± SD", title="Macro-F1 vs latency")
fig.tight_layout(); fig.savefig(os.path.join(PL, "tradeoffs.png"), dpi=170); plt.close(fig)

st = pickle.load(open(os.path.join(R, "_analysis_store.pkl"), "rb"))
fig, ax = plt.subplots(figsize=(5.2, 4))
sel_df = pd.read_csv(os.path.join(R, "selective_prediction.csv")); sel_df = sel_df[sel_df.precision == "fp32"]
for a in ARCHS:
    g = sel_df[sel_df.arch == a].groupby("coverage").selective_accuracy.mean()
    ax.plot(100 * g.index, 100 * g.values, color=COL[a], label=SHORT[a], lw=1.6)
ax.set(xlabel="Coverage (% of images the model answers)", ylabel="Accuracy on answered images (%)", title="Selective accuracy vs coverage (clean test)", ylim=(80, 101.5))
ax.legend(frameon=False, fontsize=8, loc="lower left"); fig.tight_layout(); fig.savefig(os.path.join(PL, "selective_accuracy_vs_coverage.png"), dpi=170); plt.close(fig)

rb = rob[rob.precision == "fp32"].groupby(["arch", "perturbation"]).agg(macro_f1=("macro_f1", "mean"), cov=("cov_hi", "mean"), sel=("sel_acc_hi", "mean")).reset_index()
names = ["clean"] + list(rb.perturbation.unique())
fig, ax = plt.subplots(figsize=(10, 4)); x = np.arange(len(names)); bw = 0.2
for i, a in enumerate(ARCHS):
    vals = [fp[fp.arch == a].macro_f1.mean()] + [rb[(rb.arch == a) & (rb.perturbation == n)].macro_f1.iloc[0] for n in names[1:]]
    ax.bar(x + (i - 1.5) * bw, 100 * np.array(vals), bw, color=COL[a], label=SHORT[a])
ax.set_xticks(x); ax.set_xticklabels(names, rotation=30, ha="right"); ax.set(ylabel="Macro-F1 (%)", title="SYNTHETIC ROBUSTNESS TEST — clean vs perturbed (mean of 3 splits; NOT field validation)")
ax.legend(frameon=False, fontsize=8, ncol=4); fig.tight_layout(); fig.savefig(os.path.join(PL, "robustness_clean_vs_perturbed.png"), dpi=170); plt.close(fig)
rb.to_csv(os.path.join(R, "robustness_summary_by_perturbation.csv"), index=False)
print("\nrobustness (mean macro-F1 by perturbation):"); print(rb.pivot(index="perturbation", columns="arch", values="macro_f1").round(3).to_string())
print("\nwith abstention (tau_hi fixed on clean val) — coverage / selective accuracy:")
print(rb.pivot(index="perturbation", columns="arch", values="cov").round(2).to_string()); print(rb.pivot(index="perturbation", columns="arch", values="sel").round(3).to_string())
