"""Multi-clock MAIN/real soft-FIFO check; DDR is an explicit bounded model."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]
HDL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
IP=HDL.parent/'ip_source'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(exist_ok=False,parents=True)
    sources=[ROOT/'tests/tb_target_frame_system.sv',ROOT/'tests/tb_target_progress.sv',*sorted((HDL/'target').glob('*.v')),
        *sorted((ROOT/'features/color_target/rtl').glob('*.v')),
        *[HDL/p for p in ('video_in.v','video_out.v','mc_to_user_interface.v','data_96bit_to_128bit.v',
            'isp/fifo_event_counter.v','vtc/uivtc.v','hdmi_mixer.v','osd_char_lib.v','anlogic_logo_rom.v')]]
    for folder in ('w128_d512_fifo','w155_d512_fifo'):sources+=sorted((IP/folder).glob('*.v'))
    before={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    commands=[['C:/iverilog/bin/iverilog.exe','-g2012','-Wall','-s','tb_target_frame_system','-s','tb_target_progress','-o',str(a.out/'system.vvp'),*map(str,sources)],
              ['C:/iverilog/bin/vvp.exe',str(a.out/'system.vvp')]]
    stages=[]
    for i,cmd in enumerate(commands):
        with (a.out/f'stage_{i}.txt').open('wb') as log:
            try:r=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=900)
            except subprocess.TimeoutExpired:
                stages.append(dict(argv=cmd,exit_code=None,failure='timeout'))
                (a.out/'stages.json').write_text(json.dumps(stages,indent=2)+'\n');raise
        stages.append(dict(argv=cmd,exit_code=r.returncode))
        (a.out/'stages.json').write_text(json.dumps(stages,indent=2)+'\n')
        assert r.returncode==0,f'Failed stage {i}; raw log retained in {a.out}'
    output=(a.out/'stage_1.txt').read_text()
    passed='PASS TARGET_FRAME_SYSTEM' in output and 'FAIL' not in output and 'FATAL' not in output
    after={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    result=dict(passed=passed and before==after,source_sha256=before,source_unchanged=before==after,
        scope='Actual MAIN digital adapters and soft FIFOs; modeled bounded DDR; synthetic RAW and AWB boundary stimuli; no physical CDC or board proof')
    (a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed'],a.out
    print(output[-1000:])

if __name__=='__main__':main()
