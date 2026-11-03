import json,hashlib
from vision_sim import ROOT,HDL,simulate
def main():
 out=ROOT/'tmp/track_region_fix/red_equivalence'
 src=[ROOT/'tests/tb_track_red_equivalence.sv',HDL/'vision/vision_source_observer.v',ROOT/'features/color_target/rtl/color_classify.v']
 log=simulate(out,'tb_track_red_equivalence',src,timeout=600)
 assert 'PASS exhaustive16777216' in log
 (out/'console.txt').write_text(log)
 (out/'results.json').write_text(json.dumps(dict(passed=True,colors=16777216,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-900:])
if __name__=='__main__':main()
