"""Field-adaptation data (v2): BRACOL + Uganda + RoCoLe, grouped splits, 6th class 'other'.

Classes: 0 healthy, 1 miner, 2 rust, 3 phoma, 4 cercospora, 5 other (BRACOL multi-stress + RoCoLe red spider mite).
Leak control: Uganda has augmented copies -> images are clustered by a flip/rotation-invariant perceptual hash (Hamming <= 6)
and whole clusters go to one split; RoCoLe is grouped by plant (C#P#); BRACOL keeps its seed-42 split.
Field images are centre-cropped to 2:1 and resized to 512x256, exactly like the PWA does.
Uganda/RoCoLe are therefore NO LONGER independent external data for any model trained on this split.
"""
import csv, json, os, random, re, subprocess, sys, collections
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

BASE = os.path.join("D:" + os.sep, "Esaaka", "hack_nation", "data")
OUT = os.path.join(BASE, "prepared_v2"); IMG = os.path.join(OUT, "images"); TMP = os.path.join(BASE, "_tmp_rocole")
os.makedirs(IMG, exist_ok=True); os.makedirs(TMP, exist_ok=True)
NAMES = ["healthy", "miner", "rust", "phoma", "cercospora", "other"]


def crop_resize(img):
    img = img.convert("RGB"); w, h = img.size
    if w / h > 2: sw, sh = h * 2, h; l, t = (w - sw) // 2, 0
    else: sw, sh = w, w // 2; l, t = 0, (h - w // 2) // 2
    return img.crop((l, t, l + sw, t + sh)).resize((512, 256), Image.LANCZOS)


def split_groups(group_ids, weights, seed=42):
    """group_ids: list of (group, n_images). Greedy fill train/val/test by image counts."""
    rng = random.Random(seed); gs = list(group_ids); rng.shuffle(gs); total = sum(n for _, n in gs)
    tgt = {"train": 0.70 * total, "val": 0.15 * total, "test": 0.15 * total}; got = {k: 0 for k in tgt}; out = {}
    for g, n in gs:
        s = max(tgt, key=lambda k: (tgt[k] - got[k]) / tgt[k]); out[g] = s; got[s] += n
    return out


rows = []
# ---- BRACOL (already 512x256 in prepared/images)
sp = pd.read_csv(os.path.join(BASE, "prepared", "splits_seed42.csv"))
for _, r in sp.iterrows():
    if r.split == "holdout_multi": continue
    rows.append({"id": str(r.id), "source": "bracol", "label": int(r.label), "split": r.split, "group": f"b{r.id}"})
multi = [str(i) for i in sp[sp.split == "holdout_multi"].id]
random.Random(42).shuffle(multi)
for k, i in enumerate(multi):
    rows.append({"id": i, "source": "bracol", "label": 5, "split": "train" if k < 41 else ("val" if k < 50 else "test"), "group": f"b{i}"})

# ---- Uganda (all readable files), grouped by canonical perceptual hash
ug = []
for c, lab in (("healthy", 0), ("rust", 2), ("phoma", 3)):
    d = os.path.join(BASE, "external", "uganda", c)
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if os.path.getsize(p) > 0: ug.append((c, f, lab, p))
def canon_hash(p):
    g = np.asarray(Image.open(p).convert("L").resize((9, 9), Image.LANCZOS), np.float32); best = None
    for k in range(4):
        for fl in (False, True):
            x = np.rot90(g, k); x = np.fliplr(x) if fl else x
            bits = (x[:8, 1:] > x[:8, :-1]).flatten(); v = int("".join("1" if b else "0" for b in bits), 2)   # 8x8 = 64 bits
            best = v if best is None or v < best else best
    return best
hs = np.array([canon_hash(p) for _, _, _, p in ug], dtype=np.uint64)
parent = list(range(len(ug)))
def find(a):
    while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
    return a
for i0 in range(0, len(hs), 250):
    x = hs[i0:i0 + 250, None] ^ hs[None, :]
    pc = np.unpackbits(x.view(np.uint8).reshape(x.shape + (8,)), axis=-1).sum(axis=(-1, -2)) if False else np.unpackbits(x.reshape(-1, 1).view(np.uint8), axis=1).sum(1).reshape(x.shape)
    for a, b in zip(*np.where(pc <= 6)):
        ra, rb = find(i0 + a), find(b)
        if ra != rb: parent[ra] = rb
