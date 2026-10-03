"""EXPLORATORY benchmark: can MMS give useful Ewe speech under Small-AI constraints?  (CPU, local, not Modal)

    python mms_benchmark.py 300m      # MMS-300m fine-tuned on WAXAL Ewe: fp32, dynamic INT8, ONNX attempt, + MMS-TTS Ewe
    python mms_benchmark.py base1b    # official facebook/mms-1b-all + 'ewe' adapter
    python mms_benchmark.py romaric   # community Ewe adapter on mms-1b-all (patched in via HTTP range reads)

Evaluation set: 24 utterances sampled (seed 0) from the WAXAL Ewe ASR *test* shard 1 (human transcriptions,
spontaneous image-prompted speech, many speakers). Small and from ONE corpus: results are indicative only.
No Ewe text is invented here; every reference is a human transcription from the corpus.
"""
import os, sys, io, re, json, time, struct, unicodedata, random, gc, shutil
os.environ["HF_HOME"] = r"D:\Esaaka\hack_nation\data\hf_cache"
import numpy as np, pyarrow.parquet as pq, soundfile as sf, psutil, torch, jiwer, requests
from scipy.signal import resample_poly

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
OUT = os.path.join(ROOT, "results", "speech"); os.makedirs(OUT, exist_ok=True)
RESULTS = os.path.join(OUT, "mms_results.json")
SHARD = r"D:\Esaaka\hack_nation\data\speech\waxal_ewe_test1.parquet"
N_UTT = 24
torch.set_num_threads(6)
proc_ = psutil.Process()


def rss_mb(): return proc_.memory_info().rss / 1e6


