# Responsible AI, data and safety

Mapped to the Hack-Nation pass/fail question: *are the limits respected, and is the account of privacy, consent, bias and human oversight credible?*

## 1. The tool informs; a person decides
* Three outcomes only, drawn from a **fixed list of answers**: `HIGH` (probable problem), `MEDIUM` ("possible, but I am not sure; this is not a diagnosis"), `LOW` (**no diagnosis**, "show this leaf to an extension officer"). A bad photo gets *no diagnosis at all* and a retake instruction.
* The tool never acts for the user. The only outward action is sharing an observation with an extension officer, and only when the user taps the button.
* **No chemical names, no doses, no spray advice.** The advice texts are general cultural practices and always end with "have an extension officer confirm". They are drafted from general coffee-agronomy knowledge and are **not yet validated by an agronomist**; the app says so.
* No free-text generation: nothing can be hallucinated because every sentence shown is from the fixed list.

## 2. Uncertainty is shown and used
* Calibrated confidence (temperature scaling on validation) and a top-1/top-2 margin gate the three tiers; thresholds are fixed on clean validation and never tuned on test or field data.
* An input-quality gate refuses blurred, dark, over-bright, low-contrast, cluttered or leaf-less photos instead of guessing.

## 3. What we measured about reliability (including the bad news)
* On a **synthetic robustness test** (not field validation), the clean-trained model became confidently wrong; confidence-based abstention alone did not protect (Phase 1). Robust training reduced this a lot (model-only confident-wrong on perturbed images from 9-18% to 4-6% across the four architectures), and the gate reduces it further (to under 1%) at the cost of refusing most perturbed photos.
* On **external field photos** (Uganda, RoCoLe) the clean-trained models did not generalise and gave confident wrong answers; the gate refuses all of these photos (100%), which prevents confident errors but also means **the tool does not work on photos taken on the plant**. The protocol (leaf on a plain surface) is a product constraint, stated to the user in the app.
* Abstention fails for out-of-scope disease (red spider mite) and multi-stress leaves when relying on confidence alone. Listed as limitations, not fixed.
* Full numbers: `docs/EXPERIMENTS.md`, `results/`.

## 4. Privacy and consent
* Inference runs **on the phone**; the photo is not uploaded. The app makes no network request other than loading itself (the offline end-to-end test recorded zero failed requests while offline). No analytics, no accounts, no identifiers.
* Observations (photo, result, quality metrics) are stored in the browser's IndexedDB on the device and can be deleted by the user. **Sharing is explicit** (Web Share / WhatsApp), per observation. Photos of leaves can still show a farm or people; the user decides what to send.
* Data protection law for health-like or location data is not triggered because no location or personal data is collected, but any future server sync must add consent, retention limits and a data-processing agreement.

## 5. Bias and inclusion
* Training data is Brazilian Arabica on a plain background; not African, not Robusta, not on-plant. Performance for Togolese or Ugandan farms is **unknown**.
* The interface is text-heavy; farmers with low literacy are not yet served. Voice is not implemented (see Ewe, below). Large buttons and a one-screen flow reduce, not remove, this barrier.
* Class imbalance (rust 3.4x cercospora) may make minority-class errors more frequent; per-class recall is reported and minority test sets are tiny.

## 6. Local language, honestly
* French and English are complete. **Ewe is not machine-translated**: the Ewe interface file is intentionally empty until a native speaker supplies validated text (`pwa/EWE_TRANSLATION_WORKSHEET.md`); until then French is shown with a visible notice.
* Ewe speech was studied, not integrated: the smallest Ewe MMS ASR we found is 315M parameters (1.26 GB, WER 32% on 24 conversational utterances), far beyond a 20-30 MB offline budget; Ewe TTS is 145 MB. Meta MMS and the Umbaji Yodi model are CC-BY-NC (Yodi also gated), a barrier for commercial use. How it would fare in a less-supported language: the vision core is language-independent; adding a language means validated strings, not retraining.

## 7. Security and robustness
* Static app, no server, no secrets. Model file integrity is recorded (SHA-256 in `model_config.json`). Service worker updates automatically.
* The gate and thresholds are tuned to BRACOL capture conditions and need recalibration with field photos taken under the protocol before any real deployment.

## 8. What would make this safe to pilot
Agronomist review of every advice text; photos of real leaves from target farms (labelled by an extension officer) to recalibrate the gate and thresholds; validated Ewe text and audio; a real-phone latency and battery test; a clear escalation channel with a named extension officer.
