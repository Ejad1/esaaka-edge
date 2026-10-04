"""DRAFT Ewe interface strings by machine translation (authoring time only; the shipped app calls nothing external).

Sources: Google Translate (unofficial public endpoint) FR->EE as the main draft, EN->EE as an independent cross-check,
EE->FR as a meaning check. Output: src/i18n/ee.json (drafts) and EWE_REVIEW.md (table for a native speaker to correct).
THESE ARE NOT VALIDATED TRANSLATIONS. Agreement between FR->EE and EN->EE is a hint, not proof of correctness.
"""
import difflib, json, os, re, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
I18N = os.path.join(HERE, "..", "src", "i18n")
fr = json.load(open(os.path.join(I18N, "fr.json"), encoding="utf-8"))
en = json.load(open(os.path.join(I18N, "en.json"), encoding="utf-8"))
SAMPLE = {"ms": "987654", "n": "765432", "date": "12/12/2012", "label": "LABELX", "name": "NAMEX", "size": "1234.5"}


def gt(text, sl, tl):
    u = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode({"client": "gtx", "sl": sl, "tl": tl, "dt": "t", "q": text})
    for _ in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25)
            return "".join(seg[0] for seg in json.loads(r.read().decode("utf-8"))[0])
        except Exception:
            time.sleep(1.5)
    return None


def fill(s): return re.sub(r"\{(\w+)\}", lambda m: SAMPLE.get(m.group(1), m.group(0)), s)


def unfill(s, src):
    for k in re.findall(r"\{(\w+)\}", src):
        if SAMPLE.get(k) and SAMPLE[k] in s: s = s.replace(SAMPLE[k], "{" + k + "}")
    return s


rows, ee, review = {}, {}, []
for k in fr:
    f, e = fr[k], en[k]
    d_fr = gt(fill(f), "fr", "ee"); time.sleep(0.25)
    d_en = gt(fill(e), "en", "ee"); time.sleep(0.25)
    if not d_fr: continue
    d_fr, d_en = unfill(d_fr, f), unfill(d_en or "", f)
    ph_ok = set(re.findall(r"\{(\w+)\}", f)) == set(re.findall(r"\{(\w+)\}", d_fr))
    back = gt(fill(d_fr), "ee", "fr") or ""; time.sleep(0.25)
    agree = difflib.SequenceMatcher(None, d_fr.lower(), d_en.lower()).ratio() if d_en else 0.0
    review.append((k, f, d_fr, d_en, agree, back, ph_ok))
    if ph_ok: ee[k] = d_fr
    print(f"{k:28s} agree={agree:.2f} ph_ok={ph_ok}", flush=True)

# banner: states plainly that this is unvalidated machine translation
ban = gt("Traduction automatique, pas encore validée par un locuteur natif. Le français fait foi.", "fr", "ee")
ee["ee_banner"] = (ban or "") + " (Traduction automatique non validée / unvalidated machine translation — le français fait foi.)"
json.dump({k: ee.get(k, "") for k in fr}, open(os.path.join(I18N, "ee.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

lines = ["# Ewe review sheet (MACHINE-TRANSLATED DRAFT, NOT VALIDATED)", "",
         "Main draft: Google Translate FR->EE. `Alt` = independent EN->EE. `Back` = EE->FR to check the meaning. "
         "`Agree` is string similarity between the two Ewe versions (low = suspicious). Correct `src/i18n/ee.json` where wrong.", "",
         "| key | French | Ewe draft (shipped) | Ewe alt (EN->EE) | agree | back to French | placeholders ok |", "|---|---|---|---|---|---|---|"]
for k, f, d, a, g, b, ok in review:
    lines.append(f"| `{k}` | {f} | {d} | {a} | {g:.2f} | {b} | {'yes' if ok else 'NO (left empty)'} |")
open(os.path.join(HERE, "..", "EWE_REVIEW.md"), "w", encoding="utf-8").write("\n".join(lines))
agr = [r[4] for r in review]
print(f"\nfilled {sum(1 for v in ee.values() if v)} of {len(fr)} keys | mean agreement {sum(agr) / len(agr):.2f} | low agreement (<0.5): {sum(1 for x in agr if x < 0.5)}")
