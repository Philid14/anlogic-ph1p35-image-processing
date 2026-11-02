"""Native vendor RAM + independent pre-existing spatial model, all4 hops."""
import json,hashlib
from vision_sim import ROOT,HDL,simulate
from run_edge_quality_v1 import unit_vectors
OUT=ROOT/'tmp/latency_performance/memory'
def main():
 src=[ROOT/'tests/tb_edge_link_pair.v',HDL/'isp/edge_link_pair_3x3.v']
 total=0
 for width in (64,68,72,76,1280):
  folder=OUT/str(width);folder.mkdir(parents=True,exist_ok=True)
  stim,beats=unit_vectors(folder,width)
  log=simulate(folder,'tb_edge_link_pair',src,parameters=[f'-gW={width}'],plus=['+STIM='+stim.as_posix()],eram=True)
  assert 'PASS edge_link' in log
  (folder/'console.txt').write_text(log);total+=beats;print(width,beats,'PASS',flush=True)
 (OUT/'results.json').write_text(json.dumps(dict(passed=True,widths=[64,68,72,76,1280],beats=total,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n')
if __name__=='__main__':main()
