"""Independent screen contract for wide CAL guide and illumination diagnostics."""
import numpy as np
import color_compare_model as color
from usability_screen_model import ROIS,status,gap_coordinates,draw as old_draw
from illumination_compare_model import metrics

def color_overlay(pixels,x,y,means,sid,font):
    valid=means is not None
    if valid:
        a,b=means;m=metrics(a,b)
        lines=color.text_lines(tuple(tuple(p) for p in means),sid,True).copy()
        lines[3]=f'L1:{m["l1"]:03} MAX:{m["maximum"]:03} LIM:012 {m["name"]:5} LAST:{sid:04X}'
        c=f'{m["chr"]:03}' if m['reliable'] else '---'
        lines.append(f'CHR:{c} DV:{m["dv"]:03} CLIM:006 RGB RAW'.ljust(38))
    else:lines=[' '*38]*3+['WAIT FOR FULL FRAME'.ljust(38)]+[' '*38]
    out=[]
    for lane,p in enumerate(pixels):
        px=x+lane;p=tuple(p)
        if 32<=px<1248 and 544<=y<704:
            row=(y-544)//32;col=(px-32)//32
            bits=font.get(ord(lines[row][col]),{}).get(((y-544)%32)//2,0)
            status_ink=(255,255,0) if not valid else [(64,255,128),(255,128,64),(255,255,0),(255,128,64)][m['status']]
            ink=[(64,255,128),(64,223,255),(255,255,128),status_ink,status_ink][row]
            if bits&(1<<(15-((px-32)%32)//2)):p=ink
        else:
            for (rx,ry,w,h),ink in zip(ROIS,((64,255,128),(64,223,255))):
                if rx-4<=px<rx+w+4 and ry-2<=y<ry+h+2 and not(rx<=px<rx+w and ry<=y<ry+h):p=ink
        out.append(p)
    return out

def draw(rgb,m,font,calibrated,sx,sy,cal=False,status=0,gaps=(0,0,0,0)):
    if not cal:return old_draw(rgb,m,font,calibrated,sx,sy,False,status,gaps)
    out=rgb.copy();yy,xx=np.indices(rgb.shape[:2])
    palette=np.where((rgb[:,:,1]>=128)[:,:,None],np.array((16,16,48)),np.array((255,255,128))).astype(np.uint8)
    mask=(xx>=252)&(xx<=1027)&(yy>=190)&(yy<=481)&((xx<256)|(xx>=1024)|(yy==190)|(yy==481))
    out[mask]=palette[mask]
    def text(x,y,s):
        for i,ch in enumerate(s):
            for r,bits in font.get(ord(ch),{}).items():
                for col in range(16):
                    if bits&(1<<(15-col)):out[y+r,x+i*16+col]=palette[y+r,x+i*16+col]
    text(256,168,'1CM RULER LONG TICKS')
    text(256,496,'CAL: '+{0:'NEED',1:'WAIT',2:'BUSY',3:'OK  '}.get(status,'FAIL')+' K4 CAPTURE')
    return out
