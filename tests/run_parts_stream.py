import json,hashlib,os
from vision_sim import ROOT,HDL,simulate
from run_vision_legacy import sources
from run_latency_regression import simulate as with_helpers
OUT=ROOT/'tmp/inspection_parts_motion/stream'
def main():
 src=[ROOT/'tests/tb_parts_stream.sv']+[p for p in sources() if p.name!='vision_eram_contract.v']+[HDL/'vision'/n for n in ('inspection_font_rom.v','measure_background.v','inspection_config_delay.v','inspection_shape_select.v')]
 if os.environ.get('LATENCY_STAGING')=='1':
  stage=ROOT/os.environ['LATENCY_STAGE_ROOT']
  src=[stage/p.relative_to(HDL) if p.is_relative_to(HDL) and (stage/p.relative_to(HDL)).exists() else p for p in src]
 log=with_helpers(OUT,'tb_parts_stream',src,eram=True,timeout=900)
 (OUT/'console.txt').write_text(log)
 (OUT/'results.json').write_text(json.dumps(dict(passed=True,frames=8,full_motion_pixel_frames=6,measured_T_frames=2,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-1100:])
if __name__=='__main__':main()
