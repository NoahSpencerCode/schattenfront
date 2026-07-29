#!/usr/bin/env python3
"""Post-process Imagine outputs into engine-ready Schattenfront icons.

Units: white fill + black detail on transparent 384x384 (nation-tint safe).
UI dark: near-black ink on transparent.
UI light: cream ink on transparent (derived from dark).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]  # assets/icons
RAW = Path(__file__).resolve().parent / "raw"
SIZE = 384

DARK_INK = np.array([28.0, 24.0, 20.0])
LIGHT_INK = np.array([242.0, 236.0, 220.0])


def sample_bg(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    corners = np.concatenate(
        [
            rgb[2:14, 2:14].reshape(-1, 3),
            rgb[2:14, w - 14 : w - 2].reshape(-1, 3),
            rgb[h - 14 : h - 2, 2:14].reshape(-1, 3),
            rgb[h - 14 : h - 2, w - 14 : w - 2].reshape(-1, 3),
        ],
        axis=0,
    )
    return np.median(corners, axis=0).astype(np.float32)


def key_background(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (despilled_rgb, alpha) with adaptive corner-sampled key."""
    bg = sample_bg(rgb)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=-1))
    h, w = rgb.shape[:2]
    corner_d = np.concatenate(
        [
            dist[2:22, 2:22].ravel(),
            dist[2:22, w - 22 : w - 2].ravel(),
            dist[h - 22 : h - 2, 2:22].ravel(),
            dist[h - 22 : h - 2, w - 22 : w - 2].ravel(),
        ]
    )
    thr = max(35.0, float(np.percentile(corner_d, 95)) + 25.0)
    soft = thr * 0.45
    alpha = np.clip((dist - thr) / max(soft, 1.0) * 255.0, 0, 255)
    alpha = np.where(dist < thr, 0.0, alpha)

    out = rgb.copy()
    near = (dist < thr + soft * 2) & (alpha > 0)
    lum = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
    for c in range(3):
        out[..., c] = np.where(near, out[..., c] * 0.55 + lum * 0.45, out[..., c])
    return out, alpha


def tight_crop_pad(rgba: np.ndarray, fill_ratio: float = 0.80) -> np.ndarray:
    a = rgba[..., 3]
    mask = a > 30
    if not mask.any():
        return np.zeros((SIZE, SIZE, 4), dtype=np.float32)
    ys, xs = np.where(mask)
    y0, y1 = int(np.percentile(ys, 0.5)), int(np.percentile(ys, 99.5)) + 1
    x0, x1 = int(np.percentile(xs, 0.5)), int(np.percentile(xs, 99.5)) + 1
    crop = rgba[y0:y1, x0:x1]
    h, w = crop.shape[:2]
    side = max(h, w)
    pad = np.zeros((side, side, 4), dtype=np.float32)
    pad[(side - h) // 2 : (side - h) // 2 + h, (side - w) // 2 : (side - w) // 2 + w] = crop
    new_side = max(1, int(SIZE * fill_ratio))
    im = Image.fromarray(np.clip(pad, 0, 255).astype(np.uint8)).resize(
        (new_side, new_side), Image.Resampling.LANCZOS
    )
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    off = (SIZE - new_side) // 2
    canvas.paste(im, (off, off), im)
    return np.array(canvas).astype(np.float32)


def clear_transparent(rgba: np.ndarray) -> np.ndarray:
    a = rgba[..., 3]
    out = rgba.copy()
    for c in range(3):
        out[..., c] = np.where(a < 12, 0, out[..., c])
    out[..., 3] = np.where(a < 12, 0, a)
    return out


def to_unit_grayscale(rgba: np.ndarray) -> np.ndarray:
    rgb, a = rgba[..., :3], rgba[..., 3]
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    lum = np.where(lum > 200, 252, lum)
    lum = np.where(lum < 40, lum * 0.35, lum)
    return np.dstack([lum, lum, lum, a])


def to_ui_dark(rgba: np.ndarray) -> np.ndarray:
    rgb, a = rgba[..., :3], rgba[..., 3]
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    mask = a > 12
    if not mask.any():
        return rgba
    mean_lum = float(lum[mask].mean())
    if mean_lum > 120:
        # light subject -> dark ink body
        body = np.clip(lum / 255.0, 0, 1)
        ink = DARK_INK[None, None, :] * (0.25 + 0.85 * body)[..., None]
        ink = np.where(lum[..., None] < 55, ink * 0.15, ink)
    else:
        t = np.clip(lum / max(mean_lum * 1.8, 1), 0, 1)
        ink = DARK_INK[None, None, :] * (0.30 + 0.80 * t)[..., None]
    return np.dstack([*np.moveaxis(np.clip(ink, 0, 255), -1, 0), a])


def to_ui_light_from_dark(rgba: np.ndarray) -> np.ndarray:
    rgb, a = rgba[..., :3], rgba[..., 3]
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    mask = a > 12
    if not mask.any():
        return rgba
    sub = lum[mask]
    lo, hi = float(np.percentile(sub, 5)), float(np.percentile(sub, 95))
    if hi <= lo:
        hi = lo + 1
    t = np.clip((lum - lo) / (hi - lo), 0, 1)
    cream = LIGHT_INK[None, None, :] * (0.82 + 0.18 * t)[..., None]
    cream = np.where(lum[..., None] < 35, LIGHT_INK * 0.50, cream)
    return np.dstack([*np.moveaxis(np.clip(cream, 0, 255), -1, 0), a])


def load_keyed(src: Path) -> np.ndarray:
    arr = np.array(Image.open(src).convert("RGBA"))
    rgb = arr[..., :3].astype(np.float32)
    out, alpha = key_background(rgb)
    return np.dstack([out, alpha])


def process_unit(src: Path, dest: Path) -> None:
    rgba = load_keyed(src)
    rgba = tight_crop_pad(rgba, fill_ratio=0.80)
    rgba = to_unit_grayscale(rgba)
    rgba = clear_transparent(rgba)
    Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8)).save(dest, "PNG")
    opaque = int((rgba[..., 3] > 20).sum())
    print(f"unit  -> {dest.name:30s} opaque={opaque}")


