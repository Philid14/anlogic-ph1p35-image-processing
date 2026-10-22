"""Full-raster equivalence and actual-output age of the glyph pipeline."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
HDL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--msim',type=Path,required=True);a=ap.parse_args()
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    rel=(HDL/'target/target_display_commit.v').relative_to(ROOT).as_posix()
    old=subprocess.check_output(['git','show','4cc38ed:'+rel],cwd=ROOT).decode()
    ref=a.out/'target_display_commit_reference.v';ref.write_text(old.replace('module target_display_commit #(','module target_display_commit_reference #(',1))
    files=[ROOT/'tests/tb_target_display_pipeline.sv',a.source.resolve(),ref,HDL/'osd_char_lib.v',ROOT/'features/color_target/rtl/color_target_overlay.v',ROOT/'features/color_target/rtl/color_target_text_overlay.v']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    commands=[[(a.msim/'vlib.exe').as_posix(),'work'],[(a.msim/'vlog.exe').as_posix(),'-sv',*[p.as_posix() for p in files]],[(a.msim/'vsim.exe').as_posix(),'-c','-quiet','tb_target_display_pipeline','-do','run -all; quit -f -code 0']]
    for i,cmd in enumerate(commands):
        r=subprocess.run(cmd,cwd=a.out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
        (a.out/f'stage_{i}.txt').write_bytes(r.stdout)
        assert r.returncode==0 and b'** Fatal:' not in r.stdout and b'** Error:' not in r.stdout,(i,r.stdout[-2000:])
    assert b'PASS DISPLAY_PIPELINE' in r.stdout
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (a.out/'summary.json').write_text(json.dumps(dict(passed=True,reference_commit='4cc38ed',source_sha256=hashes),indent=2)+'\n')
    print(r.stdout.decode()[-600:])
if __name__=='__main__':main()