def norm(t):
    t = unicodedata.normalize("NFC", t).replace("\xa0", " ").lower()
    t = re.sub(r"[^\w\s\u0300-\u036f]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def load_samples():
    df = pq.read_table(SHARD).to_pandas()
    idx = sorted(random.Random(0).sample(range(len(df)), N_UTT))
    out = []
    for i in idx:
        a, sr = sf.read(io.BytesIO(df["audio"].iloc[i]["bytes"]), dtype="float32")
        if a.ndim > 1: a = a.mean(1)
        a16 = resample_poly(a, 160, 441).astype(np.float32) if sr == 44100 else a
        out.append({"id": df["id"].iloc[i], "audio": a16, "dur": len(a16) / 16000, "ref": norm(df["transcription"].iloc[i]), "speaker": str(df["speaker_id"].iloc[i])})
    return out


def save_result(key, value):
    r = json.load(open(RESULTS, encoding="utf-8")) if os.path.exists(RESULTS) else {}
    r[key] = value; json.dump(r, open(RESULTS, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def transcribe_all(model, proc, samples, tag):
    model.eval(); hyp, times, peak = [], [], rss_mb()
    for k, s in enumerate(samples):
        x = proc(s["audio"], sampling_rate=16000, return_tensors="pt")
        t0 = time.time()
        with torch.inference_mode(): logits = model(**x).logits
        times.append(time.time() - t0); peak = max(peak, rss_mb())
        hyp.append(norm(proc.decode(torch.argmax(logits, -1)[0])))
        if k % 6 == 0: print(f"  [{tag}] {k}/{len(samples)}  rtf so far {sum(times) / sum(x['dur'] for x in samples[:k + 1]):.2f}", flush=True)
    refs = [s["ref"] for s in samples]
    wer, cer = jiwer.wer(refs, hyp), jiwer.cer(refs, hyp)
    dur = sum(s["dur"] for s in samples)
    return {"wer": wer, "cer": cer, "rtf_cpu6": sum(times) / dur, "median_latency_s": float(np.median(times)), "audio_s": dur,
            "peak_rss_MB": peak, "examples": [{"ref": r, "hyp": h} for r, h in list(zip(refs, hyp))[:3]]}


def params_of(m): return sum(p.numel() for p in m.parameters())


def purge(*repos):
    for r in repos:
        shutil.rmtree(os.path.join(os.environ["HF_HOME"], "hub", "models--" + r.replace("/", "--")), ignore_errors=True)


def stage_300m(samples):
    from transformers import AutoProcessor, Wav2Vec2ForCTC, VitsModel, AutoTokenizer
    repo = "waxal-benchmarking/mms-300m-waxal-ewe"
    base_mem = rss_mb()
    proc = AutoProcessor.from_pretrained(repo); model = Wav2Vec2ForCTC.from_pretrained(repo)
    res = {"repo": repo, "params": params_of(model), "fp32_MB": params_of(model) * 4 / 1e6, "rss_after_load_MB": rss_mb() - base_mem,
           "license": "cc-by-nc-4.0", "self_reported": "WER 31.3 / CER 9.6 on WAXAL test (model card, unverified)"}
    res["fp32"] = transcribe_all(model, proc, samples, "300m fp32")
    save_result("mms300m_waxal_ewe", res)
    # dynamic INT8 on Linear layers
    q = torch.ao.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
    buf = io.BytesIO(); torch.save(q.state_dict(), buf)
    res["dynamic_int8"] = transcribe_all(q, proc, samples, "300m dyn-int8"); res["dynamic_int8"]["state_dict_MB"] = buf.tell() / 1e6
    save_result("mms300m_waxal_ewe", res)
    # ONNX export feasibility
    try:
        t0 = time.time(); p = os.path.join(OUT, "_mms300m_probe.onnx")
        torch.onnx.export(model, torch.randn(1, 80000), p, opset_version=17, input_names=["audio"], output_names=["logits"], dynamic_axes={"audio": {1: "T"}, "logits": {1: "F"}})
        res["onnx_export"] = {"ok": True, "MB": os.path.getsize(p) / 1e6, "seconds": time.time() - t0}; os.remove(p)
    except Exception as e:
        res["onnx_export"] = {"ok": False, "error": str(e)[:400]}
    save_result("mms300m_waxal_ewe", res)
    del model, q; gc.collect()
    # MMS-TTS Ewe: speed/size + audio samples for a native speaker to judge (no automatic quality claim)
    tts_repo = "facebook/mms-tts-ewe"
    tok = AutoTokenizer.from_pretrained(tts_repo); tts = VitsModel.from_pretrained(tts_repo).eval()
    os.makedirs(os.path.join(OUT, "tts_samples"), exist_ok=True); rows = []
    for s in samples[:5]:
        text = s["ref"][:160]
        t0 = time.time()
        with torch.inference_mode(): wav = tts(**tok(text, return_tensors="pt")).waveform[0].numpy()
        dt = time.time() - t0; sr = tts.config.sampling_rate
        sf.write(os.path.join(OUT, "tts_samples", f"{s['id']}.wav"), wav, sr)
        rows.append({"id": s["id"], "text": text, "audio_s": len(wav) / sr, "synthesis_s": dt, "rtf": dt / (len(wav) / sr)})
    save_result("mms_tts_ewe", {"repo": tts_repo, "params": params_of(tts), "fp32_MB": params_of(tts) * 4 / 1e6, "license": "cc-by-nc-4.0",
                                "samples": rows, "note": "Texts are human WAXAL transcriptions (lower-cased, punctuation stripped). Quality NOT scored automatically: a native Ewe speaker must judge the wav files."})
    purge(repo, tts_repo)


def stage_base1b(samples):
    from transformers import AutoProcessor, Wav2Vec2ForCTC
    repo = "facebook/mms-1b-all"; base_mem = rss_mb()
    proc = AutoProcessor.from_pretrained(repo, target_lang="ewe")
    model = Wav2Vec2ForCTC.from_pretrained(repo, target_lang="ewe", ignore_mismatched_sizes=True)
    res = {"repo": repo + " (+ewe adapter)", "params": params_of(model), "fp32_MB": params_of(model) * 4 / 1e6, "rss_after_load_MB": rss_mb() - base_mem,
           "license": "cc-by-nc-4.0", "ewe_adapter_MB": 8.92}
    res["fp32"] = transcribe_all(model, proc, samples, "mms-1b-all ewe")
    save_result("mms1b_all_ewe", res)
    del model; gc.collect()


def st_header(url):
    n = struct.unpack("<Q", requests.get(url, headers={"Range": "bytes=0-7"}, timeout=60).content)[0]
    return n, requests.get(url, headers={"Range": f"bytes=8-{7 + n}"}, timeout=60).json()


def st_tensor(url, n, meta):
    s, e = meta["data_offsets"]
    raw = requests.get(url, headers={"Range": f"bytes={8 + n + s}-{8 + n + e - 1}"}, timeout=300).content
    dt = {"F32": np.float32, "F16": np.float16}[meta["dtype"]]
    return np.frombuffer(raw, dtype=dt).reshape(meta["shape"]).astype(np.float32)


def stage_romaric(samples):
    from transformers import AutoProcessor, AutoConfig, Wav2Vec2ForCTC
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    repo = "romaricnadjire/mms-ewe-asr-mixed"; url = f"https://huggingface.co/{repo}/resolve/main/model.safetensors"
    base_path = hf_hub_download("facebook/mms-1b-all", "model.safetensors")
    base = load_file(base_path)
    n, hdr = st_header(url); hdr.pop("__metadata__", None)
    patch_keys = [k for k in hdr if "adapter" in k or "lm_head" in k]
    patch = {k: torch.from_numpy(st_tensor(url, n, hdr[k])) for k in patch_keys}
    # verify the model-card claim "only adapter + CTC head are trained": sample untouched tensors and compare to the base
    rng = random.Random(0); others = [k for k in hdr if k not in patch_keys and k in base]; diffs = []
    for k in rng.sample(others, min(8, len(others))):
        diffs.append(float(np.abs(st_tensor(url, n, hdr[k]) - base[k].float().numpy()).max()))
    claim_holds = max(diffs) < 1e-6
    save_result("romaric_patch_check", {"patched_tensors": len(patch), "sampled_untouched": len(diffs), "max_abs_diff_untouched": max(diffs), "claim_only_adapter_trained_holds": claim_holds})
    if not claim_holds: print("WARNING: other weights differ from base; patching is not equivalent -> aborting stage"); return
    cfg = AutoConfig.from_pretrained(repo); proc = AutoProcessor.from_pretrained(repo)
    base_mem = rss_mb(); model = Wav2Vec2ForCTC(cfg)
    model.load_state_dict({k: v for k, v in base.items() if "lm_head" not in k and "adapter" not in k}, strict=False)
    del base; gc.collect()
    print("load patch:", model.load_state_dict(patch, strict=False))
    res = {"repo": repo + " (adapter+CTC head patched onto mms-1b-all)", "params": params_of(model), "fp32_MB": params_of(model) * 4 / 1e6,
           "license": "cc-by-nc-4.0", "self_reported": "WER 29.19 / CER 6.82 on its own validation (model card, unverified)",
           "adapter_patch_MB": sum(v.numel() for v in patch.values()) * 4 / 1e6, "rss_after_load_MB": rss_mb() - base_mem}
    res["fp32"] = transcribe_all(model, proc, samples, "romaric mixed")
    save_result("mms1b_romaric_mixed", res)


if __name__ == "__main__":
    stage = sys.argv[1]
    samples = load_samples()
    print(f"{len(samples)} utterances, {sum(s['dur'] for s in samples):.0f}s audio, {len(set(s['speaker'] for s in samples))} speakers")
    {"300m": stage_300m, "base1b": stage_base1b, "romaric": stage_romaric}[stage](samples)
    print("done", stage)
