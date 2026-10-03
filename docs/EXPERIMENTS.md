# Experiments — protocol (pre-registered before results)

> Written **before** any model was trained, so the selection rule cannot be tuned after seeing results.
> Results sections are appended below the protocol as they are produced. Anything marked
> `EXPLORATORY` is not a validated claim.

## 1. Question

Which edge-suitable image classifier gives the best **accuracy / size / latency / reliability-under-abstention**
trade-off for on-device triage of Arabica coffee-leaf stress, under the Hack-Nation *Small AI* rules
(runs on a phone the user already has, core feature offline, small files)?

## 2. Data (three explicit levels)

| Level | Purpose | Source |
|---|---|---|
| Training | fit weights | BRACOL leaf images (recovered subset, see DATA_CARD) |
| In-domain test | clean generalisation | held-out BRACOL images, never used for fitting or model selection |
| Out-of-domain / robustness | distribution shift | (a) SYNTHETIC ROBUSTNESS TEST on held-out BRACOL; (b) external coffee datasets, see `experiments/datasets/CATALOG.md` |

* Classes (5): healthy, leaf miner, rust, phoma (brown leaf spot), cercospora.
* BRACOL class `5` ("several stresses, none predominant", n=59 recovered) is **excluded from training and
  evaluation of the 5-way classifier**; it is kept as an abstention probe only (EXPLORATORY).
* The official BRACOL split is not recoverable from the (truncated) published archive, so we use a
  **stratified 70/15/15 split with a fixed seed** (primary seed 42; seeds 1 and 2 used only to estimate variance).
  Near-duplicate leakage is checked with a perceptual hash across splits.
* Same split, same preprocessing and same evaluation code for every architecture.

## 3. Candidates (identical protocol)

`mobilenetv3_small_100`, `mobilenetv3_large_100`, `efficientnet_b0`, plus **one** extra:
`efficientnet_lite0` — justification: EfficientNet-B0/MobileNetV3 use squeeze-excite and swish/hard-swish,
which are known to be fragile under int8 quantisation; EfficientNet-Lite removes them by design for edge
integer inference. ImageNet-pretrained weights (timm) for all; input 224x448 (the dataset is 2:1).

## 4. Metrics

* Quality: accuracy, macro-F1 (with 95% bootstrap CI), per-class precision/recall, confusion matrix.
* Calibration: NLL, ECE (15 bins) before/after temperature scaling (T fit on validation only).
* Reliability / abstention: top-1 confidence and top1–top2 margin; coverage and accepted-prediction
  ("selective") accuracy at thresholds chosen **on validation only**.
* Edge: parameters, FP32 ONNX size, INT8 (static QDQ) size and INT8 accuracy drop, in-browser latency
  (onnxruntime-web, WASM, median/p95) on the dev laptop and under 4x/6x CPU throttling (**emulated**, not a phone),
  approximate memory.
* Robustness: SYNTHETIC ROBUSTNESS TEST — blur (2 levels), brightness (2), contrast (2), JPEG q15,
  rotation ±15°, synthetic background replacement, and a combined worst case. Reported as clean vs perturbed
  macro-F1, and with abstention applied using thresholds fixed on clean validation.
  **This is not field validation.**

## 5. Abstention policy (fixed before results)

Confidence = temperature-scaled max softmax; margin = p1 − p2.
* `HIGH` (show probable problem): confidence ≥ τ_hi **and** margin ≥ m.
* `MEDIUM` (show "possible", with warning): confidence ≥ τ_lo.
* `LOW` (no diagnosis, refer to extension officer): otherwise.
τ_hi is the smallest threshold whose accepted-prediction accuracy on **validation** is ≥ 95%;
τ_lo the smallest with ≥ 85%; m = 0.20. If a model cannot reach 95% on validation, τ_hi is set to the
validation maximum and this is reported as a reliability failure for that model.

## 6. Model selection rule (fixed before results)

Min-max normalise each criterion across the four candidates, then:

