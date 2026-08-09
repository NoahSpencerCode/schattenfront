#!/usr/bin/env python3
"""Halftrack-derived unit processor: MAGENTA chroma-key only.

Pixel recipe reverse-engineered from icons/units/halftrack.png:

  Canvas:     384×384 RGBA
  Alpha:      binary only {0, 255} — hard cut, no soft fringe
  Transparent: RGB must be (0,0,0) wherever A=0
  Subject:    max bbox side ≈ 0.86 of canvas, centered
  Ink:        ~35% of subject lum < 35  (pure black outlines)
  Fill:       ~50% olive-grey ~RGB(105, 112, 100)
  Edge:       alpha jumps 0 → 255 in one pixel; outer rim is black ink

WHY MAGENTA: black outlines and dark olive must never be keyed.
Generate / place art on solid hot magenta (#FF00FF / ~#F115EB), then key that.

Usage:
  python3 process_unit_magenta.py <src.jpg|png> <dest_name> [fill=0.86]
  python3 process_unit_magenta.py --verify-halftrack
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
UNITS = ROOT / "units"
SIZE = 384
DEFAULT_FILL = 0.86  # matches halftrack max-side fill


def magenta_key(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Key hot magenta/violet background. Never keys black ink."""
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    # distance to pure magenta (255, 0, 255)
    dist = np.sqrt((r - 255.0) ** 2 + (g - 0.0) ** 2 + (b - 255.0) ** 2)
    mag = (r + b) / 2.0 - g
    h, w = r.shape
    corners = np.concatenate(
        [
            rgb[2:20, 2:20].reshape(-1, 3),
            rgb[2:20, w - 20 : w - 2].reshape(-1, 3),
            rgb[h - 20 : h - 2, 2:20].reshape(-1, 3),
            rgb[h - 20 : h - 2, w - 20 : w - 2].reshape(-1, 3),
        ],
        0,
    )
    bg = np.median(corners, 0)
    d2 = np.sqrt(((rgb - bg) ** 2).sum(-1))

    is_mag = (
        ((r > 160) & (b > 120) & (g < 170) & (mag > 40))
        | ((dist < 115) & (g < 165))
        | (d2 < 35)
        | ((r > 190) & (b > 150) & (g < 200) & (mag > 22))
    )
    alpha = np.where(is_mag, 0.0, 255.0)
    # soft fringe only on magenta-ish edge (not on black ink)
    soft = (
        (~is_mag)
        & (dist < 155)
        & (g < 175)
        & (r > 135)
        & (b > 115)
        & (mag > 12)
    )
    alpha = np.where(soft, np.clip((dist - 80) / 60.0 * 255.0, 0, 255), alpha)

    out = rgb.copy()
    # despill magenta fringe into subject edge
    fringe = (alpha > 0) & (mag > 12) & (r > g)
    excess = np.maximum(0.0, mag)
    out[..., 0] = np.where(fringe, np.maximum(r - excess * 0.55, g), r)
    out[..., 2] = np.where(fringe, np.maximum(b - excess * 0.55, g), b)
    return out, alpha


def finalize(rgba: np.ndarray, fill: float = DEFAULT_FILL) -> np.ndarray:
    """Hard binary alpha, crop, pad square, scale to fill, center on 384."""
    a = rgba[..., 3]
    # harden: anything that is subject becomes fully opaque
    mask = a > 40
    # clean speckles
    mimg = Image.fromarray((mask.astype(np.uint8) * 255))
    mimg = mimg.filter(ImageFilter.MedianFilter(3))
    mask = np.array(mimg) > 127
    if not mask.any():
        return np.zeros((SIZE, SIZE, 4), np.uint8)

    out = rgba.copy()
    out[..., 3] = np.where(mask, 255.0, 0.0)
    for c in range(3):
        out[..., c] = np.where(mask, out[..., c], 0.0)

    ys, xs = np.where(mask)
    crop = out[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    ch, cw = crop.shape[:2]
    side = max(ch, cw)
    pad = np.zeros((side, side, 4), np.float32)
    pad[(side - ch) // 2 : (side - ch) // 2 + ch, (side - cw) // 2 : (side - cw) // 2 + cw] = crop

    target = max(1, int(round(SIZE * fill)))
    scaled = Image.fromarray(np.clip(pad, 0, 255).astype(np.uint8)).resize(
        (target, target), Image.Resampling.LANCZOS
    )
    s = np.array(scaled).astype(np.float32)
    # re-harden after resize (LANCZOS introduces soft alpha)
    sa = s[..., 3]
    solid = sa >= 100
    # keep dark ink even if partial alpha after resize
    lum = 0.299 * s[..., 0] + 0.587 * s[..., 1] + 0.114 * s[..., 2]
    solid = solid | ((sa >= 50) & (lum < 200) & ((s[..., 0] + s[..., 1] + s[..., 2]) > 0))
    s[..., 3] = np.where(solid, 255, 0)
    for c in range(3):
        s[..., c] = np.where(solid, s[..., c], 0)

    canvas = np.zeros((SIZE, SIZE, 4), np.uint8)
    off = (SIZE - target) // 2
    canvas[off : off + target, off : off + target] = np.clip(s, 0, 255).astype(np.uint8)
    return canvas


def process_file(src: Path, dest: Path, fill: float = DEFAULT_FILL) -> bool:
    rgb = np.array(Image.open(src).convert("RGB")).astype(np.float32)
    # sanity: corners should be magenta-ish
    h, w = rgb.shape[:2]
    corner = np.median(
        np.concatenate(
            [
                rgb[2:16, 2:16].reshape(-1, 3),
                rgb[2:16, w - 16 : w - 2].reshape(-1, 3),
            ],
            0,
        ),
        0,
    )
    mag = (corner[0] + corner[2]) / 2 - corner[1]
    if mag < 30 or corner[1] > 120:
        print(
            f"WARNING {src.name}: corners look like {corner.round(0)} "
            f"(expected hot magenta). Black bg will destroy black outlines."
        )

    out, alpha = magenta_key(rgb)
    rgba = np.dstack([out, alpha])
    canvas = finalize(rgba, fill=fill)
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(canvas).save(dest)
    op = int((canvas[..., 3] > 20).sum())
    soft = int(((canvas[..., 3] > 0) & (canvas[..., 3] < 255)).sum())
    print(f"-> {dest.name:28s} opaque={op:6d} soft={soft}")
    return op > 500


def verify_halftrack() -> None:
    p = UNITS / "halftrack.png"
    a = np.array(Image.open(p).convert("RGBA"))
    alpha = a[..., 3]
    rgb = a[..., :3]
    vis = alpha >= 255
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    print("halftrack verify:")
    print(f"  alpha unique: {np.unique(alpha).tolist()}")
    print(f"  opaque: {vis.sum()}")
    print(f"  ink% lum<35: {100 * ((vis) & (lum < 35)).sum() / max(vis.sum(), 1):.1f}")
    print(f"  fill mean RGB: {rgb[vis & (lum >= 70) & (lum < 130)].mean(0).round(1)}")
    ys, xs = np.where(vis)
    print(f"  maxfill: {max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1) / 384:.3f}")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "--verify-halftrack":
        verify_halftrack()
        return
    src = Path(sys.argv[1])
    name = sys.argv[2]
    fill = float(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_FILL
    process_file(src, UNITS / f"{name}.png", fill=fill)


if __name__ == "__main__":
    main()
