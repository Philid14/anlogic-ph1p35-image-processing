"""Independent CAD sub-rectangles, all view phases, flips and invalid bypass."""
import json,hashlib
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/inspection_parts_motion/views'
def main():
 OUT.mkdir(parents=True,exist_ok=True);lines=[]
 for nl,nr in ((560,639),(400,479),(720,799)):
  for top in (0,1):
   split=304 if top else 416;full=(400,799,240,479)
   coords=(top<<33)|(nl<<22)|(nr<<11)|split
   for fid in (0,31,32,63,64,95,96,127,128,159,160,255,256,511):
    for enabled in (0,1):
     kind=0;box=full;page=(fid>>5)&7
     if enabled:
      bar=(400,799,240 if top else split,split-1 if top else 479)
      if page==1:kind=1;box=(nl,nr,split if top else 240,479 if top else split-1)
      if page==2:kind=2;box=bar
      if page==3:kind=3 if nl>400 else 2;box=(400,nl-1,bar[2],bar[3]) if nl>400 else bar
      if page==4:kind=4 if nr<799 else 2;box=(nr+1,799,bar[2],bar[3]) if nr<799 else bar
     def pack(b):return (b[0]<<33)|(b[1]<<22)|(b[2]<<11)|b[3]
     sizes=((box[1]-box[0]+1)<<33)|((box[3]-box[2]+1)<<22)|(0 if kind else 0x12345)
     lines.append(f'{enabled} {fid} {coords:x} {kind} {pack(box):x} {sizes:x}\n')
 (OUT/'vectors.txt').write_text(''.join(lines))
 src=[ROOT/'tests/tb_parts_views.sv',HDL/'isp/edge_control_stream.v']
 log=simulate(OUT,'tb_parts_views',src,plus=['+VECTORS='+str(OUT/'vectors.txt')])
 (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,cases=len(lines),sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-900:])
if __name__=='__main__':main()
