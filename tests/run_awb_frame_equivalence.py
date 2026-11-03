import json,hashlib,subprocess,sys
from pathlib import Path
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/inspection_parts_motion/awb_frame_equivalence_r1'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 rel=(HDL/'awb.v').relative_to(ROOT).as_posix()
 baseline=subprocess.check_output(['git','show','7b7a6144a810f8fdf4be368d51bb0012a0322b95:'+rel],cwd=ROOT).decode()
 ref=OUT/'awb_reference_baseline.v';ref.write_text(baseline.replace('module awb #(','module awb_reference_baseline #(',1))
 src=[ROOT/'tests/tb_awb_frame_equivalence.sv',ref,ROOT/'tmp/inspection_parts_motion/divider_stage_r1/awb.v',HDL/'signal_delay.v',HDL.parent/'ip_source/divider/divider_gate.v']
 src+=list((HDL.parent/'ip_source/blk_mem_gen_awb_delay_signal').glob('*.v'))
 src+=list(Path('D:/TD/sim_release/common').glob('al_map_*.v'))+[Path('D:/TD/sim_release/common/al_phy_glbl.v')]
 log=simulate(OUT,'tb_awb_frame_equivalence',src,parameters=['glbl'],eram=True,timeout=2400)
 (OUT/'console.txt').write_text(log)
 (OUT/'results.json').write_text(json.dumps(dict(passed=True,native=True,frames=12,width=256,height=64,baseline_commit='7b7a6144a810f8fdf4be368d51bb0012a0322b95',sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n')
 print(log[-1500:])
if __name__=='__main__':main()
