# Model card — Esaaka Edge leaf classifier

## Shipped model
* **MobileNetV3-Large** (timm `mobilenetv3_large_100`), ImageNet-pretrained, fine-tuned on BRACOL **with robust augmentation** (Phase 2, seed-42 run).
* **Why this model**: it is the winner of the pre-registered weighted selection rule applied to the Phase 2 models (score 0.763 vs 0.659 for MobileNetV3-Small, 0.570 Lite0, 0.011 B0). Its quality is within seed noise of the others, so the rule is largely deciding on robustness and calibration; MobileNetV3-Small (6.1 MB, ~25 ms) is the lighter alternative and was the Phase 1 winner. See `docs/EXPERIMENTS.md` for the rule, the sensitivity and what we would change.
* Format: FP32 ONNX, **16.8 MB**; runtime onnxruntime-web (WASM, single thread) ~14.2 MB. INT8 was rejected (see below).
* Input: one RGB image, centre-cropped to 2:1, 448x224, ImageNet normalisation. Output: 5 logits (healthy, leaf miner, rust, phoma, cercospora).
* Calibration: temperature T = 2.196 (fit on clean validation). Tiers: HIGH if confidence >= 0.624 and top1-top2 margin >= 0.20; MEDIUM if confidence >= 0.336; otherwise LOW (no diagnosis). Thresholds were chosen on clean validation only (smallest threshold whose accepted-prediction accuracy is >= 95% / 85%).
* Params 4.2 M. Training: AdamW, one-cycle LR 5e-4, <= 30 epochs with early stopping on validation macro-F1 (patience 10), batch 32, sqrt-inverse-frequency class weights, mixed precision, random-resized-crop/flips/colour jitter plus random blur, brightness, contrast, JPEG and synthetic-background augmentation.

## Intended use
Triage aid for a smallholder to decide *whether to ask an extension officer*, on a **detached coffee leaf laid on a plain surface**, offline. Four problems + a "healthy leaf" outcome.

## Out of scope (do not use for)
Leaves on the plant or with natural backgrounds; Robusta; other crops; coffee berry disease, wilt, nutrient deficiency; any decision to spray or dose a chemical; replacing an agronomist. The app refuses or abstains in many of these cases but is **not validated** for them.

## Measured performance (BRACOL held-out test, 202 images)
| | value |
|---|---|
| Accuracy / macro-F1, shipped run (seed 42) | 0.921 / 0.900 |
| Macro-F1 mean over 3 splits (robust-trained) | 0.912 (clean-trained: 0.900 +/- 0.002) |
| Mean macro-F1 over 10 synthetic perturbations | 0.876 (clean-trained: 0.706) |
| System on clean test (gate + HIGH tier) | answers 84.2%, accuracy on answered 95.9%, 3.5% of all images confidently wrong |
| Browser latency (dev laptop, WASM 1 thread) | 70 ms median; 299 ms / 529 ms under emulated 4x / 6x CPU throttle (not a phone) |

Per-class precision/recall: `results/per_class_metrics.csv` (clean-trained) and the Phase 2 tables. **Minority classes have only 21-22 test images**, so per-class numbers are noisy.

## Known failure modes (measured)
* **Field photos**: the Phase 1 (clean-trained) models are near chance on Ugandan farm photos (3-class accuracy 0.24-0.44) and over-predict rust; on RoCoLe (Robusta) healthy leaves are almost always called diseased. The final robust-trained model is reported in `results/external_eval_rob.csv`. **We make no field-validity claim.**
* **Out-of-scope disease**: for red spider mite (not a class), clean-trained models gave a confident disease label on 38-75% of images depending on model and preprocessing (90% for the Phase 1 model shipped in the browser at the time); abstention on confidence alone does not catch it.
* **Several stresses on one leaf** (BRACOL class 5, exploratory): the Phase 1 browser model still answered HIGH on 73% of them (not re-measured for the final model).
* **Gate**: calibrated on BRACOL captures; rejects 8.9% of clean test images, plain grey backgrounds (79%), strongly contrasted images; blind to heavy JPEG compression. Resolution dependent.

## Quantisation (rejected, measured)
Static INT8 (QDQ) cut size 3.6x but: macro-F1 fell by 10-28 points for MobileNetV3/EfficientNet-B0 (3.4 for EfficientNet-Lite0), it was **slower than FP32 in onnxruntime-web**, and logits differed by up to 11 between onnxruntime Python and onnxruntime-web (argmax agreement as low as 3/8), so INT8 accuracy measured in Python would not hold in the browser.

## Ethical considerations
No personal data is collected; photos and results stay on the device unless the user shares them. See `docs/RESPONSIBLE_AI.md`.
