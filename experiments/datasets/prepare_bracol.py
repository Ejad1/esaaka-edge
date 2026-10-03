"""Prepare BRACOL (recovered subset) for the vision benchmark.

- resizes every leaf image to 512x256 (W x H), the dataset is 2:1
- writes stratified 70/15/15 splits for several seeds (class 5 = holdout_multi)
- checks near-duplicate leakage across splits with a perceptual (difference) hash
"""
import csv, json, os, sys, collections
import numpy as np
from PIL import Image

RAW = os.environ.get("BRACOL_RAW", r"D:\Esaaka\hack_nation\data\bracol\coffee-datasets\coffee-datasets\leaf")
OUT = os.environ.get("BRACOL_OUT", r"D:\Esaaka\hack_nation\data\prepared")
SEEDS = [42, 1, 2]
LABELS = {0: "healthy", 1: "miner", 2: "rust", 3: "phoma", 4: "cercospora"}
W, H = 512, 256


def dhash(img, size=16):
    g = img.convert("L").resize((size + 1, size), Image.LANCZOS)
    a = np.asarray(g, dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).flatten()


def main():
    os.makedirs(os.path.join(OUT, "images"), exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(RAW, "dataset.csv"), encoding="utf-8-sig")))
    present = {os.path.splitext(f)[0] for f in os.listdir(os.path.join(RAW, "images"))}
    rows = [r for r in rows if r["id"] in present]
    sizes, hashes = collections.Counter(), {}
    for r in rows:
        im = Image.open(os.path.join(RAW, "images", r["id"] + ".jpg")).convert("RGB")
        sizes[im.size] += 1
        hashes[r["id"]] = dhash(im)
        im.resize((W, H), Image.LANCZOS).save(os.path.join(OUT, "images", r["id"] + ".jpg"), quality=95)
    print("original sizes:", sizes.most_common(5))

    ids_by_class = collections.defaultdict(list)
    holdout = []
    for r in rows:
        c = int(r["predominant_stress"])
        (ids_by_class[c] if c in LABELS else holdout).append(r["id"])

    manifest = {"n_images": len(rows), "original_sizes": {str(k): v for k, v in sizes.items()},
                "classes": LABELS, "holdout_multi": len(holdout), "seeds": SEEDS, "splits": {}}
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        split_of = {}
        for c, ids in ids_by_class.items():
            ids = sorted(ids, key=int)
            rng.shuffle(ids)
            n = len(ids); n_tr = int(round(0.70 * n)); n_va = int(round(0.15 * n))
            for i, _id in enumerate(ids):
                split_of[_id] = "train" if i < n_tr else ("val" if i < n_tr + n_va else "test")
        with open(os.path.join(OUT, f"splits_seed{seed}.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["id", "label", "label_name", "split"])
            for r in rows:
                c = int(r["predominant_stress"])
                if c in LABELS: w.writerow([r["id"], c, LABELS[c], split_of[r["id"]]])
                else: w.writerow([r["id"], c, "multi", "holdout_multi"])
        counts = collections.Counter(split_of.values())
        per_class = {LABELS[c]: {s: sum(1 for i in ids if split_of[i] == s) for s in ("train", "val", "test")}
                     for c, ids in ids_by_class.items()}
        # near-duplicate leakage check (Hamming <= 8 / 256 bits) between test and train+val
        tr = [i for i, s in split_of.items() if s in ("train", "val")]
        te = [i for i, s in split_of.items() if s == "test"]
        A = np.stack([hashes[i] for i in tr]); near = 0; examples = []
        for t in te:
            d = (A != hashes[t]).sum(1)
            if d.min() <= 8:
                near += 1; examples.append((t, tr[int(d.argmin())], int(d.min())))
        manifest["splits"][str(seed)] = {"counts": dict(counts), "per_class": per_class,
                                         "test_near_duplicates_of_trainval": near, "examples": examples[:5]}
        print(f"seed {seed}: {dict(counts)} | test images with near-duplicate in train/val: {near}/{len(te)}")
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=2)
    print("per-class (seed 42):", manifest["splits"]["42"]["per_class"])


if __name__ == "__main__":
    main()
