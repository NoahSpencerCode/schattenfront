#!/usr/bin/env python3
"""Process unit art with hot magenta / violet chroma-key (halftrack pipeline).

Why magenta: black ink outlines and dark olive fills must NOT be keyed.
A pure magenta (#FF00FF-ish) background is removed instead of black.

Usage:
  python3 process_magenta.py unit <src.jpg|png> <dest_name> [fill]
  python3 process_magenta.py halftrack          # from raw/halftrack.jpg

Default fill=0.90 (max subject side / 384).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from collections import deque

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(__file__).resolve().parent / "raw"
UNITS = ROOT / "units"
SIZE = 384
DEFAULT_FILL = 0.90


def to_magenta_bg(rgb: np.ndarray) -> np.ndarray:
    """If bg is black/dark (border-connected), paint hot magenta for safe keying."""
    h, w = rgb.shape[:2]
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    corners = np.concatenate(
        [
            rgb[0:16, 0:16].reshape(-1, 3),
            rgb[0:16, w - 16 : w].reshape(-1, 3),
            rgb[h - 16 : h, 0:16].reshape(-1, 3),
            rgb[h - 16 : h, w - 16 : w].reshape(-1, 3),
        ],
        0,
    )
    bg = np.median(corners, 0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(-1))
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mag = (r + b) / 2 - g
    already_mag = (r > 180) & (b > 150) & (g < 160) & (mag > 40)
    if already_mag.mean() > 0.15:
        return rgb

    is_bg = np.zeros((h, w), bool)
    q: deque[tuple[int, int]] = deque()
    thr = 40.0
    for x in range(w):
        for y in (0, h - 1):
            if dist[y, x] < thr or lum[y, x] < 22:
                is_bg[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if dist[y, x] < thr or lum[y, x] < 22:
                if not is_bg[y, x]:
                    is_bg[y, x] = True
                    q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not is_bg[ny, nx]:
                if dist[ny, nx] < thr or (lum[ny, nx] < 18 and dist[ny, nx] < thr + 30):
                    is_bg[ny, nx] = True
                    q.append((ny, nx))
    out = rgb.copy()
    out[is_bg] = np.array([255, 0, 255], dtype=np.float32)
    return out


def magenta_key(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Key hot magenta/violet; despill fringe. Never keys black ink."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dist = np.sqrt((r - 255) ** 2 + (g - 0) ** 2 + (b - 255) ** 2)
    mag = (r + b) / 2 - g
    h, w = rgb.shape[:2]
    bg = np.median(
        np.concatenate(
            [
                rgb[2:18, 2:18].reshape(-1, 3),
                rgb[2:18, w - 18 : w - 2].reshape(-1, 3),
                rgb[h - 18 : h - 2, 2:18].reshape(-1, 3),
                rgb[h - 18 : h - 2, w - 18 : w - 2].reshape(-1, 3),
            ],
            0,
        ),
        0,
    )
    d2 = np.sqrt(((rgb - bg) ** 2).sum(-1))
    is_mag = (
        ((r > 160) & (b > 130) & (g < 170) & (mag > 40))
        | ((dist < 110) & (g < 160))
        | (d2 < 32)
        | ((r > 200) & (b > 160) & (g < 200) & (mag > 25))
    )
    alpha = np.where(is_mag, 0.0, 255.0)
    soft = (~is_mag) & (dist < 150) & (g < 170) & (r > 140) & (b > 120) & (mag > 15)
    alpha = np.where(soft, np.clip((dist - 85) / 55 * 255, 0, 255), alpha)
    out = rgb.copy()
    fringe = (alpha > 0) & (mag > 12) & (r > g)
    excess = np.maximum(0, mag)
    out[..., 0] = np.where(fringe, np.maximum(r - excess * 0.6, g), r)
    out[..., 2] = np.where(fringe, np.maximum(b - excess * 0.6, g), b)
    return out, alpha


def process_rgb(rgb: np.ndarray, dest: Path, fill: float = DEFAULT_FILL) -> bool:
    rgb = to_magenta_bg(rgb.astype(np.float32))
    out, alpha = magenta_key(rgb)
    mask = alpha > 40
    mimg = Image.fromarray((mask.astype(np.uint8) * 255))
    mimg = mimg.filter(ImageFilter.MedianFilter(3))
    mimg = mimg.filter(ImageFilter.MaxFilter(3))
    mimg = mimg.filter(ImageFilter.MinFilter(3))
    mask = np.array(mimg) > 127
    if not mask.any():
        print("EMPTY", dest)
        return False
    alpha = np.where(mask, 255.0, 0.0)
    for c in range(3):
        out[..., c] = np.where(mask, out[..., c], 0)
    rgba = np.dstack([out, alpha])
    ys, xs = np.where(mask)
    crop = rgba[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    ch, cw = crop.shape[:2]
    target = int(round(SIZE * fill))
    scale = target / max(ch, cw)
    nw = max(1, int(round(cw * scale)))
    nh = max(1, int(round(ch * scale)))
    scaled = Image.fromarray(np.clip(crop, 0, 255).astype(np.uint8)).resize(
        (nw, nh), Image.Resampling.LANCZOS
    )
    s = np.array(scaled).astype(np.float32)
    sa = s[..., 3]
    solid = (sa >= 90) | ((sa >= 40) & ((s[..., 0] + s[..., 1] + s[..., 2]) > 3))
    s[..., 3] = np.where(solid, 255, 0)
    for c in range(3):
        s[..., c] = np.where(solid, s[..., c], 0)
    canvas = np.zeros((SIZE, SIZE, 4), np.uint8)
    ox, oy = (SIZE - nw) // 2, (SIZE - nh) // 2
    canvas[oy : oy + nh, ox : ox + nw] = np.clip(s, 0, 255).astype(np.uint8)
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(canvas).save(dest)
    print(f"-> {dest.relative_to(ROOT)} opaque={(canvas[..., 3] > 20).sum()}")
    return True


def process_file(src: Path, dest: Path, fill: float = DEFAULT_FILL) -> bool:
    rgb = np.array(Image.open(src).convert("RGB"))
    return process_rgb(rgb, dest, fill=fill)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "halftrack":
        process_file(RAW / "halftrack.jpg", UNITS / "halftrack.png")
        return
    if sys.argv[1] == "unit":
        src = Path(sys.argv[2])
        name = sys.argv[3]
        fill = float(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_FILL
        process_file(src, UNITS / f"{name}.png", fill=fill)
        return
    print("unknown command", sys.argv[1])
    sys.exit(1)


if __name__ == "__main__":
    main()