```
score = 0.30 * macroF1_test
      + 0.20 * selective_accuracy_at_80%_coverage (test)
      + 0.15 * mean_macroF1_over_perturbations (robustness)
      + 0.15 * (1 - size_int8_norm)
      + 0.20 * (1 - latency_norm)            # median browser latency, WASM, throttled 4x
```

Hard constraints: INT8 file ≤ 12 MB; INT8 macro-F1 within 3 points of FP32 (else the FP32 file is used and
its size is penalised instead). Highest raw accuracy does **not** automatically win.
Ranking stability is checked across the 3 split seeds; if the top choice is not stable, we say so.

## 6b. Speech (Ewe) — separate, exploratory

See `experiments/speech/`. The question is feasibility of MMS for Ewe under Small AI constraints, not
integration. Text-based Ewe stays in P0 unless a result clearly says otherwise.

## 6c. Phase 2 (post-hoc, motivated by Phase 1) — protocol written before Phase 2 results

**Why this phase exists.** Phase 1 (clean-trained models, rule in section 6) gave a winner whose reliability under
distribution shift is poor: with abstention thresholds fixed on clean validation, the worst-case perturbation
(`combined`) leaves the model confidently wrong (see Results). Phase 2 is therefore *post-hoc*, not part of the
original plan, and is reported as such.

* **Remedy A — robust augmentation at training time** (same 4 architectures x 3 seeds, same splits, same budget):
  random blur (sigma 0.5-5), brightness (0.45-1.7), contrast (0.45-1.7), JPEG (q 10-60) and synthetic background
  replacement (p=0.5) with parameters drawn at random. **Overlap caveat:** these are the same perturbation
  *families* as the SYNTHETIC ROBUSTNESS TEST (different, randomly drawn levels), so robustness gains are
  *in-family* and must not be read as field robustness.
* **Remedy B — on-device input-quality gate** (blur / exposure / contrast / background-uniformity / leaf-fill checks)
  with thresholds set on clean **validation** images only, evaluated on the perturbed **test** images.
* **Decision rule.** Recipe (clean vs robust) is chosen on **validation** perturbed images of the primary seed using
  the same weighted rule as section 6 with the same normalisation; the shipped model must also keep clean test
  macro-F1 within 2 points of the Phase 1 winner. Test-set numbers are then reported for the chosen model only
  (note: the test set has been looked at once in Phase 1, so Phase 2 test numbers are not fully blind).
* Additional diagnostic (EXPLORATORY): `bg_uniform` = leaf pasted on a neutral grey background, to separate
  "clutter sensitivity" from "background shortcut learning".

### Phase 2 decision criterion (frozen before any Phase 2 *perturbed* result was inspected)

Only clean-test accuracy/macro-F1 of the Phase 2 runs had been seen when this was written.

* **Recipe**: adopt robust augmentation for an architecture iff, on the **seed-42 validation** images, the mean
  macro-F1 over the 10 fixed perturbations improves by **>= 0.10 absolute** AND clean validation macro-F1 drops by
  **<= 0.03**. (Phase 1 validation-perturbed logits are computed from the shipped FP32 ONNX files.)
* **Architecture**: if the robust recipe is adopted, re-apply the section 6 weighted rule to the Phase 2 models
  (seed-averaged test metrics, same latency/size terms).
* **Gate**: thresholds are the 0.5th/99.5th percentile (widened until >= 95% of clean validation images pass) of each
  metric on clean validation images; the gate is judged on perturbed test images by rejection rate, and by
  system-level selective accuracy (gate AND confidence tier).

## 7. Results

All tables are generated by `scripts/make_results_md.py` from `results/*.csv`. Test set = 202 BRACOL images per split; means are over 3 random stratified splits (seeds 42, 1, 2). **SYNTHETIC ROBUSTNESS TEST is not field validation.**

### 7.1 Phase 1 — clean-trained architectures (pre-registered rule, section 6)

