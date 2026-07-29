#!/usr/bin/env python3
"""Process structure raws into dark/light UI, and thicken ALL unit + UI icons.

Units: white body + bold black strokes on transparent 384x384.
UI: dual ink (near-black / cream) with bold silhouettes that survive small display sizes.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(__file__).resolve().parent / "raw"
UNITS = ROOT / "units"
UI = ROOT / "ui"
SIZE = 384

DARK_INK = np.array([28.0, 24.0, 20.0])
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
CHROME_PREFIXES = ("panel_button", "panel_key", "red_button")


def sample_bg(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    corners = np.concatenate(
        [
            rgb[2:16, 2:16].reshape(-1, 3),
            rgb[2:16, w - 16 : w - 2].reshape(-1, 3),
            rgb[h - 16 : h - 2, 2:16].reshape(-1, 3),
            rgb[h - 16 : h - 2, w - 16 : w - 2].reshape(-1, 3),
        ],
        0,
    )
    return np.median(corners, 0).astype(np.float32)


def key_bg(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    bg = sample_bg(rgb)
    dist = np.sqrt(((rgb - bg) ** 2).sum(-1))
    h, w = rgb.shape[:2]
    corner_d = np.concatenate(
        [
            dist[2:24, 2:24].ravel(),
            dist[2:24, w - 24 : w - 2].ravel(),
            dist[h - 24 : h - 2, 2:24].ravel(),
            dist[h - 24 : h - 2, w - 24 : w - 2].ravel(),
        ]
    )
    thr = max(32.0, float(np.percentile(corner_d, 95)) + 22.0)
    soft = thr * 0.4
    alpha = np.clip((dist - thr) / max(soft, 1.0) * 255.0, 0, 255)
    alpha = np.where(dist < thr, 0.0, alpha)
    out = rgb.copy()
    near = (dist < thr + soft * 2) & (alpha > 0)
    lum = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
    for c in range(3):
        out[..., c] = np.where(near, out[..., c] * 0.45 + lum * 0.55, out[..., c])
    return out, alpha


def tight_crop(rgba: np.ndarray, fill: float) -> np.ndarray:
    a = rgba[..., 3]
    mask = a > 28
    if not mask.any():
        return np.zeros((SIZE, SIZE, 4), np.float32)
    ys, xs = np.where(mask)
    y0, y1 = int(np.percentile(ys, 0.4)), int(np.percentile(ys, 99.6)) + 1
    x0, x1 = int(np.percentile(xs, 0.4)), int(np.percentile(xs, 99.6)) + 1
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


def clear(rgba: np.ndarray) -> np.ndarray:
    out = rgba.copy()
    a = out[..., 3]
    for c in range(3):
        out[..., c] = np.where(a < 10, 0, out[..., c])
    out[..., 3] = np.where(a < 10, 0, a)
    return out


def dilate_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    """Binary dilate with max-filter. radius 1 -> 3x3, 2 -> 5x5, etc."""
    if radius <= 0:
        return mask
    size = radius * 2 + 1
    img = Image.fromarray((mask.astype(np.uint8) * 255))
    img = img.filter(ImageFilter.MaxFilter(size))
    return np.array(img) > 127


def thicken_unit_rgba(rgba: np.ndarray, line_radius: int = 2) -> np.ndarray:
    """Bold black strokes over white body for nation-tintable unit sprites."""
    rgb, a = rgba[..., :3], rgba[..., 3]
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    opaque = a > 20
    if not opaque.any():
        return rgba

    # Lines: dark pixels; body: light pixels
    lines = opaque & (lum < 95)
    body = opaque & (lum >= 95)

    # Grow body slightly so lines sit on fill; grow lines more for bold stroke
    body_d = dilate_mask(body, 1)
    lines_d = dilate_mask(lines, line_radius)

    # Alpha = thickened silhouette
    sil = dilate_mask(opaque, max(1, line_radius - 1))
    # Prefer body+lines for solid fill
    fill = body_d | lines_d | sil

    out_lum = np.full(lum.shape, 252.0, dtype=np.float32)
    # Soft midtones from original body where present
    out_lum = np.where(body_d, np.maximum(lum, 220.0), out_lum)
    out_lum = np.where(lines_d, np.minimum(lum * 0.25, 18.0), out_lum)
    # Outer rim: ensure black outline even on light edges
    edge = sil & ~dilate_mask(body_d & ~lines_d, 0)
    # Strong outer black stroke: silhouette border
    core = dilate_mask(opaque, 0)
    border = dilate_mask(core, line_radius) & ~dilate_mask(core, max(0, line_radius - 2))
    # Better: outer ring of thickened silhouette
    outer = dilate_mask(opaque, line_radius + 1)
    inner = dilate_mask(opaque, max(0, line_radius - 1))
    ring = outer & ~inner
    out_lum = np.where(ring, 12.0, out_lum)
    out_lum = np.where(lines_d, 12.0, out_lum)
    # White interiors
    interior = dilate_mask(body, 0) & ~lines_d & ~ring
    out_lum = np.where(interior, 250.0, out_lum)
    # Slight mid shading kept only if not ring/line
    mid = body & (lum < 220) & (lum >= 95) & ~lines_d
    out_lum = np.where(mid, np.clip(lum + 40, 180, 245), out_lum)

    alpha = np.where(outer | lines_d | body_d, 255.0, 0.0)
    out = np.dstack([out_lum, out_lum, out_lum, alpha])
    return clear(out)


def thicken_ui_glyph(rgba: np.ndarray, radius: int = 3) -> np.ndarray:
    """Bold UI glyph by dilating alpha and darkening ink mass."""
    rgb, a = rgba[..., :3], rgba[..., 3]
    opaque = a > 25
    if not opaque.any():
        return rgba
    bold = dilate_mask(opaque, radius)
    # Also dilate dark ink cores for outline-style icons
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    # For light-on-dark or dark-on-light glyphs, expand coverage
    # Sample mean of opaque
    mean_lum = float(lum[opaque].mean())
    out_rgb = rgb.copy()
    if mean_lum > 140:
        # light glyph on magenta -> keep light body, expand
        out_rgb[..., 0] = np.where(bold, np.maximum(rgb[..., 0], 230), 0)
        out_rgb[..., 1] = np.where(bold, np.maximum(rgb[..., 1], 230), 0)
        out_rgb[..., 2] = np.where(bold, np.maximum(rgb[..., 2], 220), 0)
        # thicken dark lines within
        dark = opaque & (lum < 90)
        dark_d = dilate_mask(dark, max(1, radius - 1))
        for c in range(3):
            out_rgb[..., c] = np.where(dark_d, 20, out_rgb[..., c])
    else:
        # dark glyph: expand solid dark mass
        for c in range(3):
            out_rgb[..., c] = np.where(bold, np.minimum(rgb[..., c], 40), 0)
        # preserve a little highlight from original interior
        hi = opaque & (lum > mean_lum * 1.2)
        for c in range(3):
            out_rgb[..., c] = np.where(hi & bold, np.clip(rgb[..., c] + 10, 0, 80), out_rgb[..., c])
    alpha = np.where(bold, 255.0, 0.0)
    return clear(np.dstack([out_rgb[..., 0], out_rgb[..., 1], out_rgb[..., 2], alpha]))


def to_ui_dark(rgba: np.ndarray) -> np.ndarray:
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
    if sub.mean() > 130:
        # cream/white diagram with black lines -> solid dark body + blacker lines
        ink = DARK_INK[None, None, :] * (0.55 + 0.35 * t)[..., None]
        ink = np.where(lum[..., None] > 200, DARK_INK * 0.85, ink)  # fill
        ink = np.where(lum[..., None] < 70, DARK_INK * 0.25, ink)  # lines
    else:
        ink = DARK_INK[None, None, :] * (0.35 + 0.75 * t)[..., None]
    return clear(np.concatenate([np.clip(ink, 0, 255), a[..., None]], -1))


def to_ui_light(dark: np.ndarray) -> np.ndarray:
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
    cream = LIGHT_INK[None, None, :] * (0.88 + 0.12 * t)[..., None]
    cream = np.where(lum[..., None] < lo + 0.2 * (hi - lo), LIGHT_INK * 0.62, cream)
    return clear(np.concatenate([np.clip(cream, 0, 255), a[..., None]], -1))


def process_structure(name: str) -> None:
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
        print(f"missing structure {name}")
        return
    arr = np.array(Image.open(src).convert("RGBA"))
    rgb = arr[..., :3].astype(np.float32)
    out, alpha = key_bg(rgb)
    rgba = np.dstack([out, alpha])
    rgba = tight_crop(rgba, fill=0.86)
    # Thicken structure strokes
    rgba = thicken_ui_glyph(rgba, radius=2)
    # Ensure lines bold: dilate dark parts again on diagram
    lum = 0.299 * rgba[..., 0] + 0.587 * rgba[..., 1] + 0.114 * rgba[..., 2]
    a = rgba[..., 3]
    dark = (a > 20) & (lum < 100)
    dark_d = dilate_mask(dark, 2)
    for c in range(3):
        rgba[..., c] = np.where(dark_d, np.minimum(rgba[..., c], 25), rgba[..., c])
    rgba[..., 3] = np.where(dark_d | (a > 20), np.maximum(a, 255.0 * dark_d), a)
    rgba = clear(rgba)
    dark_ui = to_ui_dark(rgba)
    # Extra bold pass on dark
    dark_ui = thicken_ui_glyph(dark_ui, radius=2)
    light_ui = to_ui_light(dark_ui)
    Image.fromarray(np.clip(dark_ui, 0, 255).astype(np.uint8)).save(UI / f"{name}_dark.png")
    Image.fromarray(np.clip(light_ui, 0, 255).astype(np.uint8)).save(UI / f"{name}_light.png")
    print(f"structure -> {name}")


def thicken_existing_unit(path: Path) -> None:
    arr = np.array(Image.open(path).convert("RGBA")).astype(np.float32)
    # re-crop first
    arr = tight_crop(arr, fill=0.84)
    arr = thicken_unit_rgba(arr, line_radius=3)
    arr = tight_crop(arr, fill=0.84)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(path)


def thicken_existing_ui(dark_path: Path, light_path: Path) -> None:
    arr = np.array(Image.open(dark_path).convert("RGBA")).astype(np.float32)
    arr = tight_crop(arr, fill=0.72)
    arr = thicken_ui_glyph(arr, radius=3)
    # solidify: make opaque mass denser
    a = arr[..., 3]
    bold = dilate_mask(a > 20, 1)
    arr[..., 3] = np.where(bold, 255.0, 0.0)
    for c in range(3):
        arr[..., c] = np.where(bold, np.minimum(arr[..., c], 45), 0)
    # slight interior from original where present
    orig = np.array(Image.open(dark_path).convert("RGBA")).astype(np.float32)
    orig = tight_crop(orig, fill=0.72)
    olum = 0.299 * orig[..., 0] + 0.587 * orig[..., 1] + 0.114 * orig[..., 2]
    # if original had light interiors, keep mild highlight
    hi = (orig[..., 3] > 20) & (olum > 80)
    # resize hi to match if needed - same crop size after tight_crop should match SIZE
    if hi.shape == arr.shape[:2]:
        for c in range(3):
            arr[..., c] = np.where(hi & bold, np.clip(arr[..., c] + 25, 0, 70), arr[..., c])
    dark = clear(arr)
    light = to_ui_light(dark)
    # thicken light as well for parity
    light = thicken_ui_glyph(light, radius=1)
    # remap light to cream properly
    light = to_ui_light(dark)
    Image.fromarray(np.clip(dark, 0, 255).astype(np.uint8)).save(dark_path)
    Image.fromarray(np.clip(light, 0, 255).astype(np.uint8)).save(light_path)


def main() -> None:
    # 1) Structures from raw
    for name in sorted(STRUCTURES):
        process_structure(name)

    # 2) Thicken all units
    for path in sorted(UNITS.glob("*.png")):
        thicken_existing_unit(path)
        print(f"unit thickened -> {path.name}")

    # 3) Thicken all UI pictograms (skip chrome, skip structures already processed)
    for dark_path in sorted(UI.glob("*_dark.png")):
        name = dark_path.name.replace("_dark.png", "")
        if any(name.startswith(p) for p in CHROME_PREFIXES):
            continue
        if name in STRUCTURES:
            continue  # already bold from process_structure
        light_path = UI / f"{name}_light.png"
        if not light_path.exists():
            continue
        thicken_existing_ui(dark_path, light_path)
        print(f"ui thickened -> {name}")

    print("DONE")


if __name__ == "__main__":
    main()
