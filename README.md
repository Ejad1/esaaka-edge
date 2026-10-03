# Esaaka Edge

**An offline-first coffee-leaf triage tool that runs on the phone a farmer already owns, and says "I am not sure — ask a person" instead of guessing.**

Hack-Nation x World Bank Youth Summit 2026 — Challenge 4, *Small AI for Development*, Agriculture track (persona: Noor, 2 ha of coffee, patchy connectivity, rare extension visits).

> **Status: working prototype.** Everything marked REAL below is implemented and was measured. Anything marked MOCK or FUTURE is not claimed as working.

## What it does

1. Noor lays a coffee leaf on a plain surface and takes a photo.
2. **On the phone, with no connection**, an input-quality gate checks the photo (blur, exposure, contrast, busy background, leaf visible). A bad photo is *not diagnosed*; she is told how to retake it.
3. A 6 MB image classifier (MobileNetV3-Small, ONNX, run with onnxruntime-web/WASM) returns a calibrated confidence for 4 problems + healthy leaf.
4. Three outcomes, from a **fixed list of answers**: `HIGH` probable problem + cautious advice, `MEDIUM` "possible, not sure", `LOW` **no diagnosis, show it to an extension officer**.
5. The observation is saved on the device (IndexedDB). When she is back in signal she can share it (Web Share / WhatsApp) with the extension officer: store-and-forward.

| Component | Status |
|---|---|
| On-device inference, offline PWA, local storage, tiers, FR/EN UI | **REAL** (end-to-end offline test, see `results/e2e_offline.json`) |
| Input-quality gate | **REAL**, evaluated on synthetic perturbations (see `docs/EXPERIMENTS.md`) |
| Ewe interface | **Structure REAL, translations pending**: `pwa/src/i18n/ee.json` is empty on purpose; no machine-invented Ewe. French is shown until a native speaker fills it (`pwa/EWE_TRANSLATION_WORKSHEET.md`) |
| Sharing with an extension officer | **REAL** via Web Share / WhatsApp link; no server |
| Server-side sync, officer dashboard, more crops, voice in Ewe | **FUTURE** |

## Why AI and not an SMS, a spreadsheet or a search?

Telling coffee-leaf rust from leaf miner or brown-eye spot is a *visual pattern-recognition* task. A farmer cannot describe the symptom in an SMS in a form a lookup table can use, and a web search needs a connection and a vocabulary she does not have. A small vision model compressed to 6 MB can do it in the field, in ~50 ms, offline.

## Headline results (read the caveats)

* In-domain test (BRACOL, held-out, 202 images): accuracy 0.93, macro-F1 0.92 for the shipped split; **mean over 3 random splits 0.906 +/- 0.038**. Differences between the four architectures we benchmarked are *within seed noise*; the choice was driven by edge cost (6.1 MB, 25 ms in-browser vs 13-17 MB, 70-170 ms).
* **Quantisation (INT8) was rejected** after measurement: it hurt accuracy a lot for architectures with squeeze-excite/swish, was *slower* than FP32 in the browser, and was not numerically reproducible between onnxruntime Python and onnxruntime-web.
* **Distribution shift is a real weakness** and we report it: under strong synthetic perturbation (blur + darkness + cluttered background + JPEG) macro-F1 collapses to ~0.2 for every model, and confidence-based abstention alone does *not* protect. This is why the app has an input-quality gate and a capture protocol. Details and the remedies we tested: `docs/EXPERIMENTS.md`, `docs/RESPONSIBLE_AI.md`.
* Offline end-to-end (Edge, no network, 202 images through the shipped pipeline): accuracy 0.936, 99% top-1 agreement with the Python pipeline, median 46 ms/image on a laptop CPU. **Not measured on a real low-end phone yet.**

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
