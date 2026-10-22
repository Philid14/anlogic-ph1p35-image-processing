"""Actual MAIN/FIFO/MC/guard/shared-font/final-output regression."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from style_target_sim_inputs import prepare_logo_inputs,manifest_name
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--msim',type=Path,required=True)
    ap.add_argument('--display-source',type=Path,help='Explicit isolated display experiment; omit for production validation')
    a=ap.parse_args();a.out=a.out.resolve();a.out.mkdir(exist_ok=False,parents=True)
    MSIM=a.msim.resolve()
    assert all((MSIM/name).is_file() for name in ('vlib.exe','vlog.exe','vsim.exe'))
    h=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source';ip=h.parent/'ip_source'
    files=[ROOT/'tests/tb_target_frame_system_final.sv',ROOT/'tests/tb_target_progress.sv',
        *sorted((h/'target').glob('*.v')),*sorted((ROOT/'features/color_target/rtl').glob('*.v')),
        *[h/p for p in ('video_in.v','video_out.v','mc_to_user_interface.v','data_96bit_to_128bit.v',
            'isp/fifo_event_counter.v','vtc/uivtc.v','hdmi_mixer.v','osd_char_lib.v','anlogic_logo_rom.v')]]
    for folder in ('w128_d512_fifo','w155_d512_fifo'):files+=sorted((ip/folder).glob('*.v'))
    if a.display_source:
        files=[a.display_source.resolve() if p==h/'target/target_display_commit.v' else p for p in files]
    models,data,tops=prepare_logo_inputs(a.out);files+=models
    from run_edge_control_v1 import glyph_table
    font=glyph_table();font_file=a.out/'reference_font.hex'
    font_file.write_text(''.join(f'{font.get(c,{}).get(row,0):04x}\n' for c in range(256) for row in range(16)))
    hashes={manifest_name(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+data}
    (a.out/'SOURCE_MANIFEST.json').write_text(json.dumps(hashes,indent=2)+'\n')
    cmds=[[(MSIM/'vlib.exe').as_posix(),'work'],
        [(MSIM/'vlog.exe').as_posix(),'-sv','-work','work',*[p.as_posix() for p in files]],
        [(MSIM/'vsim.exe').as_posix(),'-c','-quiet','-lib','work','tb_target_frame_system','tb_target_progress',*tops,'+FONT='+font_file.as_posix(),
            '-do','onerror {quit -code 2}; run -all; quit -f -code 0']]
    stages=[]
    for i,cmd in enumerate(cmds):
        started=time.monotonic()
        with (a.out/f'stage_{i}.txt').open('wb') as log:
            r=subprocess.run(cmd,cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        stages.append(dict(argv=cmd,exit_code=r.returncode,elapsed=time.monotonic()-started))
        (a.out/'stages.json').write_text(json.dumps(stages,indent=2)+'\n')
        text=(a.out/f'stage_{i}.txt').read_text(errors='replace')
        assert r.returncode==0 and '** Error:' not in text and '** Fatal:' not in text, (i,a.out)
        print('COMPLETE stage',i,'seconds',round(time.monotonic()-started,2),flush=True)
    final=(a.out/'stage_2.txt').read_text(errors='replace')
    same=hashes=={manifest_name(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+data}
    passed=same and 'PASS TARGET_FINAL_SYSTEM' in final and 'FAIL' not in final
    (a.out/'summary.json').write_text(json.dumps(dict(passed=passed,source_unchanged=same,
        display_experiment_override=bool(a.display_source),reference_font_sha256=hashlib.sha256(font_file.read_bytes()).hexdigest(),
        scope='Actual MAIN/FIFO/packer/MC/guard/leased read/shared font/final HDMI incl geometry/text/diagnostics; synthetic RAW/post-AWB and bounded DDR model; no physical or board proof'),indent=2)+'\n')
    assert passed,a.out
    print(final[-1400:])

if __name__=='__main__':main()
