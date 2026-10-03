# Coffee-leaf dataset catalogue (verdicts are decisions, with the reason)

Fields requested by the brief. "Verified" = read from the dataset's own metadata or inspected by us; "not verified" says so.

| | BRACOL | Uganda coffee leaf (Soroti Univ.) | RoCoLe | JMuBEN / JMuBEN2 |
|---|---|---|---|---|
| **Source / DOI** | Mendeley Data, `10.17632/yy2k5y8mxg.1` (Krohling, Esgario, Ventura; UFES; 2019) | Mendeley Data, `10.17632/k36wnd6knb.1` (Chelangat et al.; Soroti University; 2025) | Mendeley Data, `10.17632/c5yvn32dzg.2` (Parraga-Alava et al.; ESPAM Manabi / U. Santiago de Chile; 2019). A Zenodo mirror (`10.5281/zenodo.17461379`) carries inconsistent metadata (titled "BRACOL"), so we used Mendeley | Mendeley Data `tgv3zb82nd` (healthy, miner) and `t2r6rszp5c` (cercospora, rust, phoma) (Kenya) |
| **License** | CC BY 4.0 (verified) | CC BY 4.0 (verified) | CC BY 4.0 (verified) | CC BY 4.0 (verified, JMuBEN2) |
| **Geography** | Brazil | Uganda (farms) | Institutions in Ecuador/Chile; country of collection not stated in the metadata we read (not verified) | Kenya (Mutira plantation, Kirinyaga; from the paper's abstract as retrieved) |
| **Crop** | Arabica | coffee (species not stated) | **Robusta** | Arabica |
| **Classes** | healthy, leaf miner, rust, brown leaf spot (phoma), cercospora; code 5 = several stresses (decoded by us from the flag columns) | healthy, coffee leaf rust, phoma | healthy, red spider mite, rust levels 1-4 | phoma, cercospora, rust, healthy, miner |
| **Images** | 1,747 labels; **1,401 images recoverable** (published zip truncated, see DATA_CARD) | listing 3,322 files, **102 are empty at source** (100 healthy, 2 rust) -> 3,220 usable (description says 3,312) | 1,560 photos: healthy 791, rust L1 344 / L2 166 / L3 62 / L4 30, mite 167 | 58,555 (paper). We inspected only the rust archive (8,336 files, 69 MB) |
| **Acquisition** | Smartphone photos of **detached leaves on a plain sheet**, 2048x1024 (inspected) | Field farm photos, leaf close-ups, natural backgrounds, 256x256 JPEG (inspected) | Smartphone (5 MP) **field photos** (from the paper's abstract as retrieved) | Field, digital camera (paper). Rust archive: **128x128 blurry patches** (inspected) |
| **Class balance** | rust 465 / phoma 346 / miner 253 / healthy 142 / cercospora 136 / multi 59 (recovered) | healthy 1,079 / rust 1,031 / phoma 1,110 (usable) | healthy-heavy (791 of 1,560) | not assessed |
| **Original or augmented** | original | **augmented** (rotation, flips, brightness: stated by authors, seen in our montage; ~65% unique canonical hashes in a 1,800-image sample) | original | **mostly augmented**: only 106 of 8,336 rust files have camera-style names (inference, not stated) |
| **Overlap risk** | none found between our splits (perceptual hash, 0/202) | high: augmented copies of one leaf can be in the same evaluation set; also visible label noise | low | very high (duplicates/augmentations across classes and splits) |
| **Verdict** | **USE FOR TRAINING** and in-domain test | **USE FOR EXTERNAL TEST** (caveated) | **USE FOR EXTERNAL TEST** | **DO NOT USE** |
| **Why** | Only dataset with clean labels, original images and enough size for a small model; its plain-background capture is the main limit | Real African field photos on 3 of our classes; but augmented + noisy labels + close-ups, so unsuitable for training and only meaningful as a stress test | Real field photos, original images; different species (Robusta) and classes (no miner/phoma/cercospora), so it measures healthy-vs-rust and out-of-scope behaviour (mite) | 128 px patches, mostly augmented: invalid for training (leakage) and for whole-leaf external testing. Could be revisited after de-duplication; not inspected beyond one archive |

## Candidates found but not assessed

* A Rwandan Arabica coffee dataset (37,939 images; rust, miner, red spider mite) is mentioned in a published study; we did not locate an openly downloadable copy in the time available.
* PlantVillage / PlantDoc: not coffee; not used.

## Three-level strategy actually used

1. **Training**: BRACOL, stratified 70/15/15 split (seed 42; seeds 1 and 2 only to estimate variance).
2. **In-domain test**: held-out BRACOL images (never used for fitting or model selection).
3. **Out-of-domain / robustness**: (a) SYNTHETIC ROBUSTNESS TEST on held-out BRACOL (blur, exposure, contrast, JPEG, rotation, synthetic background); (b) external field photos: Uganda (3 shared classes) and RoCoLe (healthy vs rust, plus red spider mite as an out-of-scope disease). Thresholds are never tuned on (b).
