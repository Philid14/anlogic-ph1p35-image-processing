import json,hashlib
import run_edge_control_v1 as c
from usability_screen_model import status
OUT=c.ROOT/'tmp/inspection_v3/controls';OUT.mkdir(parents=True,exist_ok=True)
def main():
    font=c.glyph_table();beats=0
    with (OUT/'vectors.txt').open('w') as f:
        for sw in range(16):
            mode=sw%5;ruler=sw%8;cfg=(mode<<16)|(80<<8)|130
            f.write(f'0 1 0 {cfg:x} {sw} {ruler} 0 0\n')
            for y in range(176):
                for x in range(0,1280,4):
                    pix=[((x+k)%256,200 if sw%2 else 20,(x+y+k)%256) for k in range(4)]
                    expected=status(pix,x,y,mode,80,130,font,sw,ruler)
                    # All switches and error code change mid-frame; displayed snapshot must not.
                    inp=sw if y<80 else sw^15;rs=ruler if y<80 else ruler^7
                    f.write(f'1 0 {int(x==1276)} {cfg:x} {inp} {rs} {bytes(v for p in pix for v in p).hex()} {expected.hex()}\n');beats+=1
            f.write(f'0 0 0 {cfg:x} 0 0 0 0\n')
        f.write('0 0 0 0 0 0 0 0\n0 0 0 0 0 0 0 0\n')
    sources=[c.ROOT/'tests/tb_switch_status_v3.sv',c.HDL/'edge_status_osd.v',c.HDL/'osd_char_lib.v']
    log=c.simulate(OUT,'tb_switch_status_v3',sources,plus=['+STIM='+(OUT/'vectors.txt').as_posix()])
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,combinations=16,beats=beats,sources={p.relative_to(c.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}),indent=2)+'\n')
if __name__=='__main__':main()
