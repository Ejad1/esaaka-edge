"""Write the SYNTHETIC ROBUSTNESS TEST images (seed-42 test split) to disk so the in-browser harness can run the
shipped pipeline on byte-identical inputs. JPEG q98 (the jpeg_q12 artefacts are already baked into the pixels)."""
import os, sys, csv
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import perturb
BASE = os.path.join("D:" + os.sep, "Esaaka", "hack_nation", "data")
PREP = os.path.join(BASE, "prepared"); OUT = os.path.join(BASE, "guard_eval")
rows = [r for r in csv.DictReader(open(os.path.join(PREP, "splits_seed42.csv"))) if r["split"] == "test"]
for name in perturb.NAMES + perturb.EXTRA_NAMES:
    os.makedirs(os.path.join(OUT, name), exist_ok=True)
    for r in rows:
        im = Image.open(os.path.join(PREP, "images", r["id"] + ".jpg")).convert("RGB")
        perturb.apply(name, im, r["id"]).save(os.path.join(OUT, name, r["id"] + ".jpg"), quality=98)
    print(name, "done", flush=True)
