#!/usr/bin/env python3
from pathlib import Path
import sys, numpy as np
from PIL import Image

SESS = Path("/Users/noah/.grok/sessions/%2FUsers%2Fnoah%2Fschattenfront%2Fww2-rts-game/019fa433-4d97-7c62-8995-8d11562835fb/images")
ROOT = Path(__file__).resolve().parents[1]
SIZE = 384

def process(src, dest, fill=0.82, force_black=False):
    arr = np.array(Image.open(src).convert("RGBA"))
    rgb = arr[..., :3].astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dist = np.sqrt((r - 255) ** 2 + (g - 0) ** 2 + (b - 255) ** 2)
    mag = (r + b) / 2 - g
    h, w = rgb.shape[:2]
    bg = np.median(np.concatenate([
        rgb[2:16, 2:16].reshape(-1, 3), rgb[2:16, w-16:w-2].reshape(-1, 3),
        rgb[h-16:h-2, 2:16].reshape(-1, 3), rgb[h-16:h-2, w-16:w-2].reshape(-1, 3),
    ], 0), 0)
    d2 = np.sqrt(((rgb - bg) ** 2).sum(-1))
    is_mag = ((r > 170) & (b > 140) & (g < 140) & (mag > 55)) | ((dist < 100) & (g < 150)) | (d2 < 38)
    alpha = np.where(is_mag, 0.0, 255.0)
    soft = (~is_mag) & (dist < 145) & (g < 160) & (r > 150) & (b > 130)
    alpha = np.where(soft, np.clip((dist - 90) / 55 * 255, 0, 255), alpha)
    out = rgb.copy()
    fringe = (alpha > 0) & (mag > 18) & (r > g)
    excess = np.maximum(0, mag)
    out[..., 0] = np.where(fringe, np.maximum(r - excess * 0.55, g), r)
    out[..., 2] = np.where(fringe, np.maximum(b - excess * 0.55, g), b)
    if force_black:
        # monochrome black icon: any opaque -> near black by luminance
        lum = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
        # invert if light-on-magenta style so body is black
        mask = alpha > 30
        if mask.any() and lum[mask].mean() > 140:
            # light fills with dark lines -> solid black silhouettes with slight interior
            body = (lum > 80) & mask
            lines = (lum <= 80) & mask
            out_lum = np.zeros_like(lum)
            out_lum = np.where(body, 28.0, out_lum)
            out_lum = np.where(lines, 8.0, out_lum)
            # expand solid black for readability
            from PIL import ImageFilter
            mimg = Image.fromarray(((alpha > 30).astype(np.uint8) * 255))
            mimg = mimg.filter(ImageFilter.MaxFilter(3))
            solid = np.array(mimg) > 127
            out_lum = np.where(solid, np.maximum(out_lum, 22.0), out_lum)
            alpha = np.where(solid, 255.0, 0.0)
            out = np.dstack([out_lum, out_lum, out_lum])
        else:
            # already dark glyph
            out_lum = np.clip(lum * 0.15, 0, 40)
            out = np.dstack([out_lum, out_lum, out_lum])
    rgba = np.dstack([out, alpha]) if out.ndim == 3 and out.shape[2] == 3 else np.dstack([*np.moveaxis(out, -1, 0)[:3], alpha])
    if force_black and out.shape[-1] == 3:
        rgba = np.dstack([out[..., 0], out[..., 1], out[..., 2], alpha])
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
    ns = max(1, int(SIZE * fill))
    im = Image.fromarray(np.clip(pad, 0, 255).astype(np.uint8)).resize((ns, ns), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    off = (SIZE - ns) // 2
    canvas.paste(im, (off, off), im)
    o = np.array(canvas)
    o[o[..., 3] < 12] = 0
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(o).save(dest)
    print(f"-> {Path(dest).name:28s} op={(o[...,3]>20).sum()}")

def from_sess(num, dest, fill=0.82, force_black=False):
    process(SESS / f"{num}.jpg", dest, fill=fill, force_black=force_black)

if __name__ == "__main__":
    # usage: proc.py session_num dest_path [fill] [black]
    num = int(sys.argv[1])
    dest = sys.argv[2]
    fill = float(sys.argv[3]) if len(sys.argv) > 3 else 0.82
    black = len(sys.argv) > 4 and sys.argv[4] == "black"
    from_sess(num, dest, fill, black)