gid = [find(i) for i in range(len(ug))]
cnt = collections.Counter(gid)
print(f"Uganda: {len(ug)} images -> {len(cnt)} perceptual groups (largest {max(cnt.values())})")
gsplit = split_groups([(g, n) for g, n in cnt.items()], None)
for (c, f, lab, p), g in zip(ug, gid):
    name = f"uganda_{c}_{f}"; crop_resize(Image.open(p)).save(os.path.join(IMG, name), quality=92)
    rows.append({"id": name, "source": "uganda", "label": lab, "split": gsplit[g], "group": f"u{g}"})

# ---- RoCoLe: download all, crop/resize, delete originals
meta = {f["filename"]: f for f in json.load(open(os.path.join(BASE, "catalog", "c5yvn32dzg.json"), encoding="utf-8"))["files"]}
cls = pd.read_excel(os.path.join(BASE, "external", "rocole", "RoCoLe-classes.xlsx"))
# download cap: whole plants (groups of 4 images), preferring plants already processed, until ~800 images
cls["grp"] = [re.match(r"(C\d+P\d+)", f).group(1) for f in cls["File"]]
done = {re.match(r"rocole_(C\d+P\d+)", f).group(1) for f in os.listdir(IMG) if f.startswith("rocole_")}
others = sorted(set(cls.grp) - done); random.Random(7).shuffle(others)
keep = set(done)
for g in others:
    if len(keep) * 4 >= 800: break
    keep.add(g)
cls = cls[cls.grp.isin(keep)]
print("RoCoLe plants kept:", len(keep), "images:", len(cls), flush=True)
def job(row):
    f, lab = row["File"], row["Multiclass.Label"]; dst = os.path.join(IMG, "rocole_" + f)
    if not os.path.exists(dst):
        tmp = os.path.join(TMP, f)
        subprocess.run(["curl", "-L", "-s", "-m", "180", "-o", tmp, meta[f]["content_details"]["download_url"]], capture_output=True)
        try: crop_resize(Image.open(tmp)).save(dst, quality=92)
        except Exception as e: return None
        finally:
            if os.path.exists(tmp): os.remove(tmp)
    return f, lab
if os.environ.get("FINALIZE_ONLY"):   # no more downloading: use RoCoLe images already processed or already on disk
    cls_all = pd.read_excel(os.path.join(BASE, "external", "rocole", "RoCoLe-classes.xlsx")); got = []
    for _, r in cls_all.iterrows():
        dst = os.path.join(IMG, "rocole_" + r["File"]); raw = os.path.join(BASE, "external", "rocole", "images", r["File"])
        if not os.path.exists(dst) and os.path.exists(raw) and os.path.getsize(raw) > 0:
            try: crop_resize(Image.open(raw)).save(dst, quality=92)
            except Exception: continue
        if os.path.exists(dst): got.append((r["File"], r["Multiclass.Label"]))
else:
    with ThreadPoolExecutor(24) as ex: got = [r for r in ex.map(job, [r for _, r in cls.iterrows()]) if r]
print("RoCoLe processed:", len(got), "of", len(cls))
grp = collections.Counter(re.match(r"(C\d+P\d+)", f).group(1) for f, _ in got)
rs = split_groups(list(grp.items()), None)
for f, lab in got:
    g = re.match(r"(C\d+P\d+)", f).group(1); y = 0 if lab == "healthy" else (5 if lab == "red_spider_mite" else 2)
    rows.append({"id": "rocole_" + f, "source": "rocole", "label": y, "split": rs[g], "group": "r" + g})

df = pd.DataFrame(rows); df["label_name"] = [NAMES[i] for i in df.label]
df.to_csv(os.path.join(OUT, "splits_v2.csv"), index=False)
print(df.groupby(["source", "split"]).size().unstack().to_string()); print(pd.crosstab([df.source, df.split], df.label_name).to_string())
