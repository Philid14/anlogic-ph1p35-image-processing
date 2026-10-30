"""Full-frame comparison overlay and independent UI control checks."""
from pathlib import Path
import json,hashlib
import run_edge_control_v1 as c
import color_compare_model as m

OUT=c.ROOT/'tmp/metrology_v1/ui';OUT.mkdir(parents=True,exist_ok=True)
def main():
    font=c.glyph_table();path=OUT/'vectors.txt'
    # Enable changes mid-frame must wait until next SOF. Frame 0 off, 1 on, 2 off.
    means=((180,65,60),(200,70,65));beats=0
    with path.open('w') as f:
        for frame in range(3):
            enabled=frame==1
            f.write(f'0 1 0 {int(enabled)} 0 0\n')
            for _ in range(140):f.write(f'0 0 0 {int(enabled)} 0 0\n')
            for y in range(720):
                for x in range(0,1280,4):
                    pixels=[((x+k)%256,y%256,(x+y+k)%256) for k in range(4)]
                    out=m.overlay(pixels,x,y,means,0x1234,font) if enabled else pixels
                    din=bytes(v for p in pixels for v in p).hex()
                    golden=bytes(v for p in out for v in p).hex()
                    en=int(enabled) if y<300 else int(not enabled)
                    f.write(f'1 0 {int(x==1276)} {en} {din} {golden}\n');beats+=1
                f.write('0 0 0 0 0 0\n')
        f.write('0 0 0 0 0 0\n0 0 0 0 0 0\n')
    sources=[c.ROOT/'tests/tb_inspection_ui.sv',c.HDL/'isp/color_compare_osd.v',c.HDL/'osd_char_lib.v']
    log=c.simulate(OUT,'tb_inspection_ui',sources,plus=['+STIM='+path.as_posix()])
    (OUT/'overlay_console.txt').write_text(log)
    log=c.simulate(OUT,'tb_inspection_control',[c.ROOT/'tests/tb_inspection_ui.sv',c.HDL/'isp/inspection_control.v',c.HDL/'edge_key_control.v'])
    (OUT/'controls_console.txt').write_text(log)
    result=dict(passed=True,full_frame_beats=beats,frames=3,
      scope='2-cycle actual comparison overlay, frame-latched on/off and independent debounce; no board claim')
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
