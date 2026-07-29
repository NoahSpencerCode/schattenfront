#!/usr/bin/env python3
"""Process colored Imagine outputs to 384x384 RGBA transparent icons."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(__file__).resolve().parent / "raw"
SIZE = 384

def sample_bg(rgb):
    h, w = rgb.shape[:2]
    corners = np.concatenate([
        rgb[2:18, 2:18].reshape(-1, 3),
        rgb[2:18, w-18:w-2].reshape(-1, 3),
        rgb[h-18:h-2, 2:18].reshape(-1, 3),
        rgb[h-18:h-2, w-18:w-2].reshape(-1, 3),
    ], 0)
    return np.median(corners, 0).astype(np.float32)

def key_and_crop(src: Path, fill: float = 0.84) -> np.ndarray:
    arr = np.array(Image.open(src).convert("RGBA"))
    rgb = arr[..., :3].astype(np.float32)
    bg = sample_bg(rgb)
    dist = np.sqrt(((rgb - bg) ** 2).sum(-1))
    h, w = rgb.shape[:2]
    corner_d = np.concatenate([
        dist[2:24, 2:24].ravel(),
        dist[2:24, w-24:w-2].ravel(),
        dist[h-24:h-2, 2:24].ravel(),
        dist[h-24:h-2, w-24:w-2].ravel(),
    ])
    thr = max(28.0, float(np.percentile(corner_d, 95)) + 18.0)
    soft = thr * 0.45
    alpha = np.clip((dist - thr) / max(soft, 1.0) * 255.0, 0, 255)
    alpha = np.where(dist < thr, 0.0, alpha)
    # despill toward subject
    near = (dist < thr + soft * 2) & (alpha > 0)
    lum = 0.299*rgb[...,0] + 0.587*rgb[...,1] + 0.114*rgb[...,2]
    out = rgb.copy()
    for c in range(3):
        # pull fringe toward neutral of pixel lum
        out[..., c] = np.where(near, out[..., c]*0.65 + lum*0.35, out[..., c])
    rgba = np.dstack([out, alpha])
    mask = alpha > 28
    if not mask.any():
        return np.zeros((SIZE, SIZE, 4), np.float32)
    ys, xs = np.where(mask)
    y0, y1 = int(np.percentile(ys, 0.3)), int(np.percentile(ys, 99.7)) + 1
    x0, x1 = int(np.percentile(xs, 0.3)), int(np.percentile(xs, 99.7)) + 1
    crop = rgba[y0:y1, x0:x1]
    ch, cw = crop.shape[:2]
    side = max(ch, cw)
    pad = np.zeros((side, side, 4), np.float32)
    pad[(side-ch)//2:(side-ch)//2+ch, (side-cw)//2:(side-cw)//2+cw] = crop
    new_side = max(1, int(SIZE * fill))
    im = Image.fromarray(np.clip(pad, 0, 255).astype(np.uint8)).resize(
        (new_side, new_side), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    off = (SIZE - new_side) // 2
    canvas.paste(im, (off, off), im)
    outa = np.array(canvas).astype(np.float32)
    # hard clear
    a = outa[..., 3]
    for c in range(3):
        outa[..., c] = np.where(a < 12, 0, outa[..., c])
    outa[..., 3] = np.where(a < 12, 0, a)
    return outa

def process(src: Path, dest: Path, fill: float = 0.84):
    rgba = key_and_crop(src, fill=fill)
    Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8)).save(dest, "PNG")
    op = int((rgba[..., 3] > 20).sum())
    print(f"-> {dest.relative_to(ROOT)} opaque={op}")

def main():
    if len(sys.argv) < 3:
        print("Usage: process_color.py unit|ui <name> [name...]")
        print("       process_color.py unit_from <src.jpg> <dest_name>")
        sys.exit(1)
    mode = sys.argv[1]
    if mode == "unit_from":
        process(Path(sys.argv[2]), ROOT / "units" / f"{sys.argv[3]}.png", 0.86)
        return
    kind = mode  # unit or ui
    folder = ROOT / ("units" if kind == "unit" else "ui")
    fill = 0.86 if kind == "unit" else 0.78
    for name in sys.argv[2:]:
        src = None
        for stem in (f"{name}_{kind}", f"{name}_ui", name):
            for ext in (".jpg", ".png", ".jpeg", ".webp"):
                p = RAW / f"{stem}{ext}"
                if p.exists():
                    src = p
                    break
            if src:
                break
        if not src:
            print(f"missing {name}")
            continue
        process(src, folder / f"{name}.png", fill)

if __name__ == "__main__":
    main()
