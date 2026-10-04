# Esaaka Edge

**An offline-first coffee-leaf triage tool that runs on the phone a farmer already owns, and says "I am not sure — ask a person" instead of guessing.**

Hack-Nation x World Bank Youth Summit 2026 — Challenge 4, *Small AI for Development*, Agriculture track (persona: Noor, 2 ha of coffee, patchy connectivity, rare extension visits).

> **Status: working prototype.** Everything marked REAL below is implemented and was measured. Anything marked MOCK or FUTURE is not claimed as working.

## What it does

1. Noor lays a coffee leaf on a plain surface and takes a photo.
2. **On the phone, with no connection**, an input-quality gate checks the photo (blur, exposure, contrast, busy background, leaf visible). A bad photo is *not diagnosed*; she is told how to retake it.
3. A 16.8 MB image classifier (MobileNetV3-Large trained with robust augmentation, FP32 ONNX, run with onnxruntime-web/WASM) returns a calibrated confidence for 4 problems + healthy leaf.
4. Three outcomes, from a **fixed list of answers**: `HIGH` probable problem + cautious advice, `MEDIUM` "possible, not sure", `LOW` **no diagnosis, show it to an extension officer**.
5. The observation is saved on the device (IndexedDB). When she is back in signal she can share it (Web Share / WhatsApp) with the extension officer: store-and-forward.

| Component | Status |
|---|---|
| On-device inference, offline PWA, local storage, tiers, FR/EN UI | **REAL** (end-to-end offline test, see `results/e2e_offline.json`) |
| Input-quality gate | **REAL**, evaluated on synthetic perturbations (see `docs/EXPERIMENTS.md`) |
| Ewe interface | **Text only, UNVALIDATED machine translation (Google Translate FR->EE, cross-checked EN->EE and back-translated), done at authoring time; the app calls nothing external.** 49 of 58 strings shipped; 9 with wrong or doubtful back-translation are left empty and fall back to French. Advice texts: 12 of 18 sentences machine-translated to Ewe (`pwa/EWE_ADVICE_REVIEW.md`), each shown with its French original underneath; 6 with wrong back-translation (e.g. 'doctor' for extension officer, 'orange powder' as 'olive smell') are left in French. A native speaker must review `pwa/EWE_REVIEW.md` before any real use |
| Sharing with an extension officer | **REAL** via Web Share / WhatsApp link; no server |
| Server-side sync, officer dashboard, more crops, voice in Ewe | **FUTURE** |

## Why AI and not an SMS, a spreadsheet or a search?

Telling coffee-leaf rust from leaf miner or brown-eye spot is a *visual pattern-recognition* task. A farmer cannot describe the symptom in an SMS in a form a lookup table can use, and a web search needs a connection and a vocabulary she does not have. A small vision model (17 MB) can do it in the field, in well under a second, offline.

## Headline results (read the caveats)

* **Model choice was benchmarked, not assumed**: 4 edge architectures x 3 random splits, same data/preprocessing, selection rule written *before* seeing results (`docs/EXPERIMENTS.md`). In-domain macro-F1 is ~0.89-0.92 for all of them, i.e. **differences are within seed noise (SD up to 0.038)**.
* **Quantisation (INT8) was rejected after measurement**: large accuracy drops for most architectures, *slower* than FP32 in the browser, and not numerically reproducible between onnxruntime Python and onnxruntime-web.
* **Distribution shift is real and we measured it.** Clean-trained models became confidently wrong under blur/darkness/clutter (combined perturbation: macro-F1 ~0.2), so a post-hoc phase added robust augmentation (perturbed macro-F1 0.70 -> 0.88, clean accuracy unchanged) and an input-quality gate. **These gains are in-family (same perturbation families as the test), not field validation.**
* **The shipped model (MobileNetV3-Large, robust)**: test accuracy 0.92 / macro-F1 0.90 (seed 42; mean macro-F1 0.912 over 3 splits). System on clean test: answers 84%, accuracy on answered 96%.
* **It still fails on real field photos**: Ugandan farm photos 0.54 accuracy for 3 classes (chance 0.33; the clean-trained model scored 0.41); RoCoLe healthy-vs-rust AUROC 0.79-0.81 with healthy leaves usually called diseased; an out-of-scope disease (red spider mite) gets a confident label 62-68% of the time. **We make no field-validity claim**; the quality gate refuses all of those photos (the tool is for a detached leaf on a plain surface).
* Offline end-to-end (Edge, no network, 202 test images through the shipped *Phase 1* pipeline): accuracy 0.936, 99% top-1 agreement with Python, 0 failed requests. The final model/gate build was smoke-tested but not re-run on all 202 images. **Not measured on a real low-end phone yet** (laptop WASM: 70 ms for the shipped model).
* **Ewe voice is not embedded**: smallest Ewe MMS ASR found = 315M params / 1.26 GB, WER 32% (exploratory, 24 utterances). Text Ewe stays in P0.

## Data and its limits (scored, so stated plainly)

* Training/test: **BRACOL** (Mendeley Data, CC BY 4.0): Arabica leaves, Brazil, **detached leaves on a plain sheet**. The published archive is truncated at source: we recovered 1,401 of 1,747 labelled images. See `docs/DATA_CARD.md`.
* It does **not** cover: African field conditions, Robusta, leaves on the plant, coffee berry disease, wilt, nutrient deficiency, other crops.
* External field sets (Uganda, RoCoLe) were used only for evaluation, never for training or thresholds. See `experiments/datasets/CATALOG.md` and `results/external_eval.csv`.

## Run it

```bash
cd pwa
npm install
npm run build
npx vite preview --port 4173        # open http://localhost:4173 (HTTPS is required on a phone: deploy `pwa/` to Vercel/Netlify)
```

Offline end-to-end test (in a second shell, with the preview running): `node tests/e2e_offline.mjs`.

Reproduce the benchmark: `experiments/` (data preparation, Modal GPU training, analysis, in-browser benchmark). Data is downloaded from the sources listed in `docs/DATA_CARD.md`; it is not stored in this repo.

## Repository map

`pwa/` the app · `experiments/vision` benchmark, selection rule, in-browser bench · `experiments/robustness` synthetic robustness test and quality gate · `experiments/datasets` data preparation and external evaluation · `experiments/speech` Ewe speech feasibility (exploratory) · `results/` tables and plots · `docs/` data card, model card, experiments, responsible AI.

## Licences and attribution

* BRACOL: Krohling, Esgario, Ventura, CC BY 4.0. RoCoLe and the Uganda coffee-leaf dataset: CC BY 4.0 (evaluation only).
* Models: ImageNet-pretrained weights via `timm`, fine-tuned by us.
* Meta MMS models studied in `experiments/speech` are **CC-BY-NC 4.0** (non-commercial): a constraint for any commercial use.
* Code licence: to be decided by the authors.

*Advice texts are general, conservative and **not yet validated by an agronomist**. This tool supports a decision; a person makes it.*
