# Video script (target 4:00, limit 5:00)

Record the demo part on a **real phone, in airplane mode**, screen-recorded. `[UPDATE]` = fill from the final results before recording.

## Problem statement (put on screen, read aloud once)

> **Because of Esaaka Edge, a smallholder coffee farmer like Noor can check a suspicious leaf on her own phone, in the field, with no signal, and get either a cautious next step or a clear "not sure, ask a person", days earlier than waiting for an extension visit; we know because the World Bank brief says the officer reached her village twice last year and extension services are short of staff, and because our offline test shows the tool answers on the phone in well under a second and refuses to diagnose when the photo or its confidence is not good enough.**

## 0:00 – 0:30 · Noor and the gap
*Screen: Noor persona (name only, she is fictional) + a coffee leaf.*
"Noor farms two hectares of coffee. Her yields have slipped and she does not know why. The extension officer reached her village twice last year. She has a phone, no Wi-Fi, and data bundles she buys when she must. When she sees a spotted leaf on the slope, she has nobody to ask, and no signal to ask with."

## 0:30 – 1:00 · Why AI, and not an SMS, a spreadsheet or a search
"Telling coffee-leaf rust from leaf miner or brown-eye spot is a visual task. Noor cannot describe a lesion in an SMS in a way a lookup table understands, and a web search needs a connection and a vocabulary she does not have. A small vision model, 17 megabytes, can look at the leaf itself, on the phone she already owns, with zero bars."

## 1:00 – 2:15 · Demo, airplane mode on (screen recording)
1. Show airplane mode on, open the installed app. Point at the **"Works offline"** badge and the red offline dot.
2. Lay a leaf on a plain surface (or show a leaf photo on a plain sheet), tap **Take a photo**.
3. Result screen: say the tier out loud (HIGH or MEDIUM), the confidence, the cautious advice, and **"Analysed on this phone in N ms, without sending your photo"**.
4. Retake with a **blurry or busy-background photo**: the app refuses ("Photo to retake") and says why. *"It would rather ask for a better photo than guess."*
5. Show a **LOW-confidence** result (use a leaf of a different disease/object): *"I cannot identify this problem. Show this leaf to an extension officer."*
6. Open **My observations**: saved on the phone, "waiting to be sent". Tap **Ask the extension officer**: share sheet with the photo and a short message (WhatsApp). *"Store and forward: the record waits on the phone until there is a signal."*
7. Switch language FR / EN. **Ewe**: `[UPDATE]` only if validated translations/audio are in; otherwise say honestly: "The Ewe slot is built; we do not machine-translate Ewe, so it is waiting for validated text from a native speaker."

## 2:15 – 3:00 · Guardrails and evidence (slides with the plots)
* "Three outcomes only, from a fixed list of answers: probable, possible-but-not-sure, or **no diagnosis**. No pesticide names, no doses. A person makes the final call."
* "We did not pick the first model that worked. We benchmarked four edge architectures on identical splits, three random splits each. Accuracy differences are inside the noise (about 0.90 macro-F1). Our pre-registered rule, re-applied after we added robust training, chose MobileNetV3-Large: 17 MB, about 70 ms in a browser on a laptop; we have not measured a real phone yet." *(show `tradeoffs.png`)*
* "We tested quantisation and **rejected it**: it was slower in the browser and not reproducible across runtimes."
* "We tested distribution shift on purpose. On blurred, dark, cluttered photos the model becomes confidently wrong, so confidence alone is not a safe abstention. That is why the app has a **photo-quality gate** and a capture protocol." *(show `gate_confident_wrong.png`)* `[UPDATE: one sentence with the measured reduction in confidently-wrong answers]`
* "On real African field photos from Uganda, our Brazilian-trained model does **not** generalise: near chance. We report it, and we do not claim field validity." *(show external results)*

## 3:00 – 3:30 · Stack and data
"BRACOL, a public CC-BY dataset of Arabica leaves, which is lab-like and Brazilian. MobileNetV3-Large, exported to ONNX, run in the browser with onnxruntime WebAssembly. Progressive web app, service worker, IndexedDB. No server in the core path: the model, the app and the data stay on the phone."

## 3:30 – 4:00 · What localizing AI means to us
"Localizing AI is not translating a chatbot. It is building around the phone Noor owns, the connection she does not have, the language she speaks, the data that is true for her, the institution she can reach, and the one decision in front of her. Today our honest gaps are field data from Africa, validated Ewe, and an agronomist reviewing the advice. The next step is photographing real leaves on real farms with extension officers, recalibrating the gate and thresholds on them, and keeping a person in the loop."

## Checklist before you record
* App installed from the HTTPS URL, opened once online (so it is cached), then airplane mode.
* Have: a clean leaf-on-sheet photo, a blurry one, a busy-background one, a non-coffee object.
* Notification/Do-Not-Disturb on. 1080p portrait screen recording, voice-over recorded separately if the room is noisy.
