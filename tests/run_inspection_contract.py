"""Reuse independent160-frame geometry and240 formatter vectors in native RTL."""
import json,hashlib
import run_planar_measure_v1 as old
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/inspection_shape_track/contract'
def main():
 old.OUT=OUT;OUT.mkdir(parents=True,exist_ok=True);all_sources=[]
 def sim(directory,top,sources,params=(),plus=()):
  all_sources.extend(sources)
  return simulate(directory/top,top,sources,plus=plus)
 old.c.simulate=sim;old.main()
 result=json.loads((OUT/'results.json').read_text());result['sources']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in all_sources}
 (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result['frames'],result['stats_cycles'],result['metric_snapshots'],'PASS')
if __name__=='__main__':main()
