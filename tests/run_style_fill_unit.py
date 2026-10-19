from pathlib import Path
import tempfile,json
import numpy as np
import run_edge_control_v1 as c
from style_fill_model import style,scenes
OUT=c.ROOT/'tmp/edge_style_fill_v1'

def vectors(path,w,h):
    rng=np.random.default_rng(861)
    frames=list(scenes(w,h).values())
    base=frames[0]
    frames += [np.roll(base,dx,axis=1) for dx in (0,1,2,16,0)]
    frames += [np.full_like(base,96),rng.integers(0,256,base.shape,dtype=np.uint8)]
    # Explicit same-color noisy patch at palette decision boundaries. Mean
    # and min/max boundary codes must not collapse to pointwise recoloring.
    for value in (0,15,16,31,32,47,48,63,64,127,128,191,192,239,240,255):
        frame=np.full_like(base,value)
        frame[::2,::2]=np.clip(value+np.array([1,-1,2]),0,255)
        frames.append(frame)
    with path.open('w')as f:
        def cycle(r=1,v=0,u=0,d=0,e=0):f.write(f'{r} {v} {u} {d:024x} {e:024x}\n')
        cycle(0);cycle(0)
        for n,rgb in enumerate(frames):
            if n in (2,9,15):
                # Incomplete frame then reset/SOF, leaving arbitrary RAM bytes.
                cycle(u=1);cycle(v=1,d=(1<<96)-1);cycle(0);cycle(0)
            expected=style(rgb)
            early=n%2==0
            if early:
                cycle(u=1)
                for _ in range(n%7):cycle()
            for y in range(h):
                for x in range(0,w,4):
                    cycle(v=1,u=int(not early and y==0 and x==0),
                          d=int.from_bytes(rgb[y,x:x+4].tobytes(),'big'),
                          e=int.from_bytes(expected[y,x:x+4].tobytes(),'big'))
                    if rng.integers(0,5)==0:cycle(d=int(rng.integers(0,1<<60)))
                for _ in range(n%3):cycle()
            for _ in range(6):cycle()
        for _ in range(8):cycle()
    return len(frames)

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    results=[]
    for w,h in ((4,8),(8,8),(68,32),(128,72),(1280,8)):
        with tempfile.TemporaryDirectory()as t:
            p=Path(t)/'vectors.txt';n=vectors(p,w,h)
            log=c.simulate(OUT,'tb_style_fill_unit',[c.ROOT/'tests/tb_style_fill_unit.v',c.HDL/'isp/style_fill_96.v'],
                [f'-Ptb_style_fill_unit.WIDTH={w}',f'-Ptb_style_fill_unit.HEIGHT={h}'],[f'+STIM={p.as_posix()}'])
            results.append(dict(width=w,height=h,frames=n,log=log))
    (OUT/'unit_results.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__':main()
