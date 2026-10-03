"""Edge-architecture benchmark on Modal GPUs (same data, preprocessing, protocol for every model).

    modal run experiments/vision/train_modal.py --smoke      # 1 epoch sanity check
    modal run experiments/vision/train_modal.py              # 4 archs x 3 seeds in parallel

Per run it stores logits (clean val/test, synthetic-robustness test, multi-stress holdout) so every metric
can be recomputed locally. For the primary seed it also exports FP32 ONNX and two static-INT8 variants.
"""
import json, os, modal

APP = modal.App("esaaka-edge-vision")
vol = modal.Volume.from_name("esaaka-edge-data", create_if_missing=True)
HERE = os.path.dirname(os.path.abspath(__file__))
ROB = os.path.join(HERE, "..", "robustness")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch==2.5.1", "torchvision==0.20.1", "timm==1.0.11", "numpy==1.26.4", "pillow==10.4.0",
                 "scikit-learn==1.5.2", "onnx==1.17.0", "onnxruntime==1.20.1", "huggingface_hub==0.26.2")
    .add_local_dir(ROB, remote_path="/root/robustness")
)

ARCHS = ["mobilenetv3_small_100", "mobilenetv3_large_100", "efficientnet_b0", "efficientnet_lite0"]
SEEDS = [42, 1, 2]
PRIMARY = 42
LABELS = ["healthy", "miner", "rust", "phoma", "cercospora"]
MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)
H, W = 224, 448


