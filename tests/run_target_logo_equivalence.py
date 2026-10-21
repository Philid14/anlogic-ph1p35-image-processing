"""Exhaustive ROM and full-raster pixel/control equivalence to frozen WIP mixer."""
from pathlib import Path
import argparse, hashlib, json, subprocess
ROOT=Path(__file__).resolve().parents[1]
HDL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--msim',type=Path);a=ap.parse_args()
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    rel=(HDL/'hdmi_mixer.v').relative_to(ROOT).as_posix()
    old=subprocess.check_output(['git','show','d0342f0:'+rel],cwd=ROOT).decode()
    ref=a.out/'hdmi_mixer_reference.v';ref.write_text(old.replace('module hdmi_mixer #(','module hdmi_mixer_reference #(',1))
    files=[ROOT/'tests/tb_target_logo_equivalence.sv',ref,HDL/'hdmi_mixer.v',HDL/'anlogic_logo_rom.v',HDL/'osd_char_lib.v',HDL/'target/target_logo_palette.v']
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    commands=[['C:/iverilog/bin/iverilog.exe','-g2012','-s','tb_target_logo_equivalence','-o',str(a.out/'test.vvp'),*map(str,files)],['C:/iverilog/bin/vvp.exe',str(a.out/'test.vvp')]]
    if a.msim:
        commands=[[(a.msim/'vlib.exe').as_posix(),'work'],
            [(a.msim/'vlog.exe').as_posix(),'-sv',*[p.as_posix() for p in files]],
            [(a.msim/'vsim.exe').as_posix(),'-c','-quiet','tb_target_logo_equivalence','-do','run -all; quit -f -code 0']]
    for i,cmd in enumerate(commands):
        r=subprocess.run(cmd,cwd=a.out if a.msim else ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
        (a.out/f'stage_{i}.txt').write_bytes(r.stdout)
        assert r.returncode==0 and b'** Fatal:' not in r.stdout and b'** Error:' not in r.stdout,(i,r.stdout.decode(errors='replace')[-2000:])
    assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    assert b'PASS LOGO_EQUIVALENCE' in r.stdout
    (a.out/'summary.json').write_text(json.dumps(dict(passed=True,reference_commit='d0342f05a0e65477ecb2bfef63f7d39599154cc9',source_sha256=before),indent=2)+'\n')
    print(r.stdout.decode())
if __name__=='__main__':main()
