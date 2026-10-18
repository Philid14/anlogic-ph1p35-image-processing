"""Direct arbitrary-bit center checks, independent of an edge's broad gradient."""
from pathlib import Path
import json
import numpy as np
import edge_quality_model as model
import run_edge_control_v1 as control


def main():
    out=control.ROOT/'tmp/edge_temporal_v1';rng=np.random.default_rng(926);logs=[]
    for width in (64,68,72,76,1280):
        height=24;path=out/'confidence.txt';lines=[]
        for frame in range(6):
            bits=rng.integers(0,2,(height,width//2)).astype(bool)
            if frame==0:bits[:]=1
            if frame==1:bits[:]=0
            centers,_=model.window_labels(bits,bits,False,6)
            early=frame%2==0
            if early:lines+=['0 1 0 0 0\n']+['0 0 0 0 0\n']*4
            for y in range(height):
                for x in range(0,width//2,2):
                    word=(int(bits[y,x])<<1)|int(bits[y,x+1]);expected=(int(centers[y,x])<<1)|int(centers[y,x+1])
                    lines.append(f'1 {int(not early and y==0 and x==0)} {int(x==width//2-2)} {word} {expected}\n')
                    if x%10==6:lines.append('0 0 0 0 0\n')
                lines.append('0 0 0 0 0\n')
        lines+=['0 0 0 0 0\n']*5;path.write_text(''.join(lines))
        logs.append(control.simulate(out,'tb_edge_center_pair_delay',[control.ROOT/'tests/tb_edge_center_pair_delay.v',control.HDL/'isp/edge_center_pair_delay.v'],[f'-Ptb_edge_center_pair_delay.W={width}'],[f'+STIM={path.as_posix()}']))
    (out/'confidence_results.json').write_text(json.dumps(logs,indent=2)+'\n')


if __name__=='__main__':main()
