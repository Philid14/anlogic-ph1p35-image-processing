"""Small color patches and explicit logical-switch diagnostics, independent screen contract."""
import numpy as np
import color_compare_model as color
import inspection_osd_model as old
from auto_dimension_model import draw as old_draw,gap_coordinates
ROIS=((304,304,32,32),(944,304,32,32))

def color_overlay(pixels,x,y,means,sid,font):
    out=[]
    for lane,p in enumerate(pixels):
        px=x+lane;p=tuple(p)
        if 32<=px<1248 and 544<=y<672:
            # Reuse only the frozen textual comparison rule; frame borders below are new.
            p=color.overlay([p],px,y,means,sid,font,means is not None)[0]
        else:
            for (rx,ry,w,h),ink in zip(ROIS,((64,255,128),(64,223,255))):
                if rx-4<=px<rx+w+4 and ry-2<=y<ry+h+2 and not(rx<=px<rx+w and ry<=y<ry+h):p=ink
        out.append(p)
    return out

def status(pixels,x,y,mode,et,bt,font,ui,ruler,fifo_counts=0x1234abcd):
    raw=old.status(pixels,x,y,mode,et,bt,font,fifo_counts)
    out=np.frombuffer(raw,dtype=np.uint8).reshape(4,3).copy()
    if 136<=y<168:
        bits_text=''.join(str((ui>>i)&1) for i in range(4))
        text=f'SW:{bits_text} R:{ruler} '+('M' if ui&2 else 'C' if ui&1 else '-')+('A' if ui&2 and ui&8 else ' ')
        for lane in range(4):
            px=x+lane
            if 800<=px<1248:
                col=(px-800)//32;glyph=font.get(ord(text[col]),{}).get((y-136)//2,0)
                if glyph&(1<<(15-(px-800)%32//2)):out[lane]=(16,16,48) if pixels[lane][1]>=128 else (255,255,0)
    return out.tobytes()

def draw(rgb,m,font,calibrated,sx,sy,cal=False,status=0,gaps=(0,0,0,0)):
    out=old_draw(rgb,m,font,calibrated,sx,sy,cal,status,gaps)
    if cal:
        # The old guides are the only changed part of the engineering raster.
        yy,xx=np.indices(rgb.shape[:2]);region=(xx>=384)&(xx<896)&(xx%16<4)
        old_guides=region&np.isin(yy,(304,306,308))
        out[old_guides]=rgb[old_guides]
        new_guides=region&np.isin(yy,(288,294,300,306,312,318))
        dark=rgb[:,:,1]>=128
        out[new_guides&dark]=(16,16,48);out[new_guides&~dark]=(255,255,128)
    return out
