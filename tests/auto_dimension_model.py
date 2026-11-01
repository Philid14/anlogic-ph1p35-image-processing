"""Drawing contract: per-pixel raster reference, separate from the RTL renderer."""
import numpy as np
from planar_measure_model import tenths_mm

def gap_coordinates(rgb,bright,cut=130):
    g=(rgb[:,:,0].astype(np.uint16)*77+rgb[:,:,1].astype(np.uint16)*150+rgb[:,:,2].astype(np.uint16)*29+128)>>8
    fg=g>=cut if bright else g<cut
    def between(a,lo,hi,c):
        runs=[];start=None
        for i in range(lo,hi+1):
            if i<hi and a[i]:
                if start is None:start=i
            elif start is not None:
                if i-start>=3:runs.append((start,i-1))
                start=None
        left=[b for a,b in runs if b<c];right=[a for a,b in runs if a>=c]
        return ((max(left)+1,min(right)-1) if left and right else (0,0))
    return between(fg[352],256,1024,640)+between(fg[:,640],160,544,352)

def draw(rgb,m,font,calibrated,sx,sy,cal=False,status=0,gaps=(0,0,0,0)):
    out=rgb.copy();h,w=out.shape[:2];yy,xx=np.indices((h,w));ink=(255,255,128)
    def paint(mask):out[mask]=ink
    def text(x,y,s):
        for i,ch in enumerate(s):
            for r,bits in font.get(ord(ch),{}).items():
                for col in range(16):
                    if bits&(1<<(15-col)) and 0<=y+r<h and 0<=x+i*16+col<w:out[y+r,x+i*16+col]=ink
    msg='CAL: '+{0:'NEED',1:'WAIT',2:'BUSY',3:'OK  '}.get(status,'FAIL')+' K4 CAPTURE'
    if cal:
        paint((xx>=380)&(xx<=899)&(yy>=288)&(yy<=324)&((xx<384)|(xx>=896)|(yy==288)|(yy==324)))
        paint((xx>=384)&(xx<896)&np.isin(yy,[304,306,308])&(xx%16<4))
        text(384,240,'1MM RULER BLACK TICKS');text(384,352,msg)
    elif m.get('valid',False) and m['present']:
        l,r,t,b=m['box'];gl,gr,gt,gb=gaps
        paint(((yy==t-8)&(xx>=l)&(xx<=r))|
              (((xx==l)|(xx==r))&(yy>=t-12)&(yy<=t-2))|
              ((xx==r+20)&(yy>=t)&(yy<=b))|
              (((yy==t)|(yy==b))&(xx>=r+2)&(xx<=r+24)))
        paint((yy>=t-11)&(yy<=t-5)&(
            ((xx>=l)&(xx<=l+6)&(xx-l>=np.abs(yy-(t-8))*2))|
            ((xx<=r)&(xx>=r-6)&(r-xx>=np.abs(yy-(t-8))*2))))
        paint((xx>=r+17)&(xx<=r+23)&(
            ((yy>=t)&(yy<=t+6)&(yy-t>=np.abs(xx-(r+20))*2))|
            ((yy<=b)&(yy>=b-6)&(b-yy>=np.abs(xx-(r+20))*2))))
        if m['gap'][0]:paint(((yy==352)&(xx>=gl)&(xx<=gr))|(((xx==gl)|(xx==gr))&(yy>=348)&(yy<=356)))
        if m['gap'][1]:paint(((xx==640)&(yy>=gt)&(yy<=gb))|(((yy==gt)|(yy==gb))&(xx>=636)&(xx<=644)))
        vals=[tenths_mm(v,sy if i in (1,3) else sx) if calibrated else v*10 for i,v in enumerate(m['sizes'])]
        def label(i):return f'{"WHXY"[i]} {vals[i]//10:4d}.{vals[i]%10} '+('MM' if calibrated else 'PX')+' '
        labels=[((((l+r)//2-96)//4*4),t-30,label(0)),(((r+36)//4*4),(t+b)//2-8,label(1))]
        if m['gap'][0]:labels.append((((gl+gr)//2-96)//4*4,364,label(2)))
        if m['gap'][1]:labels.append((652,(gt+gb)//2-24,label(3)))
        # Earlier text boxes have priority INCLUDING transparent glyph blanks.
        blocked=np.zeros((h,w),bool)
        for x,y,s in labels:
            before=out.copy();text(x,y,s);out[blocked]=before[blocked]
            blocked[max(y,0):min(y+16,h),max(x,0):min(x+192,w)]=True
    else:text(384,184,msg if not calibrated else 'NO VALID OBJECT')
    return out
