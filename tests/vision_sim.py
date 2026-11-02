"""Native ModelSim runner. Actual Anlogic ERAM/GSR model, no behavior substitute."""
from pathlib import Path
import subprocess,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
HDL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
MSIM=Path('D:/modelsim/modelsim_ase/win32aloem')
def simulate(out,top,sources,plus=(),parameters=(),eram=False,timeout=600):
    out.mkdir(parents=True,exist_ok=True);files=list(sources);tops=[];data=[]
    if eram:
        files +=[Path('D:/TD/sim_release/ph1p/ph1p_logic_eram.v'),Path('D:/TD/sim_release/ph1p/ph1p_phy_gsr.v')]
        tops=['PH1P_PHY_GSR']
        for name in ('vision_logo_index.dath','vision_logo_palette.dath','inspection_font.dath'):
            source=HDL/'vision'/name;shutil.copy2(source,out/name);data.append(source)
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+data}
    commands=[[(MSIM/'vlib.exe').as_posix(),'work'],
       [(MSIM/'vlog.exe').as_posix(),'-sv',*[p.as_posix() for p in files]],
       [(MSIM/'vsim.exe').as_posix(),'-c','-quiet',top,*tops,*parameters,*plus,'-do','onerror {quit -f -code 1}; onbreak {quit -f -code 1}; run -all; quit -f -code 0']]
    for i,cmd in enumerate(commands):
        r=subprocess.run(cmd,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        (out/f'stage_{i}.txt').write_bytes(r.stdout)
        assert r.returncode==0 and b'** Fatal:' not in r.stdout and b'** Error:' not in r.stdout,(i,r.stdout.decode(errors='replace')[-2500:])
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+data}
    (out/'SIM_SOURCE_MANIFEST.json').write_text(json.dumps(hashes,indent=2)+'\n')
    return r.stdout.decode(errors='replace')
