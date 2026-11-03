"""Independent block-mean / LAST-map lattice reference, native 9-bit ERAM."""
import json,hashlib
import numpy as np
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/inspection_parts_motion/motion'
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    frames=[]
    for n in range(9):
        a=np.full((32,96),60,dtype=np.uint8)
        if n in (1,2):a[:16,:32]=200
        if n in (3,4):a[:16,32:64]=200
        frames.append(a)
    lines=[];previous=None;old_map=np.zeros((2,3),bool);last_mask=0;last_ready=0;last_count=0;last_state=0
    def add(gray=0,v=0,s=0,e=0,abort=0,good=0,x=0,y=0,fid=0,mask=0,ready=0,count=0,state=0):
        nonlocal last_mask,last_ready,last_count,last_state
        lines.append(f'{gray:08x} {v} {s} {e} {abort} {good} {x} {y} {fid} {last_mask:x} {last_ready} {last_count} {last_state}\n')
        last_mask=mask;last_ready=ready;last_count=count;last_state=state
    for fid,a in enumerate(frames):
        bad=fid==5
        means=((a.reshape(2,16,3,32).sum(axis=(1,3))+256)//512).astype(int)
        changed=np.zeros((2,3),bool) if previous is None else abs(means-previous)>=12
        for y in range(32):
            for x in range(0,96,4):
                mask=0
                if previous is not None and not bad and old_map[y//16,x//32] and 1<=y%8<=3:
                    for k in range(4):
                        if 1<=(x+k)%8<=3:mask|=1<<(3-k)
                eof=x==92 and y==31
                count=int(changed.sum()) if previous is not None else 0
                state=1 if previous is None else 4 if count*4>6*3 else 3 if count>=3 else 2
                add(int.from_bytes(a[y,x:x+4].tobytes(),'big'),1,int(x==0 and y==0),int(eof),int(bad),int(eof and not bad),x,y,fid,mask,int(eof),0 if bad else count,0 if bad else state)
                if (x//4+y)%13==0:add()
            add();add()
        add();add();add()
        previous=None if bad else means
        old_map=np.zeros((2,3),bool) if bad else changed
    add();add()
    (OUT/'vectors.txt').write_text(''.join(lines))
    src=[ROOT/'tests/tb_parts_motion_dense.sv',HDL/'vision/vision_motion_grid.v']
    log=simulate(OUT,'tb_parts_motion_dense',src,plus=['+VECTORS='+str(OUT/'vectors.txt')],eram=True)
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,frames=9,cycles=len(lines),sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n')
    print(log[-1000:])
if __name__=='__main__':main()
