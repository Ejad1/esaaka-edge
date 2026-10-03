"""SYNTHETIC ROBUSTNESS TEST perturbations.

Deterministic (seeded per image id + perturbation name) so every model, on every machine
(Modal GPU, local CPU, browser parity test) sees byte-identical perturbed inputs.
Operates on the 512x256 prepared images. This is NOT field validation.
"""
import hashlib, io
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

NAMES = ["blur_mild", "blur_strong", "bright_dark", "bright_light", "contrast_low", "contrast_high",
         "jpeg_q12", "rotate15", "bg_clutter", "combined"]
EXTRA_NAMES = ["bg_uniform"]   # exploratory diagnostic, not part of the pre-registered perturbation list


def _rng(key, name):
    return np.random.default_rng(int(hashlib.sha256(f"{key}:{name}".encode()).hexdigest()[:8], 16))


def leaf_mask(img):
    """Leaf vs plain-background mask via saturation, hole-filled from the border. Returns bool array."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / (mx + 1e-6)
    m = Image.fromarray(((sat > 0.22) * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(5))
    m = m.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))
    # everything not reachable from the border through non-leaf pixels is leaf (fills lesions/holes)
    flood = m.copy()
    w, h = flood.size
    for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if flood.getpixel(corner) == 0:
            ImageDraw.floodfill(flood, corner, 128)
    return np.asarray(flood) != 128


def _noise(rng, size, scale):
    w, h = size
    small = rng.random((max(2, h // scale), max(2, w // scale), 3)).astype(np.float32)
    return np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255


def make_background(rng, size):
    kind = rng.choice(["soil", "foliage", "fabric"])
    w, h = size
    if kind == "soil":
        base = np.array([rng.uniform(0.25, 0.5), rng.uniform(0.17, 0.35), rng.uniform(0.08, 0.2)])
        tex = 0.55 * _noise(rng, size, 48) + 0.45 * _noise(rng, size, 6)
        bg = base[None, None, :] * (0.55 + 0.9 * tex)
    elif kind == "foliage":
        g = np.array([rng.uniform(0.1, 0.3), rng.uniform(0.25, 0.5), rng.uniform(0.05, 0.2)])
        tex = 0.6 * _noise(rng, size, 40) + 0.4 * _noise(rng, size, 10)
        bg = g[None, None, :] * (0.35 + 1.1 * tex)
    else:  # printed fabric / paper with stripes: high-contrast regular pattern
        yy, xx = np.mgrid[0:h, 0:w]
        period = rng.integers(14, 40)
        stripes = (((xx + yy) // period) % 2).astype(np.float32)[..., None]
        c1 = rng.random(3) * 0.8 + 0.1; c2 = rng.random(3) * 0.8 + 0.1
        bg = stripes * c1 + (1 - stripes) * c2
        bg = bg * (0.85 + 0.3 * _noise(rng, size, 20))
    return Image.fromarray((np.clip(bg, 0, 1) * 255).astype(np.uint8)), str(kind)


def composite(img, mask, rng):
    """Paste the leaf (mask) onto a random synthetic background. Same RNG consumption order as before."""
    bg, kind = make_background(rng, img.size)
    alpha = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))
    return Image.composite(img, bg, alpha), kind


def bg_clutter(img, key):
    rng = _rng(key, "bg")
    mask = leaf_mask(img)
    out, kind = composite(img, mask, rng)
    return out, {"mask_fraction": float(mask.mean()), "bg": kind}


def bg_uniform(img):
    """EXPLORATORY diagnostic: leaf on neutral mid-grey (separates clutter sensitivity from background shortcuts)."""
    mask = leaf_mask(img)
    alpha = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))
    return Image.composite(img, Image.new("RGB", img.size, (170, 170, 170)), alpha)


def random_augment(img, rng, mask=None):
    """Training-time robust augmentation (Phase 2). Levels are drawn at random, unlike the fixed test levels."""
    if rng.random() < 0.4: img = img.filter(ImageFilter.GaussianBlur(float(rng.uniform(0.5, 5.0))))
    if rng.random() < 0.4: img = ImageEnhance.Brightness(img).enhance(float(rng.uniform(0.45, 1.7)))
    if rng.random() < 0.4: img = ImageEnhance.Contrast(img).enhance(float(rng.uniform(0.45, 1.7)))
    if mask is not None and rng.random() < 0.5: img = composite(img, mask, rng)[0]
    if rng.random() < 0.3: img = _jpeg(img, int(rng.integers(10, 60)))
    return img


def _jpeg(img, q):
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=q); buf.seek(0)
    return Image.open(buf).convert("RGB")


def _rotate(img, key):
    rng = _rng(key, "rot")
    deg = 15 * (1 if rng.random() < 0.5 else -1)
    fill = tuple(int(v) for v in np.median(np.asarray(img)[:10, :10].reshape(-1, 3), axis=0))
    return img.rotate(deg, resample=Image.BICUBIC, fillcolor=fill)


def apply(name, img, key):
    """img: PIL RGB 512x256. key: stable id string. Returns PIL RGB."""
    if name == "clean": return img
    if name == "blur_mild": return img.filter(ImageFilter.GaussianBlur(2.0))
    if name == "blur_strong": return img.filter(ImageFilter.GaussianBlur(6.0))
    if name == "bright_dark": return ImageEnhance.Brightness(img).enhance(0.45)
    if name == "bright_light": return ImageEnhance.Brightness(img).enhance(1.7)
    if name == "contrast_low": return ImageEnhance.Contrast(img).enhance(0.45)
    if name == "contrast_high": return ImageEnhance.Contrast(img).enhance(1.7)
    if name == "jpeg_q12": return _jpeg(img, 12)
    if name == "rotate15": return _rotate(img, key)
    if name == "bg_clutter": return bg_clutter(img, key)[0]
    if name == "bg_uniform": return bg_uniform(img)
    if name == "combined":
        x = img.filter(ImageFilter.GaussianBlur(2.0))
        x = ImageEnhance.Brightness(x).enhance(0.7)
        x = bg_clutter(x, key)[0]
        return _jpeg(x, 25)
    raise ValueError(name)
