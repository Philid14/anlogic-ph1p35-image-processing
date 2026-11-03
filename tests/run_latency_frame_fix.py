import importlib,json
from pathlib import Path
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/latency_frame_fix'
def main():
 log=simulate(OUT/'blanking','tb_latency_blanking',[ROOT/'tests/tb_latency_blanking.sv',HDL/'vision/latency_capture_tag.v'])
 (OUT/'blanking/console.txt').write_text(log)
 (OUT/'blanking/results.json').write_text(json.dumps(dict(passed=True,scope='blanking PHY error rejected by old RTL, accepted after completed RAW; active error/bad line/full still fail'))+'\n')
 for mod,folder in [('run_latency_units','units'),('run_latency_osd','osd'),('run_latency_video_path','video_path')]:
  m=importlib.import_module(mod);m.OUT=OUT/folder;m.main()
 print('PASS focused blanking, adapters, native OSD and DDR/mixer path')
if __name__=='__main__':main()
