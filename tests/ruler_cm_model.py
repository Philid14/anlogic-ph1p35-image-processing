"""Independent image RLE + interval averages, no RTL/FSM execution."""
import numpy as np
def row_scale(a):
    lo,hi=map(int,(a.min(),a.max()))
    if hi-lo<16:return None
    edges=np.diff(np.r_[False,a<lo+(hi-lo)//4,False].astype(int))
    starts=np.where(edges==1)[0];ends=np.where(edges==-1)[0]
    marks=[];best=None
    # Wide dark strokes explicitly break a possible regular tick run.
    for start,end in zip(starts,ends):
        if start==0 or end==len(a) or end-start>4:marks.append(None)
        else:marks.append(int(start+end-1))
    last=None;seed=None;gaps=[]
    for center in marks:
        if center is None:last=None;seed=None;gaps=[];continue
        gap=None if last is None else center-last;last=center
        if gap is None or not 24<=gap<=240:seed=None;gaps=[];continue
        if seed is None or abs(gap-seed)>seed//4+2:seed=gap;gaps=[gap]
        else:gaps.append(gap)
        if len(gaps)>=4 and (best is None or sum(gaps)>sum(best)):best=gaps.copy()
    if best is None:return None
    return (sum(best)*5+len(best)//2)//len(best)
def scale(image):
    result=0;contrast=False
    for y in range(0,len(image)-1,11):
        anchor=None
        for row in image[y:y+12]:
            contrast|=int(row.max())-int(row.min())>=16
            value=row_scale(row)
            if value is None:anchor=None;continue
            if not 120<=value<=1200:anchor=None;continue
            if anchor is not None and abs(value-anchor)<=anchor//8+12:result=max(result,(value+anchor+1)//2)
            anchor=value
    return dict(ok=bool(result),span=result,status=3 if result else 5 if contrast else 4)
def ruler(height=48,top=3,pitch=34.,minor=True,width=1,x0=5,x1=760,seed=0):
    a=np.full((height,768),225,np.uint8);rng=np.random.default_rng(seed)
    unit=pitch/10
    for j,xx in enumerate(np.arange(x0,x1,unit)):
        x=int(round(xx));length=15 if j%10==0 else 9 if j%5==0 else 4
        if not minor and j%10:continue
        a[top:min(height,top+length),x:min(768,x+width)]=30
    return a