| Model | Params (M) | Accuracy | Macro-F1 | FP32 ONNX (MB) | INT8 ONNX (MB) / macro-F1 drop (pts, Python ORT) | Browser latency ms (x1 / x4 / x6 throttle, emulated) | Coverage @HIGH | Selective acc @HIGH | Selective acc @80% coverage | Robustness (mean macro-F1, 10 perturbations) | Score | Rank | Top-1 in N of 3 seeds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MobileNetV3-Small | 1.52 | 0.921 +/- 0.037 | 0.906 +/- 0.038 | 6.1 | 1.8 / 22.4 | 25 / 121 / 187 | 0.922 | 0.951 | 0.973 | 0.697 | 0.887 | 1 | 2 |
| MobileNetV3-Large | 4.21 | 0.917 +/- 0.003 | 0.900 +/- 0.002 | 16.8 | 4.7 / 9.7 | 70 / 299 / 528 | 0.894 | 0.954 | 0.975 | 0.706 | 0.623 | 2 | 1 |
| EfficientNet-B0 | 4.01 | 0.904 +/- 0.027 | 0.889 +/- 0.030 | 16.0 | 4.8 / 27.9 | 172 / 784 / 1240 | 0.927 | 0.940 | 0.979 | 0.640 | 0.261 | 4 | 0 |
| EfficientNet-Lite0 | 3.38 | 0.921 +/- 0.010 | 0.903 +/- 0.006 | 13.5 | 3.8 / 3.4 | 124 / 492 / 783 | 0.901 | 0.949 | 0.967 | 0.608 | 0.393 | 3 | 0 |

INT8 (static QDQ) was **rejected** for every candidate: INT8 macro-F1 dropped by more than 3 points, INT8 was *slower* than FP32 in the browser (e.g. MobileNetV3-Small 25 -> 40 ms, MobileNetV3-Large 70 -> 116 ms, EfficientNet-B0 172 -> 205 ms, EfficientNet-Lite0 124 -> 200 ms), and onnxruntime-web INT8 logits differed from onnxruntime Python by up to 11 (argmax agreement on 8 held-out images: MobileNetV3-Small 3/8, MobileNetV3-Large 8/8, EfficientNet-B0 7/8, EfficientNet-Lite0 7/8). FP32 ONNX/browser parity was exact (max abs logit diff < 8e-4, 8/8).

Sensitivity: with 5,000 random weight vectors around the pre-registered ones, win shares were MobileNetV3-Small 1.00, MobileNetV3-Large 0.00, EfficientNet-B0 0.00, EfficientNet-Lite0 0.00. **Quality differences between architectures are within seed noise** (SD up to 0.038 macro-F1); the Phase 1 choice was driven by edge cost.

### 7.2 Phase 2 (post-hoc) — robust augmentation

Criterion frozen in section 6c. Decision on **seed-42 validation** data:

| Model | Val clean F1 (clean / robust) | Val perturbed F1 (clean / robust) | Delta perturbed | Adopt robust recipe |
|---|---|---|---|---|
| MobileNetV3-Small | 0.917 / 0.930 | 0.699 / 0.861 | +0.161 | yes |
| MobileNetV3-Large | 0.912 / 0.907 | 0.704 / 0.870 | +0.167 | yes |
| EfficientNet-B0 | 0.917 / 0.912 | 0.655 / 0.834 | +0.179 | yes |
| EfficientNet-Lite0 | 0.913 / 0.918 | 0.636 / 0.851 | +0.216 | yes |

Test, mean of 3 splits (phase 1 clean-trained -> phase 2 robust-trained). Perturbations are the same *families* as the training augmentation, so gains are **in-family**:

| Model | Clean macro-F1 | Mean perturbed macro-F1 | `combined` F1 | `bg_clutter` F1 | `bg_uniform` F1 (diagnostic) | Model-only confident-wrong rate on perturbations |
|---|---|---|---|---|---|---|
| MobileNetV3-Small | 0.906 -> 0.901 | 0.697 -> 0.858 | 0.220 -> 0.803 | 0.465 -> 0.880 | n/a -> 0.899 | 0.162 -> 0.064 |
| MobileNetV3-Large | 0.900 -> 0.912 | 0.706 -> 0.876 | 0.193 -> 0.783 | 0.669 -> 0.903 | n/a -> 0.899 | 0.087 -> 0.044 |
| EfficientNet-B0 | 0.889 -> 0.891 | 0.640 -> 0.843 | 0.233 -> 0.766 | 0.632 -> 0.892 | n/a -> 0.878 | 0.153 -> 0.051 |
| EfficientNet-Lite0 | 0.903 -> 0.915 | 0.608 -> 0.844 | 0.244 -> 0.757 | 0.769 -> 0.908 | n/a -> 0.877 | 0.184 -> 0.051 |

