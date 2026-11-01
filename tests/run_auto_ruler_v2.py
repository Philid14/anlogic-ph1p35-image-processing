"""Known physical tick spacing oracle + real full-frame geometry, no board claim."""
import json,hashlib
import numpy as np
import run_edge_control_v1 as c
OUT=c.ROOT/'tmp/auto_dimension_v2/unit';OUT.mkdir(parents=True,exist_ok=True)
def main():
    rng=np.random.default_rng(20261101);req=0;count=0
    f=(OUT/'ruler_vectors.txt').open('w')
    def emit(r=1,v=0,u=0,l=0,en=1,data=0,check=0,span=0,ok=0,status=0):
        f.write(f'{r} {v} {u} {l} {en} {req} {data:08x} {check} {span} {ok} {status}\n')
    def frame(lines,inline=False,malformed=False):
        if not inline:emit(u=1)
        for y in range(112):
            for x in range(0,640,4):
                pix=lines[(y-32)//16,x-64:x-60] if y in (32,48,64) and 64<=x<576 else np.full(4,210,np.uint8)
                emit(v=1,u=int(inline and y==0 and x==0),l=int(x==636)^(malformed and y==81 and x==636),data=int.from_bytes(bytes(pix),'big'))
            if y%7==1:emit()
    def pattern(pitch,width=1):
        a=np.full((3,512),225,np.uint8)
        for line in range(3):
            for start in range(7,510,pitch):a[line,start:start+width]=25
        return a
    for _ in range(3):emit(r=0)
    for pitch in (2,3,4,5,7,11,16):
        a=pattern(pitch)
        # One button, the following entire frame is captured. Changes without a button do not recalibrate.
        req^=1;emit();frame(a,inline=pitch%2==0);emit(u=1)
        for _ in range(2500):emit()
        emit(check=1,span=pitch*100,ok=1,status=3);count+=1
        emit(en=0);emit(en=0,check=1,span=pitch*100,ok=1,status=3);count+=1
    # Different illumination and single bad scanline: two intact lines still agree.
    a=pattern(6,2);a[1]=rng.integers(0,255,512,dtype=np.uint8)
    req^=1;emit();frame(a);emit(u=1)
    for _ in range(2500):emit()
    emit(check=1,span=600,ok=1,status=3);count+=1
    cases=[]
    cases.append((np.full((3,512),140,np.uint8),False,4))
    a=pattern(5);a[:,100:110]=225;cases.append((a,False,5))
    a=np.concatenate([pattern(3)[:1],pattern(8)[:1],pattern(14)[:1]]);cases.append((a,False,5))
    a=pattern(5);a[:2]=225;cases.append((a,False,5))
    cases.append((pattern(5),True,6))
    for a,bad,status in cases:
        req^=1;emit();frame(a,malformed=bad);emit(u=1)
        for _ in range(2500):emit()
        emit(check=1,status=status);count+=1
    # Cancellation invalidates the new request; no stale success after leaving CAL.
    req^=1;emit();emit(en=0);emit(en=0,check=1,status=7);count+=1
    for _ in range(3):emit(r=0,en=0)
    emit(en=0,check=1,status=0);count+=1
    f.close()
    sources=[c.ROOT/'tests/tb_ruler_auto_calibration.sv',c.HDL/'isp/ruler_auto_calibration.v']
    log=c.simulate(OUT,'tb_ruler_auto_calibration',sources,plus=['+STIM='+(OUT/'ruler_vectors.txt').as_posix()])
    (OUT/'ruler_console.txt').write_text(log)
    (OUT/'ruler_results.json').write_text(json.dumps(dict(passed=True,checks=count,
      cases='2..16px/mm; early/inline SOF; valid gaps; two-of-three lines; no contrast; missing ticks; mismatch; malformed stream; cancel; reset',
      sources={p.relative_to(c.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}),indent=2)+'\n')
if __name__=='__main__':main()
