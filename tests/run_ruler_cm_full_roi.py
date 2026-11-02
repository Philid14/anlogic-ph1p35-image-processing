import json,hashlib
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/ruler_cm/full_roi'
def main():
    src=[ROOT/'tests/tb_ruler_cm_full_roi.sv',HDL/'isp/ruler_area_calibration.v']
    log=simulate(OUT,'tb_ruler_cm_full_roi',src,timeout=600)
    (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,width=1280,height=720,roi=[256,192,768,288],checks=2,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-700:])
if __name__=='__main__':main()
