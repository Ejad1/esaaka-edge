"""DRAFT Ewe advice texts by machine translation (authoring time only). Adds an "ee" block to public/knowledge/advice.json
and writes EWE_ADVICE_REVIEW.md (FR, Ewe draft, EN->EE alt, back-translation) for a native speaker / agronomist.
NOT VALIDATED. The app always shows the French original under each Ewe sentence (French is authoritative)."""
import difflib, json, os, time, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.join(HERE, "..", "public", "knowledge", "advice.json")
A = json.load(open(P, encoding="utf-8"))
def gt(text, sl, tl):
    u = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode({"client": "gtx", "sl": sl, "tl": tl, "dt": "t", "q": text})
    for _ in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25)
            return "".join(s[0] for s in json.loads(r.read().decode("utf-8"))[0])
        except Exception: time.sleep(1.5)
    return ""
def tr(fr, en):
    d = gt(fr, "fr", "ee"); time.sleep(.25); a = gt(en, "en", "ee"); time.sleep(.25); b = gt(d, "ee", "fr"); time.sleep(.25)
    g = difflib.SequenceMatcher(None, d.lower(), a.lower()).ratio()
    rows.append((fr, d, a, b, g)); return d
rows, ee = [], {}
for k, v in A["fr"].items():
    if k == "escalate": ee[k] = tr(v, A["en"][k]); continue
    ee[k] = {"what": tr(v["what"], A["en"][k]["what"]), "do": [tr(x, y) for x, y in zip(v["do"], A["en"][k]["do"])]}
A["ee"] = ee; json.dump(A, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
L = ["# Ewe ADVICE review sheet (MACHINE-TRANSLATED DRAFT, NOT VALIDATED)", "", "Safety content: needs a native speaker AND an agronomist. Check especially negations (ne traitez pas / évitez) and disease names.", "",
     "| French | Ewe draft (shipped) | Ewe alt (EN->EE) | back to French | agree |", "|---|---|---|---|---|"]
L += [f"| {f} | {d} | {a} | {b} | {g:.2f} |" for f, d, a, b, g in rows]
open(os.path.join(HERE, "..", "EWE_ADVICE_REVIEW.md"), "w", encoding="utf-8").write("\n".join(L))
print(len(rows), "strings; mean agree", sum(r[4] for r in rows) / len(rows))
