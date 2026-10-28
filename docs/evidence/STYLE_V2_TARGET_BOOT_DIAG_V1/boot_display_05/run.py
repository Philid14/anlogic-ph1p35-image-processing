import subprocess,json
from pathlib import Path
p=Path(__file__).resolve().parent;m=Path("D:/modelsim/modelsim_ase/win32aloem")
for i,cmd in enumerate([[str(m/'vlib.exe'),'work'],[str(m/'vlog.exe'),'-sv',*json.loads((p/'files.json').read_text())],[str(m/'vsim.exe'),'-c','-quiet','tb_target_boot_display','-do','onerror {quit -code 2}; run -all; quit -f -code 0']]):
 with (p/f'stage_{i}.txt').open('wb') as log:r=subprocess.run(cmd,cwd=p,stdout=log,stderr=subprocess.STDOUT,timeout=300)
 print(i,r.returncode,flush=True);assert r.returncode==0