@APP.function(image=image, gpu="T4", cpu=4, memory=16384, timeout=3600, volumes={"/data": vol})
def run_experiment(arch: str, seed: int, epochs: int = 30, export: bool = False, smoke: bool = False,
                   robust: bool = False, quantize: bool = True) -> dict:
    import sys, csv, copy, random, time, io
    sys.path.insert(0, "/root/robustness")
    import numpy as np, torch, timm, torchvision
    from torch import nn
    from torchvision import transforms as T
    from PIL import Image
    from sklearn.metrics import f1_score
    import perturb

    t_start = time.time()
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    P = "/data/prepared"
    rows = list(csv.DictReader(open(f"{P}/splits_seed{seed}.csv")))
    by = {s: [(r["id"], int(r["label"])) for r in rows if r["split"] == s] for s in ("train", "val", "test")}
    multi = [r["id"] for r in rows if r["split"] == "holdout_multi"]
    if smoke:
        by = {k: v[::max(1, len(v) // (96 if k == "train" else 40))][: (96 if k == "train" else 40)] for k, v in by.items()}
        multi = multi[:20]
    imgs = {i: np.asarray(Image.open(f"{P}/images/{i}.jpg").convert("RGB"))
            for i in [i for v in by.values() for i, _ in v] + multi}

    norm = T.Normalize(MEAN, STD)
    eval_tf = T.Compose([T.Resize((H, W)), T.ToTensor(), norm])
    train_tf = T.Compose([T.RandomResizedCrop((H, W), scale=(0.6, 1.0), ratio=(1.7, 2.3)), T.RandomHorizontalFlip(),
                          T.RandomVerticalFlip(), T.ColorJitter(0.2, 0.2, 0.2, 0.02), T.ToTensor(), norm])

    masks = {}
    if robust:   # leaf masks are computed once, so the random background composite stays cheap per sample
        masks = {i: perturb.leaf_mask(Image.fromarray(imgs[i])) for i, _ in by["train"]}

    class DS(torch.utils.data.Dataset):
        def __init__(self, items, tf, aug=False): self.items, self.tf, self.aug = items, tf, aug
        def __len__(self): return len(self.items)
        def __getitem__(self, k):
            i, y = self.items[k]; pil = Image.fromarray(imgs[i])
            if self.aug and robust:
                rng = np.random.default_rng((torch.initial_seed() + 7919 * k) % (2 ** 32))
                pil = perturb.random_augment(pil, rng, masks.get(i))
            return self.tf(pil), y

    dev = "cuda"
    tr_dl = torch.utils.data.DataLoader(DS(by["train"], train_tf, aug=True), batch_size=32, shuffle=True, num_workers=4, drop_last=True)

    model = timm.create_model(arch, pretrained=True, num_classes=5, drop_rate=0.2).to(dev)
    params = sum(p.numel() for p in model.parameters())
    counts = np.bincount([y for _, y in by["train"]], minlength=5).astype(np.float32)
    cw = torch.tensor((counts.sum() / (5 * np.maximum(counts, 1))) ** 0.5, device=dev)
    crit = nn.CrossEntropyLoss(weight=cw)
    opt = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=1e-2)
    steps = epochs * len(tr_dl)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=5e-4, total_steps=steps, pct_start=0.1)
    scaler = torch.amp.GradScaler("cuda")

    @torch.no_grad()
    def logits_of(tensors_iter):
        model.eval(); out = []
        batch = []
        for x in tensors_iter:
            batch.append(x)
            if len(batch) == 64:
                out.append(model(torch.stack(batch).to(dev)).float().cpu()); batch = []
        if batch:
            out.append(model(torch.stack(batch).to(dev)).float().cpu())
        return torch.cat(out).numpy()   # FP32 on purpose: matches the deployed (FP32/INT8) numerics

    def eval_pil(ids_labels, name="clean"):
        return logits_of(eval_tf(perturb.apply(name, Image.fromarray(imgs[i]), i)) for i, _ in ids_labels)

    best, best_f1, best_ep, bad = None, -1, -1, 0
    yv = np.array([y for _, y in by["val"]])
    for ep in range(epochs):
        model.train()
        for x, y in tr_dl:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16): loss = crit(model(x), y)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step()
        f1 = f1_score(yv, eval_pil(by["val"]).argmax(1), average="macro")
        if f1 > best_f1: best_f1, best_ep, best, bad = f1, ep, copy.deepcopy(model.state_dict()), 0
        else: bad += 1
        print(f"[{arch} s{seed}] ep{ep} loss {loss.item():.3f} val_macroF1 {f1:.3f} (best {best_f1:.3f}@{best_ep})", flush=True)
        if bad >= 10: break
    model.load_state_dict(best)
    train_time = time.time() - t_start

    ids_test = by["test"]; ytest = np.array([y for _, y in ids_test])
    arrays = {"val_logits": eval_pil(by["val"]), "val_y": yv, "test_logits": eval_pil(ids_test), "test_y": ytest,
              "test_ids": np.array([i for i, _ in ids_test]), "val_ids": np.array([i for i, _ in by["val"]]),
              "multi_logits": eval_pil([(i, -1) for i in multi]), "multi_ids": np.array(multi)}
    for name in perturb.NAMES + perturb.EXTRA_NAMES:
        arrays[f"pert_{name}"] = eval_pil(ids_test, name)
    if robust:   # validation-perturbed logits: lets the recipe decision be made on validation, not test
        for name in perturb.NAMES + perturb.EXTRA_NAMES:
            arrays[f"valpert_{name}"] = eval_pil(by["val"], name)
    tag = f"{arch}_s{seed}" + ("_rob" if robust else "")
    os.makedirs("/data/runs", exist_ok=True)
    np.savez_compressed(f"/data/runs/{tag}.npz", **arrays)
    summary = {"arch": arch, "seed": seed, "params": params, "best_epoch": best_ep, "epochs_run": ep + 1,
               "val_macro_f1": best_f1, "test_acc": float((arrays["test_logits"].argmax(1) == ytest).mean()),
               "test_macro_f1": float(f1_score(ytest, arrays["test_logits"].argmax(1), average="macro")),
               "train_time_s": round(train_time, 1), "gpu": torch.cuda.get_device_name(0),
               "torch": torch.__version__, "timm": timm.__version__, "smoke": smoke, "robust_aug": robust}

    if export:
        import onnxruntime as ort
        from onnxruntime.quantization import (quantize_static, CalibrationDataReader, QuantFormat, QuantType,
                                              CalibrationMethod)
        d = f"/data/runs/{tag}"; os.makedirs(d, exist_ok=True)
        model.eval().cpu().float()
        fp32 = f"{d}/model_fp32.onnx"
        torch.onnx.export(model, torch.randn(1, 3, H, W), fp32, opset_version=17, input_names=["input"],
                          output_names=["logits"], dynamic_axes={"input": {0: "N"}, "logits": {0: "N"}},
                          do_constant_folding=True)
        summary["onnx_fp32_bytes"] = os.path.getsize(fp32)

        def prep(pil): return eval_tf(pil).numpy().astype(np.float32)
        def ort_logits(path, pils):
            so = ort.SessionOptions(); so.intra_op_num_threads = 4
            s = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
            return np.stack([s.run(None, {"input": prep(p)[None]})[0][0] for p in pils])

        test_pils = [Image.fromarray(imgs[i]) for i, _ in ids_test]
        val_pils = [Image.fromarray(imgs[i]) for i, _ in by["val"]]
        lf = ort_logits(fp32, test_pils)
        with torch.no_grad():
            tl = model(torch.stack([eval_tf(p) for p in test_pils[:16]])).numpy()
        summary["onnx_vs_torch_max_abs_diff_cpu16"] = float(np.abs(lf[:16] - tl).max())
        summary["onnx_vs_torch_max_abs_diff_gpu_all"] = float(np.abs(lf - arrays["test_logits"]).max())
        summary["onnx_fp32_test_macro_f1"] = float(f1_score(ytest, lf.argmax(1), average="macro"))

        cal_ids = [i for i, _ in by["train"]]; random.Random(0).shuffle(cal_ids); cal_ids = cal_ids[:128]
        class Reader(CalibrationDataReader):
            def __init__(self): self.it = iter([{"input": prep(Image.fromarray(imgs[i]))[None]} for i in cal_ids])
            def get_next(self): return next(self.it, None)

        best_variant, best_val = None, -1
        for qtag, method in ([("minmax", CalibrationMethod.MinMax), ("percentile", CalibrationMethod.Percentile)] if quantize else []):
            tag_ = qtag
            q = f"{d}/model_int8_{tag_}.onnx"
            try:
                quantize_static(fp32, q, Reader(), quant_format=QuantFormat.QDQ, per_channel=True,
                                weight_type=QuantType.QInt8, activation_type=QuantType.QUInt8, calibrate_method=method)
            except Exception as e:
                summary[f"int8_{tag_}_error"] = str(e)[:300]; continue
            lv = ort_logits(q, val_pils)
            f1v = float(f1_score(yv, lv.argmax(1), average="macro"))
            summary[f"int8_{tag_}_bytes"] = os.path.getsize(q); summary[f"int8_{tag_}_val_macro_f1"] = f1v
            if f1v > best_val: best_val, best_variant = f1v, tag_
        if best_variant:
            q = f"{d}/model_int8_{best_variant}.onnx"
            ex = {"int8_variant": best_variant, "int8_val_logits": ort_logits(q, val_pils), "int8_test_logits": ort_logits(q, test_pils)}
            for name in perturb.NAMES:
                ex[f"int8_pert_{name}"] = ort_logits(q, [perturb.apply(name, p, i) for p, (i, _) in zip(test_pils, ids_test)])
            ex["int8_multi_logits"] = ort_logits(q, [Image.fromarray(imgs[i]) for i in multi])
            np.savez_compressed(f"{d}/int8_logits.npz", **ex)
            summary["int8_variant"] = best_variant
            summary["int8_test_macro_f1"] = float(f1_score(ytest, ex["int8_test_logits"].argmax(1), average="macro"))
            summary["int8_bytes"] = os.path.getsize(q)
        json.dump(summary, open(f"{d}/summary.json", "w"), indent=2)
    vol.commit()
    return summary


@APP.local_entrypoint()
def main(smoke: bool = False, phase2: bool = False):
    out_dir = os.path.join(HERE, "..", "..", "results")
    if smoke:
        r = run_experiment.remote("mobilenetv3_small_100", PRIMARY, epochs=1, export=True, smoke=True, robust=phase2, quantize=not phase2)
        print(json.dumps(r, indent=2)); return
    if phase2:
        jobs = [(a, s, 30, s == PRIMARY, False, True, False) for s in SEEDS for a in ARCHS]
    else:
        jobs = [(a, s, 30, s == PRIMARY, False) for s in SEEDS for a in ARCHS]
    res = []
    for r in run_experiment.starmap(jobs):
        print(json.dumps({k: r[k] for k in ("arch", "seed", "best_epoch", "test_acc", "test_macro_f1", "train_time_s")}))
        res.append(r)
    json.dump(res, open(os.path.join(out_dir, "vision_runs_summary_rob.json" if phase2 else "vision_runs_summary.json"), "w"), indent=2)