def process_ui(src: Path, dest_dark: Path, dest_light: Path) -> None:
    rgba = load_keyed(src)
    rgba = tight_crop_pad(rgba, fill_ratio=0.70)
    dark = clear_transparent(to_ui_dark(rgba))
    light = clear_transparent(to_ui_light_from_dark(dark))
    Image.fromarray(np.clip(dark, 0, 255).astype(np.uint8)).save(dest_dark, "PNG")
    Image.fromarray(np.clip(light, 0, 255).astype(np.uint8)).save(dest_light, "PNG")
    print(f"ui    -> {dest_dark.name} / {dest_light.name}")


def find_raw(name: str, ui: bool = False) -> Path | None:
    stems = [f"{name}_ui", name] if ui else [name]
    for stem in stems:
        for ext in (".jpg", ".png", ".jpeg", ".webp"):
            p = RAW / f"{stem}{ext}"
            if p.exists():
                return p
    return None


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: process_icons.py unit|ui|all_units|all_ui [names...]")
        sys.exit(1)
    mode = sys.argv[1]
    names = sys.argv[2:]

    if mode == "all_units":
        for src in sorted(RAW.glob("*")):
            if src.suffix.lower() not in {".jpg", ".png", ".jpeg", ".webp"}:
                continue
            if src.stem.endswith("_ui"):
                continue
            process_unit(src, ROOT / "units" / f"{src.stem}.png")
        return

    if mode == "all_ui":
        seen = set()
        for src in sorted(RAW.glob("*")):
            if src.suffix.lower() not in {".jpg", ".png", ".jpeg", ".webp"}:
                continue
            stem = src.stem
            name = stem[:-3] if stem.endswith("_ui") else stem
            if name in seen:
                continue
            if not stem.endswith("_ui"):
                # only process as UI if explicitly named or no unit intent
                continue
            seen.add(name)
            process_ui(src, ROOT / "ui" / f"{name}_dark.png", ROOT / "ui" / f"{name}_light.png")
        return

    if mode == "unit":
        for name in names:
            src = find_raw(name, ui=False)
            if not src:
                print(f"missing {name}")
                continue
            process_unit(src, ROOT / "units" / f"{name}.png")
        return

    if mode == "ui":
        for name in names:
            src = find_raw(name, ui=True)
            if not src:
                print(f"missing {name}")
                continue
            process_ui(src, ROOT / "ui" / f"{name}_dark.png", ROOT / "ui" / f"{name}_light.png")
        return

    print("unknown mode", mode)
    sys.exit(1)


if __name__ == "__main__":
    main()
