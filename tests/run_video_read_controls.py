"""Actual native FIFO/unpacker plus aligned mixer, full 1280-pixel line."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--msim',type=Path,required=True)
    ap.add_argument('--negative-control',action='store_true');a=ap.parse_args()
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    h=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
    files=[ROOT/'tests/tb_video_read_controls.sv',h/'target/video_read_controls.v',h/'target/target_logo_palette.v',h/'video_out.v',h/'hdmi_mixer.v',h/'osd_char_lib.v',h/'isp/fifo_event_counter.v',*sorted((h.parent/'ip_source/w128_d512_fifo').glob('*.v'))]
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    cmds=[[(a.msim/'vlib.exe').as_posix(),'work'],[(a.msim/'vlog.exe').as_posix(),'-sv',*[p.as_posix() for p in files]],[(a.msim/'vsim.exe').as_posix(),'-c','-quiet',*(['-gALIGN_ENABLE=0'] if a.negative_control else []),'tb_video_read_controls','-do','run -all; quit -f -code 0']]
    for i,cmd in enumerate(cmds):
        r=subprocess.run(cmd,cwd=a.out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (a.out/f'stage_{i}.txt').write_bytes(r.stdout)
        assert r.returncode==0 and b'** Error:' not in r.stdout and (b'** Fatal:' not in r.stdout or (i==2 and a.negative_control)),(i,r.stdout.decode(errors='replace')[-2000:])
    assert (b'** Fatal: pixel x=' in r.stdout) if a.negative_control else (b'PASS VIDEO_READ_CONTROLS' in r.stdout)
    assert hashes=={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (a.out/'summary.json').write_text(json.dumps(dict(passed=True,negative_control=a.negative_control,source_sha256=hashes),indent=2)+'\n')
    print(r.stdout.decode()[-700:])
if __name__=='__main__':main()
