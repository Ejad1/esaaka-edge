"""Download the external coffee evaluation sets (CC BY 4.0) from Mendeley's public API.

Uses curl (the Mendeley metadata endpoint rejects Python's default user agent).
- Uganda (k36wnd6knb): all 3,322 images, class inferred from folder size ordering (verified visually afterwards)
- RoCoLe (c5yvn32dzg): label csv + a seeded, class-balanced sample of photos
"""
import csv, json, os, subprocess, sys, collections, random, io
from concurrent.futures import ThreadPoolExecutor

BASE = r"D:\Esaaka\hack_nation\data"
CAT = os.path.join(BASE, "catalog")
OUT = os.path.join(BASE, "external")


def curl(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0: return True
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    r = subprocess.run(["curl", "-L", "-s", "-m", "300", "-o", dest, url], capture_output=True)
    return r.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0


def uganda():
    d = json.load(open(os.path.join(CAT, "k36wnd6knb.json"), encoding="utf-8"))
    by = collections.defaultdict(list)
    for f in d["files"]: by[f["folder_id"]].append(f)
    # folder sizes: ~1179 healthy, ~1033 coffee-leaf-rust, ~1110 phoma (description: 1179 / 1023 / 1110)
    order = sorted(by.items(), key=lambda kv: -len(kv[1]))
    names = {order[0][0]: "healthy", order[1][0]: "phoma", order[2][0]: "rust"}
    jobs = []
    for fid, L in by.items():
        for f in L:
            jobs.append((f["content_details"]["download_url"], os.path.join(OUT, "uganda", names[fid], f["filename"])))
    with ThreadPoolExecutor(16) as ex: ok = list(ex.map(lambda j: curl(*j), jobs))
    print("uganda: downloaded", sum(ok), "/", len(jobs), {names[k]: len(v) for k, v in by.items()})


def rocole(n_per_group=120, seed=0):
    d = json.load(open(os.path.join(CAT, "c5yvn32dzg.json"), encoding="utf-8"))
    meta = {f["filename"]: f for f in d["files"]}
    for name in ("RoCoLE-csv.csv", "RoCoLe-classes.xlsx"):
        f = meta[name]; curl(f["content_details"]["download_url"], os.path.join(OUT, "rocole", name))
    print("rocole labels downloaded; first lines:")
    print(open(os.path.join(OUT, "rocole", "RoCoLE-csv.csv"), encoding="utf-8", errors="replace").read(600))


def rocole_images(n_healthy=100, n_rust=100, n_mite=40, seed=0):
    """Seeded sample of RoCoLe photos: healthy / rust (proportional to severity levels) / red spider mite."""
    import pandas as pd
    d = json.load(open(os.path.join(CAT, "c5yvn32dzg.json"), encoding="utf-8"))
    meta = {f["filename"]: f for f in d["files"]}
    df = pd.read_excel(os.path.join(OUT, "rocole", "RoCoLe-classes.xlsx"))
    rng = random.Random(seed)
    pick = []
    healthy = df[df["Multiclass.Label"] == "healthy"]["File"].tolist(); rng.shuffle(healthy); pick += [(f, "healthy") for f in healthy[:n_healthy]]
    rust = df[df["Multiclass.Label"].str.startswith("rust")]
    frac = n_rust / len(rust)
    for lvl, g in rust.groupby("Multiclass.Label"):
        fs = g["File"].tolist(); rng.shuffle(fs); pick += [(f, lvl) for f in fs[:max(1, round(len(fs) * frac))]]
    mite = df[df["Multiclass.Label"] == "red_spider_mite"]["File"].tolist(); rng.shuffle(mite); pick += [(f, "red_spider_mite") for f in mite[:n_mite]]
    jobs = [(meta[f]["content_details"]["download_url"], os.path.join(OUT, "rocole", "images", f)) for f, _ in pick]
    with ThreadPoolExecutor(8) as ex: ok = list(ex.map(lambda j: curl(*j), jobs))
    with open(os.path.join(OUT, "rocole", "sample.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["file", "label"]); w.writerows(pick)
    print("rocole images:", sum(ok), "/", len(jobs), collections.Counter(l for _, l in pick))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "uganda"): uganda()
    if which in ("all", "rocole"): rocole()
    if which in ("all", "rocole_images"): rocole_images()
