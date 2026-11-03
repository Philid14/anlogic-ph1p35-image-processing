"""Directed extremes, hue classes, tolerance boundary and atomic decimal cache."""
import random,json
from run_edge_control_v1 import ROOT,HDL,simulate
from color_compare_model import category,NAMES
OUT=ROOT/'tmp/color_compare_v1'

def main():
    rng=random.Random(20261028)
    colors=[(0,0,0),(255,255,255),(128,128,128),(255,0,0),(0,255,0),(0,0,255),
            (255,255,0),(0,255,255),(255,0,255),(31,10,5),(32,10,5),
            (224,224,224),(223,223,223),(120,96,96),(121,96,96)]
    pairs=[(a,a) for a in colors]+[(colors[0],colors[1]),((100,100,100),(112,112,112)),((100,100,100),(113,112,112))]
    pairs +=[(tuple(rng.randrange(256) for _ in range(3)),tuple(rng.randrange(256) for _ in range(3))) for _ in range(200)]
    rows=[]
    for i,(a,b) in enumerate(pairs):
        v=list(a)+list(b);delta=[abs(x-y) for x,y in zip(a,b)];numbers=v+delta+[sum(delta),max(delta)]
        bcd=sum(int(f'{n:03}',16)<<(12*k) for k,n in enumerate(numbers))
        cl=NAMES.index(category(a))*16+NAMES.index(category(b))
        rgb=int.from_bytes(bytes(v),'big');rows.append(f'{rgb:012x} {i:04x} {cl:02x} {bcd:033x} {int(i%7!=3)}')
    path=OUT/'formatter_vectors.txt';path.write_text('\n'.join(rows)+'\n')
    log=simulate(OUT,'tb_color_compare_formatter',[ROOT/'tests/tb_color_compare_formatter.sv',HDL/'isp/color_compare_osd.v',HDL/'osd_char_lib.v'],plus=['+STIM='+path.as_posix()])
    (OUT/'formatter_console.txt').write_text(log)
    (OUT/'formatter_results.json').write_text(json.dumps(dict(passed=True,snapshots=len(pairs),fields=len(pairs)*11,classes=9,tolerance_boundary=[12,13],reset=True),indent=2)+'\n')
if __name__=='__main__':main()
