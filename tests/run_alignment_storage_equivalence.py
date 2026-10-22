"""Real five-mode/STYLE/Edge RTL, all public outputs against frozen delay chain."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
HDL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--width',type=int,default=68);ap.add_argument('--height',type=int,default=9)
    ap.add_argument('--spatial-only',action='store_true');a=ap.parse_args()
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    rel=(HDL/'isp/edge_control_stream.v').relative_to(ROOT).as_posix()
    old=subprocess.check_output(['git','show','89093f4:'+rel],cwd=ROOT).decode()
    ref=a.out/'edge_control_reference.v';ref.write_text(old.replace('module edge_control_stream #(','module edge_control_reference #(',1))
    files=[ROOT/'tests/tb_alignment_storage.sv',a.source.resolve(),ref,*[HDL/p for p in (
        'isp/rgb_effects_96.v','isp/style_fill_96.v','isp/edge_detect_96.v','isp/gaussian_pair_3x3.v',
        'isp/nms_gradient_pair_3x3.v','isp/edge_link_pair_3x3.v','isp/edge_center_pair_delay.v',
        'isp/edge_temporal_hold.v','edge_status_osd.v','osd_char_lib.v')]]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    cmds=[['C:/iverilog/bin/iverilog.exe','-g2012','-s','tb_alignment_storage',f'-Ptb_alignment_storage.WIDTH={a.width}',f'-Ptb_alignment_storage.HEIGHT={a.height}',f'-Ptb_alignment_storage.SPATIAL_ONLY={int(a.spatial_only)}','-o',str(a.out/'test.vvp'),*map(str,files)],['C:/iverilog/bin/vvp.exe',str(a.out/'test.vvp')]]
    for i,cmd in enumerate(cmds):
        r=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
        (a.out/f'stage_{i}.txt').write_bytes(r.stdout);assert r.returncode==0,(i,r.stdout[-2000:])
    assert b'PASS ALIGNMENT_STORAGE' in r.stdout
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (a.out/'summary.json').write_text(json.dumps(dict(passed=True,reference_commit='89093f4',width=a.width,height=a.height,source_sha256=hashes),indent=2)+'\n')
    print(r.stdout.decode())
if __name__=='__main__':main()
