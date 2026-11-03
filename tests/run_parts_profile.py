"""Geometric ground truth masks; constrained T/L sections and rejection cases."""
import json,hashlib
import numpy as np
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/inspection_parts_motion/profile'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 cases=[]
 for nl,nr in ((228,283),(100,155),(356,411)):
  a=np.zeros((256,512),bool);a[64:96,100:412]=1;a[96:192,nl:nr+1]=1
  for flip in (False,True):
   b=a[::-1].copy() if flip else a
   cases.append((b,True,(int(not flip),nl,nr,160 if flip else 96),False))
 # Same envelope remains measurable around an interior reflective patch.
 a=cases[0][0].copy();a[74:84,170:182]=0;cases.append((a,True,(1,228,283,96),False))
 # Rectangles, a three-band rotated T, taper, short bar, disconnected bands.
 a=np.zeros((256,512),bool);a[64:192,100:412]=1;cases.append((a,False,None,False))
 a=np.zeros((256,512),bool);a[64:192,100:156]=1;a[112:144,156:412]=1;cases.append((a,False,None,False))
 a=np.zeros((256,512),bool)
 for y in range(64,192):a[y,100:180+y]=1
 cases.append((a,False,None,False))
 a=cases[0][0].copy();a[64:92]=0;cases.append((a,False,None,False))
 a=cases[0][0].copy();a[120:123]=0;cases.append((a,False,None,False))
 cases.append((cases[0][0],False,None,True))
 cases.append(cases[0]) # recovery after a malformed frame
 with (OUT/'stim.txt').open('w') as f:
  for a,_,_,bad in cases:
   for y in range(256):
    for x in range(0,512,4):
     mask=sum(int(a[y,x+k])<<(3-k) for k in range(4))
     f.write(f'{mask:x} {int(x==508) ^ int(bad and x==0 and y==100)}\n')
 with (OUT/'expected.txt').open('w') as f:
  for a,good,coords,_ in cases:
   yy,xx=np.where(a);box=(int(xx.min()),int(xx.max()),int(yy.min()),int(yy.max()))
   c=0 if coords is None else (coords[0]<<33)|(coords[1]<<22)|(coords[2]<<11)|coords[3]
   b=(box[0]<<33)|(box[1]<<22)|(box[2]<<11)|box[3]
   f.write(f'{int(good)} {c:x} {b:x}\n')
 src=[ROOT/'tests/tb_parts_profile.sv',HDL/'isp/planar_measure_stats.v']
 log=simulate(OUT,'tb_parts_profile',src,plus=['+DIR='+OUT.as_posix()])
 (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,cases=len(cases),sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-1000:])
if __name__=='__main__':main()
