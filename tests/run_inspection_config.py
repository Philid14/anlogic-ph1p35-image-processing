import json,hashlib
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/inspection_shape_track/config'
def main():
 src=[ROOT/'tests/tb_inspection_config_delay.sv',HDL/'vision/inspection_config_delay.v']
 log=simulate(OUT,'tb_inspection_config_delay',src,eram=True)
 (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-800:])
if __name__=='__main__':main()
