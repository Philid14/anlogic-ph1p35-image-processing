"""Independent numeric truth for red HSV classification and block-frame differences."""
import colorsys
import numpy as np
def red_hit(rgb):
    r,g,b=map(int,rgb);h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
    return max(r,g,b)>=32 and max(r,g,b)-min(r,g,b)>=24 and min(h*360,360-h*360)<=30+1e-10
def luma(rgb):
    v=rgb.astype(np.uint16)
    return ((77*v[:,:,0]+150*v[:,:,1]+29*v[:,:,2]+128)>>8).astype(np.uint8)
def means(rgb):
    g=luma(rgb);h,w=g.shape
    return ((g.reshape(h//16,16,w//32,32).sum(axis=(1,3),dtype=np.uint32)+256)//512).astype(np.uint8)
def motion(rgb,previous):
    h,w=rgb.shape[:2];changed=np.zeros((h//16,w//32),bool)
    if previous is not None:changed=np.abs(means(rgb).astype(int)-means(previous).astype(int))>=12
    n=int(changed.sum());state=1 if previous is None else 4 if n*4>changed.size*3 else 3 if n>=3 else 2
    return changed,n,state
def target(rgb):
    mask=np.array([red_hit(p) for p in rgb.reshape(-1,3)]).reshape(rgb.shape[:2])
    yy,xx=np.where(mask);n=len(xx)
    return mask, bool(n>=64), ((int(xx.min()+xx.max())//2,int(yy.min()+yy.max())//2) if n>=64 else (0,0)),n