Phase 2 selection (same weighted rule, same edge terms): MobileNetV3-Small 0.659 (rank 2), MobileNetV3-Large 0.763 (rank 1), EfficientNet-B0 0.011 (rank 4), EfficientNet-Lite0 0.570 (rank 3). **Shipped: MobileNetV3-Large (robust).** Honest note: its clean macro-F1 is within noise of MobileNetV3-Small, which is 2.8x smaller and faster; the pre-registered rule favours Large through its robustness and calibration terms (min-max normalisation amplifies small differences).

### 7.3 Input-quality gate and the whole system (shipped model, in-browser metrics)

Bounds learned on clean validation only (validation pass rate 0.96). System = gate AND confidence tier HIGH. Per condition, over the 202 test images (`results/system_eval_final.csv`):

| Condition | Model macro-F1 | Model HIGH-and-wrong | Gate rejects | System answers | System HIGH-and-wrong | Accuracy on answered |
|---|---|---|---|---|---|---|
| clean | 0.900 | 0.045 | 0.089 | 0.842 | 0.035 | 0.959 |
| blur_mild | 0.902 | 0.040 | 1.000 | 0.000 | 0.000 |  |
| blur_strong | 0.839 | 0.045 | 1.000 | 0.000 | 0.000 |  |
| bright_dark | 0.887 | 0.045 | 1.000 | 0.000 | 0.000 |  |
| bright_light | 0.888 | 0.059 | 0.995 | 0.005 | 0.000 | 1.000 |
| contrast_low | 0.899 | 0.040 | 1.000 | 0.000 | 0.000 |  |
| contrast_high | 0.882 | 0.035 | 0.876 | 0.119 | 0.000 | 1.000 |
| jpeg_q12 | 0.845 | 0.064 | 0.084 | 0.757 | 0.059 | 0.922 |
| rotate15 | 0.905 | 0.025 | 0.139 | 0.782 | 0.020 | 0.975 |
| bg_clutter | 0.908 | 0.045 | 1.000 | 0.000 | 0.000 |  |
| combined | 0.802 | 0.054 | 1.000 | 0.000 | 0.000 |  |
| bg_uniform | 0.900 | 0.050 | 0.792 | 0.183 | 0.025 | 0.865 |

Averaged over the 10 fixed perturbations: model-only confident-wrong 0.045 -> system 0.008, at the price of the gate refusing 81% of them (and 8.9% of clean images). **With robust training the model alone is already fairly safe on these perturbations, so the gate is now mostly a scope guard** (it also refuses plain grey backgrounds and high-contrast images that the model handles: over-specific, tuned to BRACOL captures).

External field photos (Uganda + RoCoLe, 2039 images): the gate rejects 100%. RoCoLe rejections are real out-of-protocol backgrounds (busy 100%, colourful 94%); Uganda rejections are partly a resolution artefact (256 px images upscaled, so a sharpness check fails). The gate is **resolution dependent**.

### 7.4 External field data, final model (model alone, thresholds from clean BRACOL validation; image padded to 2:1 or stretched)

| Dataset | Preprocessing | Accuracy / macro-F1 (3 classes) or AUROC | Recall healthy / rust (/ phoma) | HIGH-tier coverage | Notes |
|---|---|---|---|---|---|
| Uganda (n=1800, ~1168 unique) | pad | 0.544 / 0.564 | 0.47 / 0.56 / 0.60 | 0.63 (acc 0.60) | chance for 3 classes = 0.33 |
| Uganda (n=1800, ~1168 unique) | stretch | 0.453 / 0.483 | 0.41 / 0.56 / 0.38 | 0.34 (acc 0.62) | chance for 3 classes = 0.33 |
| RoCoLe (n=239) | pad | AUROC rust vs healthy 0.792 | 0.17 / 0.31 | 0.64 | red spider mite given a confident disease label: 0.62 |
| RoCoLe (n=239) | stretch | AUROC rust vs healthy 0.810 | 0.16 / 0.40 | 0.58 | red spider mite given a confident disease label: 0.68 |

