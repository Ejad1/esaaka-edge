# Data card — BRACOL (recovered subset)

## Source
BRACOL, *A Brazilian Arabica Coffee Leaf images dataset to identification and quantification of coffee diseases and pests*.
Krohling, Esgario, Ventura, Universidade Federal do Espirito Santo. Mendeley Data, DOI `10.17632/yy2k5y8mxg.1`, published 2019-11-06.
**Licence: CC BY 4.0** (verified on the dataset page). Attribution is required and given in the README.

## What it contains
* Leaf-level photos of Arabica coffee leaves affected by leaf miner, rust, brown leaf spot (phoma), cercospora, or healthy, with a severity score.
* All recovered images are **2048x1024 px** (1,401 of 1,401).
* Capture conditions (inspected, not from the paper): **a detached leaf laid on a plain white/grey sheet**, soft shadow, close to studio conditions.

## What we actually used (and the truncation)
* The archive published on Mendeley is **truncated at the source**: the zip has no central directory and the last entry is cut off. Its SHA-256 equals the hash Mendeley publishes, so the damage is not ours. We recovered every readable entry by parsing local headers (CRC-checked): **1,401 images of the 1,747 listed**; the 346 missing ids are scattered (7 to 999). All 1,747 labels are intact. The official train/val/test split could not be recovered.
* Label codes (`predominant_stress`) were decoded from the per-disease flag columns, not assumed: 0 healthy, 1 miner, 2 rust, 3 phoma, 4 cercospora, 5 several stresses with none predominant.
* Recovered counts: healthy 142, miner 253, rust 465, phoma 346, cercospora 136, multi-stress 59.
* **Class 5 (59 images) is excluded** from the 5-class classifier and used only as an abstention probe (exploratory).
* Splits: stratified 70/15/15 with fixed seeds (42 primary, 1 and 2 for variance): 939 train / 201 val / 202 test per seed. A perceptual-hash check found **0 near-duplicates** between test and train/val.
* Preprocessing: resize to 512x256, then 448x224 at train/eval time; ImageNet normalisation.

## What this data does NOT cover (scored, so stated plainly)
* **Field conditions**: no leaves on the plant, no natural backgrounds, no mixed lighting. The models are brittle off this protocol (see `results/external_eval.csv`).
* **Africa**: Brazilian Arabica varieties and climate. No African validation of accuracy.
* **Robusta** and other coffee species; **coffee berry disease**, coffee wilt, nutrient deficiency, pests other than leaf miner; other crops.
* **Other devices/cameras**: capture hardware is limited to what the authors used.
* **Severity** is not predicted by our model.

## Biases and risks
* Small test set (202 images; 21-22 per minority class): macro-F1 differs by up to ~0.08 between random splits, so single-split rankings are unreliable. We report mean and SD over 3 splits.
* Class imbalance (rust 3.4x cercospora); we use sqrt-inverse-frequency class weights and report per-class recall.
* Possible background/session shortcuts (classes may have been photographed on different days or lighting): not excluded; the `bg_uniform` diagnostic probes it (see EXPERIMENTS).
* Labels were produced by the dataset authors (with a pathologist per their paper); we did not re-annotate.

## Other data used only for evaluation
See `experiments/datasets/CATALOG.md` (Uganda, RoCoLe) — never used for training or for choosing thresholds.
