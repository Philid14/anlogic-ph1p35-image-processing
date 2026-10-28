"""Independent patch arithmetic and screen contract for COLOR_COMPARE_V1."""
import numpy as np
from functools import lru_cache

REF=(256,256,128,128)
TEST=(896,256,128,128)
NAMES=('BLACK','WHITE','GRAY','RED','GREEN','BLUE','YELLOW','CYAN','MAGENTA')

def patch_means(rgb,rois=(REF,TEST)):
    return [tuple(int(v) for v in np.floor(np.mean(rgb[y:y+h,x:x+w],axis=(0,1))+0.5))
            for x,y,w,h in rois]

def category(v):
    lo,mid,hi=sorted(v)
    if hi<32:return 'BLACK'
    if hi-lo<=24:return 'WHITE' if lo>=224 else 'GRAY'
    if 2*(mid-lo)>=hi-lo:
        return 'YELLOW' if v[2]==lo else 'CYAN' if v[0]==lo else 'MAGENTA'
    return ('RED','GREEN','BLUE')[v.index(hi)]

@lru_cache(maxsize=64)
def text_lines(means,sid,valid=True):
    if not valid:return [' '*38]*3+['WAIT FOR FULL FRAME'.ljust(38)]
    a,b=means
    delta=[abs(x-y) for x,y in zip(a,b)]
    status='MATCH' if max(delta)<=12 else 'DIFF '
    return [f'REF  R:{a[0]:03} G:{a[1]:03} B:{a[2]:03} C:{category(a):7}'.ljust(38),
            f'TEST R:{b[0]:03} G:{b[1]:03} B:{b[2]:03} C:{category(b):7}'.ljust(38),
            f'ABS  R:{delta[0]:03} G:{delta[1]:03} B:{delta[2]:03}'.ljust(38),
            f'L1:{sum(delta):03} MAX:{max(delta):03} LIM:012 {status} LAST:{sid:04X}']

def overlay(pixels,x,y,means,sid,font,valid=True):
    result=[]
    for lane,p in enumerate(pixels):
        px=x+lane;p=tuple(p)
        if 32<=px<1248 and 544<=y<672:
            row=(y-544)//32;col=(px-32)//32
            char=text_lines(tuple(tuple(p) for p in means),sid,valid)[row][col]
            bits=font.get(ord(char),{}).get(((y-544)%32)//2,0)
            ink=[(64,255,128),(64,223,255),(255,255,128),
                 (255,255,0) if not valid else (64,255,128) if max(abs(a-b) for a,b in zip(*means))<=12 else (255,128,64)][row]
            p=ink if bits & (1<<(15-((px-32)%32)//2)) else (16,24,32)
        else:
            for roi,color in [(REF,(64,255,128)),(TEST,(64,223,255))]:
                rx,ry,rw,rh=roi
                if rx-4<=px<rx+rw+4 and ry-2<=y<ry+rh+2 and not(rx<=px<rx+rw and ry<=y<ry+rh):p=color
        result.append(p)
    return result
