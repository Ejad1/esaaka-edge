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

_(appended by the experiment scripts and then summarised here)_
