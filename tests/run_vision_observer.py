import json,hashlib
import numpy as np
from vision_sim import ROOT,HDL,simulate
from vision_models import target,motion,luma
OUT=ROOT/'tmp/vision_track_motion/observer_unit'
def main():
    OUT.mkdir(parents=True,exist_ok=True);f=(OUT/'vectors.txt').open('w');fid=0;toggle=0;checks=0
    def emit(r=1,v=0,u=0,l=0,d=0,g=0,t=0,m=0,check=0,state=0,cx=0,cy=0,n=0,frame=0,mn=0,ms=0,ok=1):
        f.write(f'{r} {v} {u} {l} {d:024x} {g:08x} {t} {m} {check} {state} {cx} {cy} {n} {frame} {mn} {ms} {ok} {toggle}\n')
    def image(move=0,empty=False,dark=0):
        a=np.full((64,128,3),230,np.uint8)
        if not empty:a[16:48,16+move:48+move]=(220,40,40)
        return np.maximum(a.astype(int)-dark,0).astype(np.uint8)
    for _ in range(4):emit(r=0)
    for _ in range(4):emit()
    previous=None
    def frame(a,state,highlight,inline=False,bad=False):
        nonlocal fid,toggle,checks,previous
        fid+=1;mask,present,xy,n=target(a);changes,mn,ms=motion(a,previous);g=luma(a)
        if not inline:emit(u=1)
        for y in range(64):
            for x in range(0,128,4):
                tm=sum(int(mask[y,x+k] and highlight and not bad)<<(3-k) for k in range(4))
                mm=15 if not bad and y%16==15 and x%32==28 and changes[y//16,x//32] else 0
                emit(v=1,u=int(inline and x==0 and y==0),l=int(x==124)^(bad and y==2 and x==124),
                     d=int.from_bytes(a[y,x:x+4].tobytes(),'big'),g=int.from_bytes(g[y,x:x+4].tobytes(),'big'),t=tm,m=mm)
                if x==40 and y%5==2:emit()
        for _ in range(10):emit()
        if not bad:toggle^=1
        emit(check=1,state=state,cx=xy[0] if not bad else 0,cy=xy[1] if not bad else 0,n=n if not bad else 0,
             frame=fid,mn=mn if not bad else 0,ms=ms if not bad else 0,ok=int(not bad));checks+=1
        previous=a if not bad else None
    frame(image(),1,False);frame(image(),1,False,inline=True);frame(image(),2,False)
    frame(image(32),2,True);frame(image(empty=True),3,True);frame(image(32),2,True)
    frame(image(32),0,False,bad=True)
    frame(image(32),1,False,inline=True);frame(image(32),1,False);frame(image(32),2,False)
    for _ in range(8010):emit()
    previous=None
    frame(image(32),1,False)
    # An abandoned frame must clear history before the next full frame.
    fid+=1;emit(u=1)
    for y in range(20):
        for x in range(0,128,4):emit(v=1,l=int(x==124),d=int.from_bytes(bytes((230,230,230))*4,'big'),g=0xe6e6e6e6)
    previous=None
    frame(image(32),1,False)
    frame(image(32,dark=50),1,False);frame(image(32,dark=50),2,False)
    f.close()
    src=[ROOT/'tests/tb_vision_observer.sv',HDL/'vision/vision_source_observer.v',HDL/'vision/vision_motion_grid.v']
    src +=[ROOT/'features/color_target/rtl'/n for n in ('color_classify.v','color_target_mask_stats.v','color_target_track.v','color_target_track_guard.v')]
    digests={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}
    log=simulate(OUT,'tb_vision_observer',src,plus=['+STIM='+(OUT/'vectors.txt').as_posix()])
    assert 'PASS vision observer' in log
    (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,checks=checks,sources=digests),indent=2)+'\n')
    print(log[-750:])
if __name__=='__main__':main()
