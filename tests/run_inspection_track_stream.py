import json,hashlib
from vision_sim import ROOT,HDL,simulate
from run_vision_legacy import sources
OUT=ROOT/'tmp/inspection_shape_track/track_stream'
def main():
 src=[ROOT/'tests/tb_inspection_track_stream.sv']+[p for p in sources() if p.name!='vision_eram_contract.v']+[HDL/'vision/inspection_font_rom.v',HDL/'vision/measure_background.v',HDL/'vision/inspection_config_delay.v',HDL/'vision/inspection_shape_select.v']
 log=simulate(OUT,'tb_inspection_track_stream',src,eram=True)
 (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n');print(log[-1000:])
if __name__=='__main__':main()
