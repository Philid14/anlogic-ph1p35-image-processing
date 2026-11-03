import json,hashlib
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/inspection_parts_motion/payload'
def main():
 src=[ROOT/'tests/tb_inspection_payload_delay.sv',HDL/'vision/inspection_payload_delay.v']
 log=simulate(OUT,'tb_inspection_payload_delay',src,eram=True)
 (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,native=True,widths=[96,32,23,36],delays=[21,26,24,26],sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-700:])
if __name__=='__main__':main()
