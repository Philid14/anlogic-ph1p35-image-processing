import json,hashlib
import numpy as np
from ruler_cm_model import ruler,scale
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/ruler_cm/unit'
def main():
    OUT.mkdir(parents=True,exist_ok=True);req=0;records=[];f=(OUT/'vectors.txt').open('w')
    def emit(r=1,v=0,u=0,l=0,en=1,d=0,check=0,m=None):
        m=m or dict(span=0,ok=False,status=0)
        f.write(f'{r} {v} {u} {l} {en} {req} {d:08x} {check} {m["span"]} {int(m["ok"])} {m["status"]}\n')
    def frame(a,inline=False,bad=False):
        if not inline:emit(u=1)
        for y in range(128):
            for x in range(0,896,4):
                pixels=a[y-32,x-64:x-60] if 32<=y<80 and 64<=x<832 else np.full(4,225,np.uint8)
                emit(v=1,u=int(inline and x==0 and y==0),l=int(x==892)^(bad and y==100 and x==892),d=int.from_bytes(pixels.tobytes(),'big'))
            if y%7==1:emit()
        emit(u=1)
        for _ in range(20000):emit()
    for _ in range(4):emit(r=0)
    cases=[('cm_'+str(p),ruler(pitch=p)) for p in (12,20,33.4,34,50,90,120)]
    cases += [('bottom',ruler(top=37)),('boundary_overlap',ruler(top=10)),('thick3',ruler(width=3)),
              ('cm_only',ruler(minor=False)),('short_visible_cm',ruler(x0=340,x1=540,minor=False)),
              ('flat',np.full((48,768),150,np.uint8)),('only_fine_ticks',ruler(pitch=34,top=46)),
              ('four_cm_marks',ruler(x0=20,x1=140,minor=False))]
    # Irregular centimeter pitch and dark speckles: preserve a valid run and
    # average measured intervals instead of selecting a single interval.
    a=ruler(minor=False);a[:,104:110]=225;a[3:18,106:107]=30;cases.append(('jitter_one_mark',a))
    for i,(name,a) in enumerate(cases):
        m=scale(a)
        # Image-construction truth, independent of both the model and RTL:
        # centimeter scale must be10*pitch, not the half/mm harmonic.
        if name.startswith('cm_') and name!='cm_only':expected=int(round(float(name[3:])*10))
        elif name in ('flat','only_fine_ticks','four_cm_marks'):expected=0
        else:expected=340
        assert m['ok']==bool(expected) and (not expected or abs(m['span']-expected)<=2),(name,m,expected)
        req^=1;emit()
        for b in range(5):frame(a,inline=(i+b)%2==0)
        emit(check=1,m=m);records.append(dict(case=name,**m))
    req^=1;emit();frame(ruler(),bad=True);emit(check=1,m=dict(span=0,ok=False,status=6))
    req^=1;emit();frame(ruler());emit(en=0);emit(en=0,check=1,m=dict(span=0,ok=False,status=7))
    for _ in range(3):emit(r=0,en=0)
    emit(en=0,check=1);f.close()
    src=[ROOT/'tests/tb_ruler_cm.sv',HDL/'isp/ruler_area_calibration.v'];print('CM vectors ready',flush=True)
    log=simulate(OUT,'tb_ruler_cm',src,plus=['+STIM='+(OUT/'vectors.txt').as_posix()])
    (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,cases=records,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-700:])
if __name__=='__main__':main()
