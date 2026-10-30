"""Independent mask geometry and ruler conversion, no temporal filtering."""
import numpy as np

def long_runs(a):
    a=np.asarray(a,dtype=bool)
    edges=np.diff(np.r_[False,a,False].astype(np.int8))
    return [(int(s),int(e)) for s,e in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)) if e-s>=3]

def measure(binary,bright=False,roi=(256,160,1024,544),min_row=8,min_rows=3,min_area=64):
    x0,y0,x1,y1=roi;cx=(x0+x1)//2;cy=(y0+y1)//2
    fg=np.asarray(binary,dtype=bool)==bright
    xs=[];ys=[];area=0
    for y in range(y0,y1):
        runs=long_runs(fg[y,x0:x1]);n=sum(e-s for s,e in runs)
        if n>=min_row:
            xs.extend([x0+runs[0][0],x0+runs[-1][1]-1]);ys.append(y);area+=n
    present=bool(len(ys)>=min_rows and area>=min_area and min(xs)>x0 and max(xs)<x1-1 and min(ys)>y0 and max(ys)<y1-1)
    if not present:return dict(present=False,sizes=(0,0,0,0),box=(0,0,0,0),gap=(False,False))
    def gap(a,center):
        runs=long_runs(a)
        if np.any(a[center-1:center+2]):return 0,False
        left=[e-1 for s,e in runs if e<=center]
        right=[s for s,e in runs if s>=center]
        if not left or not right:return 0,False
        n=min(right)-max(left)-1
        return n,n>0
    gx,hx=gap(fg[cy,x0:x1],cx-x0)
    gy,hy=gap(fg[y0:y1,cx],cy-y0)
    return dict(present=True,sizes=(max(xs)-min(xs)+1,max(ys)-min(ys)+1,gx,gy),
        box=(min(xs),max(xs),min(ys),max(ys)),gap=(hx,hy))

def tenths_mm(pixels,calibration_pixels):
    assert calibration_pixels>0
    return (int(pixels)*1000+calibration_pixels//2)//calibration_pixels
