"""Wide ROI tests: real multi-frame scheduling, no mixed-frame scale evidence."""
import json,hashlib
import numpy as np
import run_edge_control_v1 as c
from ruler_usability_model import robust
OUT=c.ROOT/'tmp/inspection_v4/area'

def model(image):
    any_contrast=False
    for band,y in enumerate(range(0,len(image)-1,11)):
        rows=np.full((12,768),225,np.uint8);part=image[y:y+12];rows[:len(part)]=part
        m=robust(rows);any_contrast|=m['status']!=4
        if m['ok']:return m,band+1
    return dict(ok=False,span=0,status=5 if any_contrast else 4),band+1

def pattern(y,height=3,x0=0,x1=768,pitch=3.4):
    a=np.full((48,768),225,np.uint8)
    for x in np.rint(np.arange(x0+3,x1-2,pitch)).astype(int):a[y:y+height,x]=30
    return a

def main():
    OUT.mkdir(parents=True,exist_ok=True);req=0;checks=0;records=[]
    f=(OUT/'vectors.txt').open('w')
    def emit(r=1,v=0,u=0,l=0,en=1,data=0,check=0,span=0,ok=0,status=0):
        f.write(f'{r} {v} {u} {l} {en} {req} {data:08x} {check} {span} {ok} {status}\n')
    def frame(image,inline=False,bad=False):
        if not inline:emit(u=1)
        for y in range(128):
            for x in range(0,896,4):
                pix=image[y-32,x-64:x-60] if 32<=y<80 and 64<=x<832 else np.full(4,225,np.uint8)
                emit(v=1,u=int(inline and x==0 and y==0),l=int(x==892)^(bad and y==100 and x==892),data=int.from_bytes(bytes(pix),'big'))
            if y%7==1:emit()
        emit(u=1)
        for _ in range(20000):emit()
    cases=[(f'vertical_{y}',pattern(y,2),True) for y in (0,10,11,21,22,33,46)]
    cases += [('left_partial',pattern(25,3,0,176),True),('right_partial',pattern(35,3,588,768),True),
              ('small_pitch_wide_histogram',pattern(4,3,pitch=2),True),
              ('large_pitch_wide_accumulator',pattern(18,3,pitch=16),True),
              ('flat',np.full((48,768),140,np.uint8),False)]
    # One line in each capture band is never enough; do not pool across frames.
    a=np.full((48,768),225,np.uint8)
    for y in (5,16,27,38):a[y]=pattern(0,1)[0]
    cases.append(('no_cross_frame_pairing',a,False))
    for i,(name,image,ok) in enumerate(cases):
        m,bands=model(image);assert m['ok']==ok,(name,m)
        req^=1;emit()
        for b in range(bands):frame(image,inline=(i+b)%2==0)
        emit(check=1,span=m['span'],ok=int(ok),status=m['status']);checks+=1
        records.append(dict(case=name,bands=bands,**m))
    req^=1;emit();frame(pattern(40),bad=True);emit(check=1,status=6);checks+=1
    req^=1;emit();frame(np.full((48,768),225,np.uint8));emit(en=0);emit(en=0,check=1,status=7);checks+=1
    for _ in range(3):emit(r=0,en=0)
    emit(en=0,check=1,status=0);checks+=1;f.close()
    sources=[c.ROOT/'tests/tb_ruler_area_v4.sv',c.HDL/'isp/ruler_area_calibration.v']
    hashes={p.relative_to(c.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    print('Area vectors ready; running multi-frame actual RTL',flush=True)
    log=c.simulate(OUT,'tb_ruler_area_v4',sources,plus=['+STIM='+(OUT/'vectors.txt').as_posix()])
    assert hashes=={p.relative_to(c.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,checks=checks,cases=records,sources=hashes,
        scope='768px actual datapath; reduced vertical search for schedule tests; full production ROI covered separately'),indent=2)+'\n')
if __name__=='__main__':main()
