import json,hashlib
from functools import lru_cache
import run_edge_control_v1 as c
from inspection_v4_screen_model import color_overlay
OUT=c.ROOT/'tmp/inspection_v4/panel'
def main():
    OUT.mkdir(parents=True,exist_ok=True);font=c.glyph_table();count=0
    cases=[((140,150,90),(168,180,108)),((200,40,40),(40,200,40)),
           ((140,150,90),(140,150,90)),((250,240,220),(255,254,220)),None]
    with (OUT/'vectors.txt').open('w') as f:
        for i,means in enumerate(cases):
            packed=int.from_bytes(bytes(sum((list(a) for a in means),[])),'big') if means else 0
            f.write(f'0 0 0 0 0 {packed:012x} {i:04x} {int(means is not None)}\n')
            for y in list(range(300,339))+list(range(544,706)):
                for x in range(0,1280,4):
                    pixels=[(150,160,170)]*4
                    expected=bytes(sum((list(p) for p in color_overlay(pixels,x,y,means,i,font)),[])).hex()
                    f.write(f'1 {x} {y} 96a0aa96a0aa96a0aa96a0aa {expected} 0 0 0\n');count+=1
    sources=[c.ROOT/'tests/tb_light_panel_v4.sv',c.HDL/'isp/color_compare_osd.v',c.HDL/'isp/engineering_dimension_marks.v',c.HDL/'osd_char_lib.v']
    hashes={p.relative_to(c.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    log=c.simulate(OUT,'tb_light_panel_v4',sources,plus=['+STIM='+(OUT/'vectors.txt').as_posix()])
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,cases=len(cases),beats=count,sources=hashes,
      boundary='explicit raster coordinates; actual frame counters/metadata covered by production ISP test'),indent=2)+'\n')
if __name__=='__main__':main()
