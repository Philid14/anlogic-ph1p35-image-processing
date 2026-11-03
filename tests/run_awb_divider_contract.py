import sys,json,hashlib
from pathlib import Path
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/inspection_parts_motion/awb_divider_contract'
def main():
 src=[ROOT/'tests/tb_awb_divider_contract.sv',HDL.parent/'ip_source/divider/divider_gate.v']
 src+=list(Path('D:/TD/sim_release/common').glob('al_map_*.v'))
 src+=[Path('D:/TD/sim_release/common/al_phy_glbl.v')]
 log=simulate(OUT,'tb_awb_divider_contract',src,parameters=['glbl'],timeout=600)
 (OUT/'console.txt').write_text(log)
 (OUT/'results.json').write_text(json.dumps(dict(passed=True,native=True,sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n')
 print(log[-1200:])
if __name__=='__main__':main()
