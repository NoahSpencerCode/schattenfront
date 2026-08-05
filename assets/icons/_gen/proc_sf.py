#!/usr/bin/env python3
"""Process SF-style monochrome icons: keep greyscale depth, drop magenta + app plates."""
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageFilter
from collections import deque

SESS = Path("/Users/noah/.grok/sessions/%2FUsers%2Fnoah%2Fschattenfront%2Fww2-rts-game/019fa433-4d97-7c62-8995-8d11562835fb/images")
UI = Path(__file__).resolve().parents[1] / "ui"
SIZE = 384

def process(src, dest, fill=0.72):
    arr = np.array(Image.open(src).convert("RGBA"))
    rgb = arr[..., :3].astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dist = np.sqrt((r - 255) ** 2 + (g - 0) ** 2 + (b - 255) ** 2)
    mag = (r + b) / 2 - g
    h, w = rgb.shape[:2]
    bg = np.median(np.concatenate([
        rgb[2:18, 2:18].reshape(-1, 3), rgb[2:18, w-18:w-2].reshape(-1, 3),
        rgb[h-18:h-2, 2:18].reshape(-1, 3), rgb[h-18:h-2, w-18:w-2].reshape(-1, 3),
    ], 0), 0)
    d2 = np.sqrt(((rgb - bg) ** 2).sum(-1))
    # also key light pink app-icon plate (lighter magenta)
    is_mag = (
        ((r > 160) & (b > 120) & (g < 160) & (mag > 40))
        | ((dist < 110) & (g < 170))
        | (d2 < 35)
        | ((r > 200) & (b > 160) & (g > 80) & (g < 200) & (mag > 20))  # soft pink plate
    )
    alpha = np.where(is_mag, 0.0, 255.0)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    # greyscale subject: map to dark greys for depth (SF hierarchical)
    # light greys stay lighter, black stays black
    out_lum = np.clip(lum, 0, 255)
    # if mostly white icon on magenta, invert
    mask = alpha > 30
    if mask.any() and out_lum[mask].mean() > 160:
        out_lum = np.where(mask, 255 - out_lum, out_lum)
    # compress into near-black range with depth: 8..90
    if mask.any():
        sub = out_lum[mask]
        lo, hi = np.percentile(sub, 2), np.percentile(sub, 98)
        if hi <= lo:
            hi = lo + 1
        t = np.clip((out_lum - lo) / (hi - lo), 0, 1)
        # dark lines = 8, mid fills = 55, highlights = 95
        mapped = 8 + t * 90
        out_lum = np.where(mask, mapped, 0)
    rgba = np.dstack([out_lum, out_lum, out_lum, alpha])
    # remove hollow rounded-rect app plate component if present
    a = rgba[..., 3]
    solid = a > 40
    labels = np.zeros(solid.shape, np.int32)
    cur = 0
    sizes = {}
    hh, ww = solid.shape
    for y in range(hh):
        for x in range(ww):
            if solid[y, x] and labels[y, x] == 0:
                cur += 1
                q = deque([(y, x)])
                labels[y, x] = cur
                cnt = 0
                ys, xs = [], []
                while q:
                    cy, cx = q.popleft()
                    cnt += 1
                    ys.append(cy); xs.append(cx)
                    for dy, dx in ((0,1),(0,-1),(1,0),(-1,0)):
                        ny, nx = cy+dy, cx+dx
                        if 0<=ny<hh and 0<=nx<ww and solid[ny,nx] and labels[ny,nx]==0:
                            labels[ny,nx]=cur
                            q.append((ny,nx))
                sizes[cur] = (cnt, min(ys), max(ys), min(xs), max(xs))
    # drop large hollow frames
    for lid, (cnt, y0, y1, x0, x1) in sizes.items():
        bh, bw = y1-y0+1, x1-x0+1
        fill_r = cnt / max(1, bh*bw)
        aspect = bw / max(1, bh)
        if 0.75 < aspect < 1.35 and fill_r < 0.18 and cnt > 500:
            rgba[labels==lid, 3] = 0
    mask = rgba[..., 3] > 30
    if not mask.any():
        print("EMPTY", dest)
        return
    ys, xs = np.where(mask)
    crop = rgba[ys.min():ys.max()+1, xs.min():xs.max()+1]
    ch, cw = crop.shape[:2]
    side = max(ch, cw)
    pad = np.zeros((side, side, 4), np.float32)
    pad[(side-ch)//2:(side-ch)//2+ch, (side-cw)//2:(side-cw)//2+cw] = crop
    ns = int(SIZE * fill)
    im = Image.fromarray(np.clip(pad, 0, 255).astype(np.uint8)).resize((ns, ns), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(im, ((SIZE-ns)//2, (SIZE-ns)//2), im)
    o = np.array(canvas)
    o[o[..., 3] < 12] = 0
    Image.fromarray(o).save(dest)
    print(f"-> {Path(dest).name:28s} op={(o[...,3]>20).sum()}")

if __name__ == "__main__":
    # proc_sf.py num name [fill]
    num = int(sys.argv[1])
    name = sys.argv[2]
    fill = float(sys.argv[3]) if len(sys.argv) > 3 else 0.72
    process(SESS / f"{num}.jpg", UI / f"{name}.png", fill)
