"""Independent ruler line models. Synthetic evidence, never phone RGB as sensor RGB."""
import numpy as np

def centers(line):
    low,high=int(line.min()),int(line.max())
    if high-low<24:return [],False
    black=line<(low+high)//2
    starts=np.flatnonzero(black & ~np.r_[False,black[:-1]])
    ends=np.flatnonzero(black & ~np.r_[black[1:],False])
    pairs=[];previous=None
    for a,b in zip(starts,ends):
        if a==0 or b==len(line)-1:continue
        if b-a+1>8:previous=None;continue
        c=int(a+b)
        if previous is not None and 4<=c-previous<=32:pairs.append(c-previous)
        previous=c
    return pairs,True

def robust(rows):
    previous=None;any_contrast=False;details=[]
    for row in rows:
        gaps,contrast=centers(row);any_contrast|=contrast
        if not gaps:details.append(None);continue
        groups=[np.array([g for g in gaps if abs(g-center)<=2],np.int32) for center in range(4,33)]
        best=max(groups,key=len)
        if len(best)<24 or int(best.sum())<256 or len(best)*4<len(gaps)*3:
            details.append(None);continue
        span=(int(best.sum())*50+len(best)//2)//len(best)
        if not 200<=span<=1600:details.append(None);continue
        details.append(span)
        if previous is not None and abs(span-previous)<=8:return dict(ok=True,span=(span+previous+1)//2,status=3,lines=details)
        previous=span
    return dict(ok=False,span=0,status=5 if any_contrast else 4,lines=details)

def strict(rows):
    sample=rows[[2,3,4]] if len(rows)>3 else rows
    low,high=int(sample.min()),int(sample.max())
    if high-low<48:return dict(ok=False)
    spans=[]
    for row in sample:
        black=row<(low+high)//2
        a=np.flatnonzero(black & ~np.r_[False,black[:-1]])
        b=np.flatnonzero(black & ~np.r_[black[1:],False])
        valid=[(x,y) for x,y in zip(a,b) if x>0 and y<511]
        if any(y-x+1>6 for x,y in valid) or len(valid)<16:continue
        gap=np.diff([x+y for x,y in valid])
        if gap.min()<4 or gap.max()>32 or gap.max()>gap.min()+2:continue
        spans.append(int((sum(gap)*50+len(gap)//2)//len(gap)))
    return dict(ok=any(abs(a-b)<=8 for j,a in enumerate(spans) for b in spans[j+1:]))

def ticks(pitch=3.4,dark=30,light=225,width=1,phase=0,missing=0):
    row=np.full(512,light,np.uint8)
    for i,p in enumerate(np.rint(np.arange(7+phase,510,pitch)).astype(int)):
        if missing and i%missing==missing-1:continue
        row[p:p+width]=dark
    return row

def scenarios():
    rng=np.random.default_rng(20261101)
    cases={}
    def add(name,rows,ok,pitch=3.4):cases[name]=(np.array(rows,np.uint8),ok,round(pitch*100))
    a=[ticks(phase=i*.1) for i in range(6)];add('clean_fractional',a,True)
    add('low_contrast_ticks',[ticks(dark=195,light=225) for _ in range(6)],True)
    a=[ticks(missing=12) for _ in range(6)];add('occasional_missing_tick',a,True)
    a=np.array([ticks() for _ in range(6)]);a[:,210:230]=10;add('wide_dark_artifact',a,True)
    a=np.full((6,512),225,np.uint8);a[:2]=ticks();add('ticks_away_from_old_three_lines',a,True)
    a=np.full((6,512),225,np.uint8);a[2]=ticks();add('only_one_readable_line',a,False)
    add('flat_no_ruler',np.full((6,512),140,np.uint8),False)
    add('random_texture',rng.integers(20,226,(6,512),dtype=np.uint8),False)
    add('inconsistent_scale',[ticks(p) for p in (2,3,4,5,7,11)],False)
    a=np.full((6,512),225,np.uint8)
    for p in range(8,510,34):a[:,p:p+2]=20
    add('centimetre_marks_only_at_this_zoom',a,False)
    for p in (2,2.2,2.5,5,6.6,11.7,16):add('pitch_'+str(p),[ticks(p,phase=i*.1) for i in range(6)],True,p)
    return cases

def main():
    import json
    from pathlib import Path
    rows=[]
    for name,(image,ok,span) in scenarios().items():
        after=robust(image);before=strict(image)
        assert after['ok']==ok,(name,after)
        if ok:assert abs(after['span']-span)<=1,(name,after,span)
        rows.append(dict(case=name,old_accepted=before['ok'],new=after,expected=ok))
    out=Path('tmp/inspection_v3');out.mkdir(parents=True,exist_ok=True)
    (out/'MODEL_COMPARISON.json').write_text(json.dumps(dict(passed=True,scope='Synthetic spacing/contrast/placement evidence only; board failure code not captured in V2 photo',cases=rows),indent=2)+'\n')
    print('PASS',len(rows),'synthetic ruler comparisons; old/new evidence saved')
if __name__=='__main__':main()
