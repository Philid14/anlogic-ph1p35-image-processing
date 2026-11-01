import json,hashlib
import numpy as np
import run_edge_control_v1 as c
from ruler_usability_model import scenarios,robust
OUT=c.ROOT/'tmp/inspection_v3/unit';OUT.mkdir(parents=True,exist_ok=True)
def main():
    req=0;checks=0
    f=(OUT/'ruler_vectors.txt').open('w')
    def emit(r=1,v=0,u=0,l=0,en=1,data=0,check=0,span=0,ok=0,status=0):
        f.write(f'{r} {v} {u} {l} {en} {req} {data:08x} {check} {span} {ok} {status}\n')
    def frame(lines,inline=False,bad=False):
        if len(lines)<12:lines=np.concatenate((lines,np.full((12-len(lines),512),225,np.uint8)))
        if not inline:emit(u=1)
        for y in range(112):
            for x in range(0,640,4):
                pix=lines[(y-32)//3,x-64:x-60] if y in range(32,66,3) and 64<=x<576 else np.full(4,225,np.uint8)
                emit(v=1,u=int(inline and y==0 and x==0),l=int(x==636)^(bad and y==81 and x==636),data=int.from_bytes(bytes(pix),'big'))
            if y%7==1:emit()
    for _ in range(3):emit(r=0)
    cases=list(scenarios().items())
    for start in (0,5,13,21,29):
        a=np.full((12,512),225,np.uint8)
        ticks=next(iter(scenarios().values()))[0][0]
        for j,y in enumerate(range(0,36,3)):
            if start<=y<start+6:a[j]=ticks
        cases.append((f'6px_vertical_band_at_{start}',(a,True,340)))
    for index,(name,(a,ok,ideal)) in enumerate(cases):
        if len(a)<12:a=np.concatenate((a,np.full((12-len(a),512),225,np.uint8)))
        expected=robust(a)
        req^=1;emit();frame(a,inline=index%2==0);emit(u=1)
        for _ in range(6000):emit()
        emit(check=1,span=expected['span'],ok=int(ok),status=expected['status']);checks+=1
    a=next(iter(scenarios().values()))[0]
    req^=1;emit();frame(a,bad=True);emit(u=1)
    for _ in range(6000):emit()
    emit(check=1,status=6);checks+=1
    req^=1;emit();emit(en=0);emit(en=0,check=1,status=7);checks+=1
    for _ in range(3):emit(r=0,en=0)
    emit(en=0,check=1,status=0);checks+=1
    f.close()
    sources=[c.ROOT/'tests/tb_ruler_robust_calibration.sv',c.HDL/'isp/ruler_robust_calibration.v']
    hashes={p.relative_to(c.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    log=c.simulate(OUT,'tb_ruler_robust_calibration',sources,plus=['+STIM='+(OUT/'ruler_vectors.txt').as_posix()])
    assert hashes=={p.relative_to(c.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (OUT/'ruler_console.txt').write_text(log)
    (OUT/'ruler_results.json').write_text(json.dumps(dict(passed=True,checks=checks,scope='Synthetic model vs actual RTL; no board success claim',sources=hashes),indent=2)+'\n')
if __name__=='__main__':main()
