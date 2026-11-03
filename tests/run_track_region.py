"""Independent software raster model + native RTL, including legacy failure evidence.

Synthetic camera RGB only: the phone photograph is never treated as sensor RGB.
"""
import json,hashlib,random,subprocess,sys
from vision_sim import ROOT,HDL,simulate

OUT=ROOT/'tmp/track_region_fix/region'
OBSERVER=HDL/'vision/vision_source_observer.v'

def red(p,relative=True):
 r,g,b=p;c=max(p)-min(p)
 return r>=max(g,b) and 2*abs(g-b)<=c and c>=24 and r>=32 and (not relative or max(g,b)<=r-(r>>2))

def region(im):
 best=None;chain=None;prev=None
 for y,row in enumerate(im):
  runs=[];start=None
  for bx in range(len(row)//4+1):
   hit=bx<len(row)//4 and sum(red(p) for p in row[bx*4:bx*4+4])>=3
   if hit and start is None:start=bx
   if not hit and start is not None:runs.append((start,bx-1));start=None
  span=max(runs,key=lambda z:z[1]-z[0],default=None)
  if span is None or span[1]-span[0]+1<2:chain=None;prev=None;continue
  l,r=span;n=r-l+1
  if chain and l<=prev[1]+1 and r+1>=prev[0]:
   x0,x1,y0,_,area=chain;chain=(min(x0,l),max(x1,r),y0,y,area+n)
  else:chain=(l,r,y,y,n)
  prev=span
  if y-chain[2]>=3 and chain[4]>=16 and (best is None or chain[4]>best[4]):best=chain
 if best:
  l,r,t,b,n=best;return [l*4,r*4+3,t,b,n*4]
 return [0]*5

def legacy(im):
 points=[(x,y) for y,row in enumerate(im) for x,p in enumerate(row) if red(p,False)]
 if len(points)<64:return [0]*5
 return [min(p[0] for p in points),max(p[0] for p in points),min(p[1] for p in points),max(p[1] for p in points),len(points)]

def scenes(w,h):
 rng=random.Random(83117);seq=[]
 for f in range(16):
  im=[[tuple((208,192,176) if f==1 else (160,164,160)) for x in range(w)] for y in range(h)]
  # One complete red block per row with gaps: old global count passes 64.
  for y in range(h):
   x=((y*17)%(w//4))*4
   for k in range(4):im[y][x+k]=(200,24,24)
  # Disconnected short strokes, none >=4 consecutive rows.
  for y in range(2,h-2,19):
   for x in range(4,16):im[y][x]=(200,24,24);im[y+1][x]=(200,24,24)
  if f in (2,3,4,5,6,7,9,10,11,12,13,14,15):
   left=40 if f in (2,3,4) else 60 if f==5 else w-32 if f==6 else 0 if f==7 else 48
   top=32 if f<9 else h-28 if f==9 else 0 if f==10 else 40
   for y in range(max(0,top-2),min(h,top+26)):
    for x in range(max(0,left-8),min(w,left+32)):im[y][x]=(160,164,160)
   for y in range(top,min(top+24,h)):
    for x in range(left,min(left+24,w)):im[y][x]=(224,32,32)
   if f==11:
    # A separate smaller red item must not merge with the main object.
    for y in range(8,16):
     for x in range(w-16,w-8):im[y][x]=(210,20,20)
   if f==12:
    for y in range(top,top+24):
     for x in range(left,left+24):
      if (x-left-11.5)**2+(y-top-11.5)**2>144:im[y][x]=(160,164,160)
   if f==13:
    # Isolated holes: may shorten row runs; report model limitations honestly.
    for _ in range(8):im[rng.randrange(top,top+24)][rng.randrange(left,left+24)]=(240,240,240)
   if f==14:
    # Dark red should still pass; this is not a blanket brightness increase.
    for y in range(top,top+24):
     for x in range(left,left+24):im[y][x]=(64,20,20)
   if f==15:
    # One red-outlier pixel in each otherwise neutral block must not expand bbox.
    for y in range(h):
     for x in range(0,w,4):
      if not(left<=x<left+24 and top<=y<top+24):im[y][x]=(255,0,0)
  seq.append(im)
 return seq

def main():
 full='--full' in sys.argv;out=OUT.parent/'region_full' if full else OUT
 w,h=(1280,720) if full else (160,120)
 out.mkdir(parents=True,exist_ok=True);imseq=scenes(w,h);report=[]
 if full:
  imseq=imseq[:5]
  im=[[(160,164,160) for _ in range(w)] for _ in range(h)]
  for y in range(h-24,h):
   for x in range(w-24,w):im[y][x]=(224,32,32)
  imseq.append(im)
  imseq.append([[(224,32,32) for _ in range(w)] for _ in range(h)])
 stim=out/'stim.txt'
 with stim.open('w') as o:
  for f,im in enumerate(imseq):
   new=region(im);old=legacy(im);report.append(dict(frame=f,old=old,new=new))
   o.write(' '.join(map(str,new+[f%2]))+'\n')
   for row in im:
    for x in range(0,w,4):o.write(''.join(bytes(p).hex() for p in row[x:x+4])+'\n')
 assert report[0]['old'][4]>=64 and report[0]['new'][4]==0
 assert report[1]['old'][:4]==[0,w-1,0,h-1] and report[1]['new'][4]==0
 for f in (2,3,4):assert report[f]['new']==[40,63,32,55,576]
 src=[ROOT/'tests/tb_track_region.sv',OBSERVER,HDL/'vision/vision_motion_grid.v']+[ROOT/'features/color_target/rtl'/n for n in ('color_classify.v','color_target_mask_stats.v','color_target_track.v','color_target_track_guard.v')]
 log=simulate(out,'tb_track_region',src,parameters=[f'-gWIDTH={w}',f'-gHEIGHT={h}'],plus=['+STIM='+stim.as_posix()],eram=True,timeout=900)
 (out/'console.txt').write_text(log)
 if not full:
  tight=simulate(out/'tight','tb_track_region',src,parameters=['-gTIGHT=1'],plus=['+STIM='+stim.as_posix()],eram=True)
  (out/'tight/console.txt').write_text(tight)
 # Prove the preceding implementation fails exactly the same new test vector.
 original=subprocess.check_output(['git','show','4d0f779cefd680363b8a3f0d4d5c33a42d81197f:'+OBSERVER.relative_to(ROOT).as_posix()],cwd=ROOT)
 oldfile=out/'legacy_observer.v';oldfile.write_bytes(original)
 try:
  simulate(out/'legacy_failure','tb_track_region',[oldfile if p==OBSERVER else p for p in src],parameters=[f'-gWIDTH={w}',f'-gHEIGHT={h}'],plus=['+STIM='+stim.as_posix()],eram=True)
 except AssertionError as exc:
  message=str(exc);assert 'bbox=' in message,message
  (out/'legacy_failure.txt').write_text(message)
 else:raise AssertionError('Old observer unexpectedly passed noise test')
 (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
 (out/'results.json').write_text(json.dumps(dict(passed=True,width=w,height=h,frames=len(imseq),legacy_reproduced=True,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-1200:])
if __name__=='__main__':main()
