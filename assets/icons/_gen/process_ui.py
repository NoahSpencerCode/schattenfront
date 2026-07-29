#!/usr/bin/env python3
"""Process UI icon raws into dark/light 384x384 pairs."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(__file__).resolve().parent / "raw"
SIZE = 384
DARK_INK = np.array([32.0, 28.0, 24.0])
LIGHT_INK = np.array([245.0, 238.0, 220.0])

STRUCTURES = {
    "airfield",
    "army_post",
    "depot",
    "bunker",
    "bridge_map",
    "capital",
    "city",
    "harbor",
    "radar",
}


def sample_bg(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    corners = np.concatenate(
        [
            rgb[2:14, 2:14].reshape(-1, 3),
            rgb[2:14, w - 14 : w - 2].reshape(-1, 3),
            rgb[h - 14 : h - 2, 2:14].reshape(-1, 3),
            rgb[h - 14 : h - 2, w - 14 : w - 2].reshape(-1, 3),
        ],
        0,
    )
    return np.median(corners, 0).astype(np.float32)


def key(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    bg = sample_bg(rgb)
    dist = np.sqrt(((rgb - bg) ** 2).sum(-1))
    h, w = rgb.shape[:2]
    corner_d = np.concatenate(
        [
            dist[2:22, 2:22].ravel(),
            dist[2:22, w - 22 : w - 2].ravel(),
            dist[h - 22 : h - 2, 2:22].ravel(),
            dist[h - 22 : h - 2, w - 22 : w - 2].ravel(),
        ]
    )
    thr = max(35.0, float(np.percentile(corner_d, 95)) + 25)
    soft = thr * 0.45
    alpha = np.clip((dist - thr) / max(soft, 1) * 255, 0, 255)
    alpha = np.where(dist < thr, 0.0, alpha)
    out = rgb.copy()
    near = (dist < thr + soft * 2) & (alpha > 0)
    lum = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
    for c in range(3):
        out[..., c] = np.where(near, out[..., c] * 0.5 + lum * 0.5, out[..., c])
    return out, alpha


def remove_flat_plate(rgb: np.ndarray, alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    gy, gx = np.gradient(lum)
    grad = np.sqrt(gx * gx + gy * gy)
    opaque = alpha > 40
    if not opaque.any():
        return rgb, alpha
    plate = opaque & (grad < 5.0)
    # protect edges of detailed content
    detail = opaque & (grad >= 5.0)
    # dilate detail manually with max filter via pad rolls
    d = detail.copy()
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            d |= np.roll(np.roll(detail, dy, 0), dx, 1)
    plate = plate & ~d
    if plate.sum() > opaque.sum() * 0.22:
        alpha = alpha.copy()
        alpha[plate] = 0
    return rgb, alpha


def tight_crop(rgba: np.ndarray, fill: float) -> np.ndarray:
    a = rgba[..., 3]
    mask = a > 30
    if not mask.any():
        return np.zeros((SIZE, SIZE, 4), np.float32)
    ys, xs = np.where(mask)
    y0, y1 = int(np.percentile(ys, 0.3)), int(np.percentile(ys, 99.7)) + 1
    x0, x1 = int(np.percentile(xs, 0.3)), int(np.percentile(xs, 99.7)) + 1
    crop = rgba[y0:y1, x0:x1]
    h, w = crop.shape[:2]
    side = max(h, w)
    pad = np.zeros((side, side, 4), np.float32)
    pad[(side - h) // 2 : (side - h) // 2 + h, (side - w) // 2 : (side - w) // 2 + w] = crop
    new_side = max(1, int(SIZE * fill))
    im = Image.fromarray(np.clip(pad, 0, 255).astype(np.uint8)).resize(
        (new_side, new_side), Image.Resampling.LANCZOS
    )
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    off = (SIZE - new_side) // 2
    canvas.paste(im, (off, off), im)
    return np.array(canvas).astype(np.float32)


def to_dark(rgba: np.ndarray) -> np.ndarray:
    rgb, a = rgba[..., :3], rgba[..., 3]
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    mask = a > 12
    if not mask.any():
        return rgba
    sub = lum[mask]
    lo, hi = float(np.percentile(sub, 2)), float(np.percentile(sub, 98))
    if hi <= lo:
        hi = lo + 1
    t = np.clip((lum - lo) / (hi - lo), 0, 1)
    if sub.mean() > 140:
        # light-on-magenta glyph: invert to dark ink body
        ink = DARK_INK[None, None, :] * (0.25 + 0.75 * (1.0 - t))[..., None]
        ink = np.where(lum[..., None] > 200, DARK_INK * 0.55, ink)
        ink = np.where(lum[..., None] < 60, DARK_INK * 0.12, ink)
    else:
        ink = DARK_INK[None, None, :] * (0.20 + 0.90 * t)[..., None]
    return np.concatenate([np.clip(ink, 0, 255), a[..., None]], -1)


def to_light(dark: np.ndarray) -> np.ndarray:
    rgb, a = dark[..., :3], dark[..., 3]
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    mask = a > 12
    if not mask.any():
        return dark
    sub = lum[mask]
    lo, hi = float(np.percentile(sub, 2)), float(np.percentile(sub, 98))
    if hi <= lo:
        hi = lo + 1
    t = np.clip((lum - lo) / (hi - lo), 0, 1)
    cream = LIGHT_INK[None, None, :] * (0.78 + 0.22 * t)[..., None]
    cream = np.where(lum[..., None] < lo + 0.15 * (hi - lo), LIGHT_INK * 0.55, cream)
    return np.concatenate([np.clip(cream, 0, 255), a[..., None]], -1)


def clear(rgba: np.ndarray) -> np.ndarray:
    out = rgba.copy()
    a = out[..., 3]
    for c in range(3):
        out[..., c] = np.where(a < 12, 0, out[..., c])
    out[..., 3] = np.where(a < 12, 0, a)
    return out


def process_one(name: str) -> None:
    src = None
    for stem in (f"{name}_ui", name):
        for ext in (".jpg", ".png", ".jpeg", ".webp"):
            p = RAW / f"{stem}{ext}"
            if p.exists():
                src = p
                break
        if src:
            break
    if not src:
        print(f"missing {name}")
        return
    arr = np.array(Image.open(src).convert("RGBA"))
    out, alpha = key(arr[..., :3].astype(np.float32))
    out, alpha = remove_flat_plate(out, alpha)
    rgba = np.dstack([out, alpha])
    fill = 0.74 if name in STRUCTURES else 0.66
    rgba = tight_crop(rgba, fill)
    dark = clear(to_dark(rgba))
    light = clear(to_light(dark))
    Image.fromarray(np.clip(dark, 0, 255).astype(np.uint8)).save(ROOT / "ui" / f"{name}_dark.png")
    Image.fromarray(np.clip(light, 0, 255).astype(np.uint8)).save(ROOT / "ui" / f"{name}_light.png")
    print(f"ui -> {name} opaque={(dark[..., 3] > 20).sum()}")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        names = sorted({p.stem.replace("_ui", "") for p in RAW.glob("*_ui.*")})
        for n in names:
            process_one(n)
        return
    for name in sys.argv[1:]:
        process_one(name)


if __name__ == "__main__":
    main()
