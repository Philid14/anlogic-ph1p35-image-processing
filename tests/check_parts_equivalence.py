"""Finite-domain arithmetic proofs for actual MAIN ROI/counter invariants."""
import hashlib,json
from pathlib import Path
import numpy as np
from vision_sim import ROOT,HDL
def main():
 pairs=0
 for outer in range(1280):
  left=np.arange(outer,1280);q=(left//4)*4
  old=np.maximum(q,outer);new=(q//4)*4+np.where(q//4==outer//4,outer%4,0)
  assert np.array_equal(old,new)
  right=np.arange(outer+1);q=(right//4)*4+3
  old=np.minimum(q,outer);new=(q//4)*4+np.where(q//4==outer//4,outer%4,3)
  assert np.array_equal(old,new);pairs+=left.size+right.size
 a=np.arange(320)[:,None];b=np.arange(320)[None,:];delta=(a-b)%512
 assert np.array_equal((delta==0)|(delta==1)|(delta==511),abs(a-b)<=1)
 cases=0
 for count in range(67):
  for run in range(4):
   for mask in range(16):
    old=count;r=run;inc=0
    for lane in range(4):
     if mask>>(3-lane)&1:
      if r<3:
       r+=1;n=3 if r==3 else 0
      else:n=1
      if old<64:old+=n
      inc+=n
     else:r=0
    new=min(64,min(count,64)+inc)
    assert min(old,64)==new and (old>=6)==(new>=6)
    for area in (0,1,32,63,64):assert min(64,area+old)==min(64,area+new)
    cases+=1
 for n in range(721):assert (min(n,3)>=3)==(n>=3)
 for first in range(385):
  for second in range(385):assert (min(first,6)==6 and min(second,6)==6)==(first>=6 and second>=6)
 sources=[Path(__file__).resolve(),HDL/'isp/planar_measure_stats.v',HDL/'isp/color_compare_osd.v']
 result=dict(passed=True,scope='Software finite-domain proof, not native RTL or board evidence',clamp_pairs=pairs,tolerance_pairs=320*320,counter_cases=cases,band_height_pairs=385*385,
  assumptions='qualified chosen intervals contribute to full envelope; source bounds0..1279; MIN_ROW6/MIN_AREA64, MIN_ROWS3',
  sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
 out=ROOT/'tmp/inspection_parts_motion/equivalence';out.mkdir(parents=True,exist_ok=True);(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
