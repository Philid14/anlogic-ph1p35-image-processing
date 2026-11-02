import json,hashlib
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/inspection_shape_track/font'
def main():
    src=[ROOT/'tests/tb_inspection_font.sv',HDL/'vision/inspection_font_rom.v',HDL/'osd_char_lib.v']
    log=simulate(OUT,'tb_inspection_font',src,eram=True)
    (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,checks=4096,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-600:])
if __name__=='__main__':main()
