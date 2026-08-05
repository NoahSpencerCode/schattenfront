
from pathlib import Path
import numpy as np
from PIL import Image
SESS = Path("/Users/noah/.grok/sessions/%2FUsers%2Fnoah%2Fschattenfront%2Fww2-rts-game/019fa433-4d97-7c62-8995-8d11562835fb/images")
SIZE=384
def process(src, dest, fill=0.84):
    arr=np.array(Image.open(src).convert("RGBA"))
    rgb=arr[...,:3].astype(np.float32)
    r,g,b=rgb[...,0],rgb[...,1],rgb[...,2]
    dist=np.sqrt((r-255)**2+(g-0)**2+(b-255)**2)
    mag=((r+b)/2-g)
    h,w=rgb.shape[:2]
    bg=np.median(np.concatenate([
        rgb[2:16,2:16].reshape(-1,3),rgb[2:16,w-16:w-2].reshape(-1,3),
        rgb[h-16:h-2,2:16].reshape(-1,3),rgb[h-16:h-2,w-16:w-2].reshape(-1,3)
    ],0),0)
    d2=np.sqrt(((rgb-bg)**2).sum(-1))
    is_mag=((r>170)&(b>140)&(g<140)&(mag>55))|((dist<100)&(g<150))|(d2<35)
    alpha=np.where(is_mag,0.,255.)
    soft=(~is_mag)&(dist<145)&(g<160)&(r>150)&(b>130)
    alpha=np.where(soft,np.clip((dist-90)/55*255,0,255),alpha)
    out=rgb.copy()
    fringe=(alpha>0)&(mag>18)&(r>g)
    excess=np.maximum(0,mag)
    out[...,0]=np.where(fringe,np.maximum(r-excess*0.55,g),r)
    out[...,2]=np.where(fringe,np.maximum(b-excess*0.55,g),b)
    rgba=np.dstack([out,alpha])
    mask=alpha>35
    if not mask.any():
        print("EMPTY", dest); return False
    ys,xs=np.where(mask)
    crop=rgba[ys.min():ys.max()+1,xs.min():xs.max()+1]
    ch,cw=crop.shape[:2]; side=max(ch,cw)
    pad=np.zeros((side,side,4),np.float32)
    pad[(side-ch)//2:(side-ch)//2+ch,(side-cw)//2:(side-cw)//2+cw]=crop
    ns=int(SIZE*fill)
    im=Image.fromarray(np.clip(pad,0,255).astype(np.uint8)).resize((ns,ns),Image.Resampling.LANCZOS)
    canvas=Image.new("RGBA",(SIZE,SIZE),(0,0,0,0))
    off=(SIZE-ns)//2
    canvas.paste(im,(off,off),im)
    o=np.array(canvas); o[o[...,3]<12]=0
    Image.fromarray(o).save(dest)
    print(f"{Path(dest).name:28s} {(o[...,3]>20).sum()}")
    return True
