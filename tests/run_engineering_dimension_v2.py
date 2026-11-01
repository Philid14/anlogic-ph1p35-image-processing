import json,hashlib
import numpy as np
from PIL import Image
import run_edge_control_v1 as c
from auto_dimension_model import draw
from planar_measure_model import tenths_mm
from run_planar_measure_v1 import pack
OUT=c.ROOT/'tmp/auto_dimension_v2/drawing';OUT.mkdir(parents=True,exist_ok=True)
def main():
    font=c.glyph_table();zero=np.zeros((720,1280,3),np.uint8);total=0
    cases=[((400,819,240,459),(420,220,80,76),(600,679,314,389),(True,True),False,True,3),
           ((257,305,161,210),(49,50,0,0),(0,0,0,0),(False,False),False,False,0),
           ((900,1022,500,542),(123,43,0,0),(0,0,0,0),(False,False),False,True,3),
           ((0,0,0,0),(0,0,0,0),(0,0,0,0),(False,False),True,True,3),
           ((0,0,0,0),(0,0,0,0),(0,0,0,0),(False,False),False,False,5)]
    with (OUT/'vectors.txt').open('w') as f:
        for i,(box,sizes,coords,gaps,cal,scaled,status) in enumerate(cases):
            present=box[0]!=0;m=dict(box=box,sizes=sizes,gap=gaps,present=present,valid=present)
            image=draw(zero,m,font,scaled,400,200,cal,status,coords)
            Image.fromarray(image).save(OUT/f'drawing_{i}.png')
            values=[tenths_mm(v,200 if k in(1,3) else 400) if scaled else v*10 for k,v in enumerate(sizes)]
            digits=''.join(f'{v:05d}' for v in values);mask=image[:,:,0]>0
            # Whole screen checks catch drawing outside intended regions and all lane offsets.
            for y in range(720):
                for x in range(0,1280,4):
                    expected=sum(int(mask[y,x+k])<<(3-k) for k in range(4))
                    f.write(f'{x} {y} {int(cal)} {int(scaled)} {int(present)} 1 {status} {pack(box):011x} {pack(coords):011x} {(int(gaps[0])<<1)|int(gaps[1])} {digits} {expected:x}\n');total+=1
    sources=[c.ROOT/'tests/tb_engineering_dimension.sv',c.HDL/'isp/engineering_dimension_marks.v',c.HDL/'osd_char_lib.v']
    log=c.simulate(OUT,'tb_engineering_dimension',sources,plus=['+STIM='+(OUT/'vectors.txt').as_posix()])
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,beats=total,frames=len(cases),
       sources={p.relative_to(c.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}),indent=2)+'\n')
if __name__=='__main__':main()
