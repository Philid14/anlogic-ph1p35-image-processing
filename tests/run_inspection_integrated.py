"""720p production V5/compact-font path, independent baseline pixels plus BG UI.

Post-AWB/UI boundaries. No background learn request in these nine mode/CM
frames; learned classifier is exhaustively checked separately with real ERAM.
"""
import json,hashlib
from vision_sim import ROOT,HDL,simulate
from run_vision_legacy import sources
from run_edge_control_v1 import glyph_table
OUT=ROOT/'tmp/inspection_shape_track/integrated'
def vectors():
 OUT.mkdir(parents=True,exist_ok=True);font=glyph_table();x=y=frame=0;ui=0;count=previous=0;words=0
 stim=OUT/'stim.txt';pack=OUT/'pack.txt'
 with (ROOT/'tmp/ruler_cm/stream_r1/stim.txt').open() as inp,stim.open('w') as out,pack.open('w') as pf:
  for line in inp:
   fields=line.split();v,u,l=map(int,fields[:3]);cfg=int(fields[3],16)
   if u:x=y=0;ui=int(fields[6]);frame+=1
   current=int(fields[5],16)
   if v:
    if ui&2 and not ui&8 and 560<=y<576:
     rgb=bytes.fromhex(fields[4]);pixels=bytearray.fromhex(fields[5]);message='BG:NEED K4 EMPTY CUT'.ljust(48)
     for lane in range(4):
      px=x+lane
      if 256<=px<1024:
       c=ord(message[(px-256)//16]);bits=font.get(c,{}).get(y-560,0)
       if bits>>(15-((px-256)%16))&1:pixels[lane*3:lane*3+3]=bytes((16,16,48) if pixels[lane*3+1]>=128 else (255,255,128))
     fields[5]=pixels.hex();current=int(fields[5],16)
    x+=4
    if l:x=0;y+=1
    if count==1:word=((previous<<32)|(current>>64))&((1<<128)-1)
    elif count==2:word=((previous&((1<<64)-1))<<64)|(current>>32)
    elif count==3:word=((previous&((1<<32)-1))<<96)|current
    if count:pf.write(f'{word:032x}\n');words+=1
    previous=current;count=(count+1)&3
   else:count=0
   out.write(' '.join(fields)+'\n')
 return stim,pack,words
def main():
 stim,pack,words=vectors();print('V5 vectors ready',words,flush=True)
 src=[ROOT/'tests/tb_inspection_integrated_stream.sv']+[p for p in sources() if p.name!='vision_eram_contract.v']+[HDL/'vision/inspection_font_rom.v',HDL/'vision/measure_background.v']
 log=simulate(OUT,'tb_inspection_integrated_stream',src,parameters=['-g'+v for v in ('WIDTH=1280','HEIGHT=720','COMPARE=1','INSPECTION=1','AUTO_DIMENSION=1','USABILITY_ENABLE=1','INSPECTION_V4=1')],plus=[f'+STIM={stim.as_posix()}',f'+PACK={pack.as_posix()}',f'+WORDS={words}'],eram=True,timeout=1000)
 (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,frames=9,beats=2073600,words=words,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-900:])
if __name__=='__main__':main()
