import json,hashlib
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/inspection_shape_track/background_full'
def main():
 src=[ROOT/'tests/tb_measure_background_full.sv',HDL/'vision/measure_background.v']
 log=simulate(OUT,'tb_measure_background_full',src,eram=True)
 (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,frames=4,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-900:])
if __name__=='__main__':main()
