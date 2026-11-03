"""Independent paged CAD dimension raster, native font/units and old D/R."""
import json,hashlib
import numpy as np
from vision_sim import ROOT,HDL,simulate
from run_edge_control_v1 import glyph_table
OUT=ROOT/'tmp/inspection_parts_motion/drawing'
def main():
 OUT.mkdir(parents=True,exist_ok=True);font=glyph_table();cases=[];metadata=[]
 for kind in range(5):cases.append((560,639,True,kind,True,False))
 cases +=[(560,639,False,1,True,False),(560,639,False,2,True,False),
          (400,479,True,3,True,False),(400,479,True,4,True,False),
          (720,799,False,3,True,False),(720,799,False,4,True,False),
          (560,639,True,0,False,False),(560,639,True,0,True,True)]
 for index,(nl,nr,top,kind,on,round_mode) in enumerate(cases):
  split=304 if top else 416;bar=(400,799,240 if top else split,split-1 if top else 479)
  box=(400,799,240,479)
  if kind==1:box=(nl,nr,split if top else 240,479 if top else split-1)
  if kind==2:box=bar
  if kind==3:
   if nl==400:kind=2;box=bar
   else:box=(400,nl-1,bar[2],bar[3])
  if kind==4:
   if nr==799:kind=2;box=bar
   else:box=(nr+1,799,bar[2],bar[3])
  if round_mode:box=(500,599,300,399)
  xl,xr,yt,yb=box;w=xr-xl+1;h=yb-yt+1
  values=(w*2,w if round_mode else h*2)
  labels=('D','R') if round_mode else ('S','V') if kind==1 else ('W','T') if kind==2 else ('A','T') if kind==3 else ('B','T') if kind==4 else ('W','H')
  im=np.full((720,1280,3),96,dtype=np.uint8);ink=(255,255,128)
  def horizontal(y,left,right):im[y,left:right+1]=ink
  def vertical(x,top,bottom):im[top:bottom+1,x]=ink
  def text(x,y,s):
   for n,c in enumerate(s):
    for yy,bits in font.get(ord(c),{}).items():
     for xx in range(16):
      if bits>>(15-xx)&1:im[y+yy,x+16*n+xx]=ink
  if on:
   horizontal(yt-8,xl,xr)
   for xx in (xl,xr):vertical(xx,yt-12,yt-2)
   if round_mode:
    cx=(xl+xr)//2;cy=(yt+yb)//2;horizontal(cy,cx,xr);vertical(cx,cy-3,cy+3)
    for d in (2,4):
     for yy in (cy-d//2,cy+d//2):im[yy,xr-d]=ink
   else:
    vertical(xr+20,yt,yb)
    for yy in (yt,yb):horizontal(yy,xr+2,xr+24)
    for d in (2,4,6):
     for yy in (yt-8-d//2,yt-8+d//2):im[yy,xl+d]=ink;im[yy,xr-d]=ink
     for xx in (xr+20-d//2,xr+20+d//2):im[yt+d,xx]=ink;im[yb-d,xx]=ink
   text((((xl+xr)//2-96)//4)*4,yt-30,f'{labels[0]} {values[0]/10:6.1f} MM ')
   text(((xr+36)//4)*4,(yt+yb)//2-8,f'{labels[1]} {values[1]/10:6.1f} MM ')
   msg='BG:OK   K4 EMPTY AUTO12'.ljust(24)+'K4 HOLD: '+('D/R' if round_mode else 'W/H')
   if kind:msg=msg.ljust(37)+'VIEW:'+labels[0]+'/'+labels[1]
   text(256,560,msg)
  with (OUT/f'gold_{index}.txt').open('w') as f:
   for row in im:
    for x in range(0,1280,4):f.write(row[x:x+4].tobytes().hex()+'\n')
  if index<5:
   from PIL import Image
   preview=np.full_like(im,96);preview[240:304,400:800]=20;preview[304:480,560:640]=20
   mask=np.any(im!=96,axis=2);preview[mask]=im[mask]
   Image.fromarray(preview).save(OUT/f'T_view_{index}.png')
  packed=(xl<<33)|(xr<<22)|(yt<<11)|yb;sizes=(w<<33)|(h<<22)
  metadata.append(f'{int(on)} {int(round_mode)} {kind} {packed:x} {sizes:x} '+ ' '.join(f'{int(str(v),16):05x}' for v in values)+'\n')
 (OUT/'metadata.txt').write_text(''.join(metadata))
 src=[ROOT/'tests/tb_parts_drawing.sv',HDL/'isp/color_compare_osd.v',HDL/'isp/engineering_dimension_marks.v',HDL/'osd_char_lib.v',HDL/'vision/inspection_font_rom.v']
 log=simulate(OUT,'tb_parts_drawing',src,plus=['+DIR='+OUT.as_posix(),'+FRAMES='+str(len(cases))],eram=True,timeout=600)
 (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,frames=len(cases),sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-1000:])
if __name__=='__main__':main()