### 7.5 Ewe speech feasibility (EXPLORATORY: 24 utterances, one corpus, CPU)

Eval set: WAXAL Ewe ASR test shard 1 (human transcriptions, spontaneous image-prompted speech, CC-BY / CC-BY-SA). Only the smallest Ewe MMS-based model was benchmarked; the 1B-parameter models (`facebook/mms-1b-all` 965M params / 3.86 GB; community adapters on the same base) were **not** benchmarked because size alone rules them out. Their self-reported scores are unverified.

| System | Params | FP32 size | WER | CER | CPU RTF (6 threads) | Notes |
|---|---|---|---|---|---|---|
| MMS-300M fine-tuned on WAXAL Ewe (community, CC-BY-NC-4.0) | 316 M | 1262 MB | 0.316 | 0.099 | 0.47 | peak RSS ~2.1 GB; model card claims WER 31.3 / CER 9.6 on WAXAL test |
| same, dynamic INT8 (Linear layers) | | 355 MB | 0.322 | 0.100 | 0.33 | still ~60x our vision model |
| MMS-TTS Ewe (Meta, CC-BY-NC-4.0) | 36.3 M | 145 MB | n/a | n/a | 0.55 | quality needs a native speaker; 5 samples in `results/speech/tts_samples/` |

**Decision: Ewe voice input is not embedded.** Text Ewe stays in P0 (translations to be supplied by a native speaker). A feasible route is *pre-generated* audio of the fixed answers from validated Ewe text. ONNX export of the 300M model was not tested (missing `onnxscript` in the environment), so ONNX feasibility is inconclusive, not negative. Umbaji's `Umbaji/Yodi` (Ewe+English ASR, Keras `.h5`) is gated (manual approval) and CC-BY-NC-3.0, so it could not be benchmarked.


### 7.6 Field adaptation (prepared, NOT trained in time)

Because the model fails on real field photos (7.4), we prepared a field-adapted v2: BRACOL + Uganda + RoCoLe for **training**, with a 6th class `other`
(BRACOL multi-stress leaves + RoCoLe red spider mite) so the model can learn to say "no diagnosis". Leak control: Uganda has augmented copies, so its
3,220 usable images were clustered with a flip/rotation-invariant perceptual hash into 1,740 groups and whole groups were assigned to one split; RoCoLe was
split by plant (`C#P#`). Resulting split: train 3,487 / validation 746 / test 746 images (RoCoLe limited to 358 photos because of download speed).
Because these sources are then used for training, **they stop being independent external data**, and test numbers from the same farms would be optimistic.

Status: data preparation (`experiments/datasets/prepare_field_v2.py`), the training/analysis scripts (`train_modal.py --field`, `analyze_v2.py`) and a re-learned gate exist, but the
GPU run was **not executed**: uploading the dataset to the cloud volume did not finish in the time available (very slow connection). The shipped model is therefore still the one in 7.2.

Gate re-learned for a field model (`experiments/robustness/guard_v2.py`, bounds on v2 validation, phone-resolution sources only): 96.6% of BRACOL+RoCoLe validation images pass.
On held-out test the gate rejects 2.8% of BRACOL, 27.8% of RoCoLe photos and 93% of Uganda photos; the Uganda rejection is mostly a **resolution artefact** (256 px images upscaled),
which is why those images were excluded from setting the bounds. A first version of the rule let Uganda drive the bounds and produced a 41% pass rate; that was a flaw in the rule and was corrected before any model result existed.

### 7.7 First manual test of the deployed app (2026-10-03)
Maize/sorghum field photos were refused by the gate (too dark, busy and colourful background), as designed. A coffee leaf on a plain sheet was classified with a displayed
confidence of "100 %", which is misleading for a model with known over-confidence under shift; the display is now capped at 99%. It also confirms the main limitation: only
a detached leaf on a plain surface is handled.
