import json,hashlib
import numpy as np
from vision_sim import ROOT,HDL,simulate
from run_edge_control_v1 import glyph_table
OUT=ROOT/'tmp/inspection_shape_track/drawing'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 image=np.full((720,1280,3),96,dtype=np.uint8);ink=(255,255,128)
 image[292,500:600]=ink
 for x in (500,599):image[288:299,x]=ink
 image[349,549:600]=ink;image[346:353,549]=ink
 for yy,xx in ((348,597),(350,597),(347,595),(351,595)):image[yy,xx]=ink
 font=glyph_table()
 def text(x,y,s):
  for n,c in enumerate(s):
   for yy,bits in font.get(ord(c),{}).items():
    for xx in range(16):
     if bits>>(15-xx)&1:image[y+yy,x+16*n+xx]=ink
 text(452,270,'D   10.0 MM ')
 text(632,341,'R    5.0 MM ')
 text(256,560,'BG:OK   K4 EMPTY AUTO12')
 gold=OUT/'gold.txt'
 with gold.open('w') as f:
  for row in image:
   for x in range(0,1280,4):f.write(row[x:x+4].tobytes().hex()+'\n')
 src=[ROOT/'tests/tb_inspection_drawing.sv',HDL/'isp/color_compare_osd.v',HDL/'isp/engineering_dimension_marks.v',HDL/'osd_char_lib.v',HDL/'vision/inspection_font_rom.v']
 log=simulate(OUT,'tb_inspection_drawing',src,plus=['+GOLD='+gold.as_posix()],eram=True)
 (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src},gold_sha256=hashlib.sha256(gold.read_bytes()).hexdigest()),indent=2)+'\n');print(log[-1000:])
if __name__=='__main__':main()



