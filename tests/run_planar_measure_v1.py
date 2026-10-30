from pathlib import Path
import json,hashlib
import numpy as np
import run_edge_control_v1 as c
from planar_measure_model import measure,tenths_mm
OUT=c.ROOT/'tmp/metrology_v1/unit';OUT.mkdir(parents=True,exist_ok=True)
def pack(values):
    n=0
    for v in values:n=(n<<11)|int(v)
    return n
def main():
    rng=np.random.default_rng(20261030);rows=[]
    state=dict(rv=0,present=False,sizes=(0,0,0,0),box=(0,0,0,0),gap=(False,False),sid=0,cut=0,bright=0)
    def emit(reset=1,v=0,u=0,last=0,bright=0,mask=0,cut=130):
        a=state
        rows.append(f'{reset} {v} {u} {last} {bright} {mask:x} {cut} {a["rv"]} {int(a["present"])} {(int(a["gap"][0])<<1)|int(a["gap"][1])} {pack(a["sizes"]):011x} {pack(a["box"]):011x} {a["sid"]} {a["cut"]} {a["bright"]}')
    for _ in range(3):emit(0)
    previous=None;seq=0
    for f in range(160):
        if f==80:
            state.update(rv=0,present=False,sizes=(0,0,0,0),box=(0,0,0,0),gap=(False,False),sid=0,cut=0,bright=0)
            emit(0);emit(0);previous=None;seq=0
        shape=np.zeros((32,64),bool)
        if f%10==0:shape[8:25,17:45]=1
        elif f%10==1:
            yy,xx=np.indices(shape.shape);d=(xx-32)**2+(yy-16)**2;shape=(d<=100)&(d>=16)
        elif f%10==2:shape[4:28,8:56]=1 # clipped invalid
        elif f%10==3:shape[:]=0
        elif f%10==4:shape[10:13,19:21]=1 # short speck invalid
        elif f%10==5:
            shape[8:25,17:45]=1;shape[12:20,25:39]=0 # central slot
        else:
            left=int(rng.integers(9,25));right=int(rng.integers(40,55))
            top=int(rng.integers(5,11));bottom=int(rng.integers(23,27))
            shape[top:bottom,left:right]=1
            # Isolated specks and 1/2-wide streaks cannot expand bbox.
            shape[5,51]=1;shape[6,9:11]=1
        bright=f%2;binary=shape if bright else ~shape;cut=10+(f%25)*10
        if previous is not None:
            old,good,ocut,obright=previous;state.update(measure(old,obright,(8,4,56,28)),rv=int(good),sid=seq,cut=ocut,bright=obright)
            if not good:state.update(present=False,gap=(False,False))
        else:state.update(rv=0,present=False,gap=(False,False),sid=seq)
        seq=(seq+1)&65535
        early=f%3!=1;broken=f%17==12;truncated=f%23==15;extra=f%31==17
        if early:emit(u=1,bright=bright,cut=cut);emit(bright=bright,cut=cut)
        for y in range(32):
            if truncated and y==31:break
            for x in range(0,64,4):
                mask=sum(int(binary[y,x+k])<<(3-k) for k in range(4))
                emit(v=1,u=int(not early and x==0 and y==0),last=int(x==60 and not(broken and y==3)),bright=bright,mask=mask,cut=cut)
                if (x+y)%19==7:emit(bright=bright,cut=cut)
            emit(bright=bright,cut=cut)
        if extra:emit(v=1,bright=bright,cut=cut)
        previous=(binary,not(broken or truncated or extra),cut,bright)
    old,good,ocut,obright=previous;state.update(measure(old,obright,(8,4,56,28)),rv=int(good),sid=seq,cut=ocut,bright=obright)
    if not good:state.update(present=False,gap=(False,False))
    emit(u=1)
    path=OUT/'stats.txt';path.write_text('\n'.join(rows)+'\n')
    logs={}
    logs['stats']=c.simulate(OUT,'tb_planar_measure',[c.ROOT/'tests/tb_planar_measure.sv',c.HDL/'isp/planar_measure_stats.v'],plus=['+STIM='+path.as_posix()])
    logs['calibration']=c.simulate(OUT,'tb_inspection_calibration',[c.ROOT/'tests/tb_planar_measure.sv',c.HDL/'isp/inspection_calibration.v'])
    vectors=[]
    for i in range(240):
        sx=int(rng.integers(4,185))*4;sy=int(rng.integers(4,89))*4
        vals=tuple(int(v) for v in rng.integers(0,769,4));cal=i%3!=0
        result=[tenths_mm(v,sy if k in (1,3) else sx) if cal else v*10 for k,v in enumerate(vals)]
        digits=''.join(f'{v:05d}' for v in result)
        vectors.append(f'{int(cal)} {sx} {sy} {pack(vals):011x} {digits}')
    path=OUT/'formatter.txt';path.write_text('\n'.join(vectors)+'\n')
    logs['formatter']=c.simulate(OUT,'tb_dimension_formatter',[c.ROOT/'tests/tb_planar_measure.sv',c.HDL/'isp/color_compare_osd.v',c.HDL/'osd_char_lib.v'],plus=['+STIM='+path.as_posix()])
    for k,v in logs.items():(OUT/(k+'_console.txt')).write_text(v)
    result=dict(passed=True,frames=160,stats_cycles=len(rows),metric_snapshots=len(vectors),calibration_test=True,
        scope='independent binary-mask geometry and ruler arithmetic, no camera/board accuracy claim')
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
