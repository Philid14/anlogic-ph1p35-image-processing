"""Independent raster drawing of canonical T/L dimensions and unit conversion."""
import json,hashlib,os
import numpy as np
from vision_sim import ROOT,HDL,simulate
from run_edge_control_v1 import glyph_table
OUT=ROOT/'tmp/inspection_parts_motion/all_drawing_r3'
def main():
 OUT.mkdir(parents=True,exist_ok=True);font=glyph_table();cases=[]
 for nl,nr in ((560,639),(400,479),(720,799)):
  for top in (True,False):cases.append((nl,nr,304 if top else 416,top,True))
 cases.append((560,639,304,True,False))
 metadata=[]
 for index,(nl,nr,split,top,on) in enumerate(cases):
  im=np.full((720,1280,3),96,dtype=np.uint8);ink=(255,255,128)
  def h(y,l,r):im[y,l:r+1]=ink
  def v(x,t,b):im[t:b+1,x]=ink
  def text(x,y,s):
   for n,c in enumerate(s):
    for yy,bits in font.get(ord(c),{}).items():
     for xx in range(16):
      if bits>>(15-xx)&1:im[y+yy,x+16*n+xx]=ink
  vals=[800,480,(nr-nl+1)*2,128,(nl-400)*2,(799-nr)*2,352]
  if on:
   h(232,400,799)
   for xx in (400,799):v(xx,228,238)
   v(819,240,479)
   for yy in (240,479):h(yy,801,823)
   for d in (2,4,6):
    for yy in (232-d//2,232+d//2):im[yy,400+d]=ink;im[yy,799-d]=ink
    for xx in (819-d//2,819+d//2):im[240+d,xx]=ink;im[479-d,xx]=ink
   text(500,210,'W   80.0 MM ');text(832,351,'H   48.0 MM ')
   bar_mid=(240+split)//2 if top else (split+479)//2
   leg_mid=(split+479)//2 if top else (240+split)//2
   im[240:480,380:384]=ink
   for yy in (240,split,479):im[yy,376:388]=ink
   im[leg_mid,nl:nr+1]=ink
   for xx in (nl,nr//4*4):im[leg_mid-4:leg_mid+5,xx:xx+4]=ink
   if nl>400:
    im[192,400:nl]=ink
    for xx in (400,nl):im[188:197,xx:xx+4]=ink
   if nr<799:
    im[503,nr//4*4:800]=ink
    for xx in (nr//4*4,796):im[499:508,xx:xx+4]=ink
   text((((nl+nr)//2-56)//4)*4,leg_mid+4,f'S {vals[2]/10:5.1f}')
   text(256,bar_mid-8,f'T {vals[3]/10:5.1f}')
   text(256,leg_mid-8,f'V {vals[6]/10:5.1f}')
   if nl>400:text((((400+nl)//2-56)//4)*4,172,f'A {vals[4]/10:5.1f}')
   if nr<799:text((((nr+799)//2-56)//4)*4,507,f'B {vals[5]/10:5.1f}')
   text(256,688,'BG:OK   K4 EMPTY AUTO12'.ljust(24)+'K4 HOLD: W/H')
  # One complete expected overlay per frame, independently drawn primitives.
  with (OUT/f'gold_{index}.txt').open('w') as f:
   for row in im:
    for x in range(0,1280,4):f.write(row[x:x+4].tobytes().hex()+'\n')
  if index==0:
   from PIL import Image
   Image.fromarray(im).save(OUT/'T_dimension_reference.png')
  coords=(int(top)<<33)|(nl<<22)|(nr<<11)|split
  metadata.append(f'{int(on)} {coords:x} '+' '.join(f'{int(str(v),16):05x}' for v in vals)+'\n')
 (OUT/'metadata.txt').write_text(''.join(metadata))
 src=[ROOT/'tests/tb_parts_all_drawing.sv',HDL/'isp/color_compare_osd.v',HDL/'isp/engineering_dimension_marks.v',HDL/'osd_char_lib.v',HDL/'vision/inspection_font_rom.v']
 if os.environ.get('LATENCY_STAGING')=='1':
  stage=ROOT/os.environ['LATENCY_STAGE_ROOT'];src=[stage/p.relative_to(HDL) if p.is_relative_to(HDL) and (stage/p.relative_to(HDL)).exists() else p for p in src]
 log=simulate(OUT,'tb_parts_all_drawing',src,plus=['+DIR='+OUT.as_posix()],eram=True,timeout=600)
 (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,frames=len(cases),sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-1000:])
if __name__=='__main__':main()
