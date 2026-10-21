"""Actual MAIN adapter RTL checks, separate from TARGET's abstract scheduler."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
HDL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
TARGET=ROOT/'features/color_target/rtl'
JOBS={
    'frame_transaction_ledger':(['frame_transaction_ledger.v'],[], 'FRAME_LEDGER'),
    'frame_bundle_cdc':(['frame_bundle_cdc.v'],[], 'FRAME_CDC'),
    'target_observer_adapter':(['target_observer_adapter.v'],[], 'OBSERVER_ADAPTER'),
    'target_display_commit':(['target_display_commit.v'],
        [TARGET/'color_target_overlay.v',TARGET/'color_target_text_overlay.v',HDL/'osd_char_lib.v'],'DISPLAY_COMMIT'),
}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--jobs',nargs='+',choices=list(JOBS),default=list(JOBS))
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=False)
    rows=[]
    for name,(files,extra,marker) in JOBS.items():
        if name not in a.jobs:continue
        sources=[ROOT/'tests'/('tb_'+name+'.sv')]+[HDL/'target'/s for s in files]+extra
        before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
        executable=a.out/(name+'.vvp')
        commands=[['C:/iverilog/bin/iverilog.exe','-g2012','-Wall','-s','tb_'+name,'-o',str(executable),*map(str,sources)],
                  ['C:/iverilog/bin/vvp.exe',str(executable)]]
        stages=[]
        for i,cmd in enumerate(commands):
            r=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
            log=name+f'_{i}.txt'; (a.out/log).write_bytes(r.stdout)
            stages.append(dict(argv=cmd,exit_code=r.returncode,log=log))
            assert r.returncode==0,stages[-1]
            if i==1:
                result=r.stdout.decode(errors='replace')
                assert not re.search(r'\b(FAIL|FATAL)\b',result),result
                m=re.search(r'PASS '+marker+r' checks=(\d+)',result); assert m,result
        assert before=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
        rows.append(dict(name=name,passed=True,checks=int(m[1]),stages=stages,source_sha256=before))
        (a.out/'summary.json').write_text(json.dumps(dict(passed=True,scope='MAIN adapters only; no DDR/whole-system certification',jobs=rows),indent=2)+'\n')
        print('PASS',name,'checks',m[1],flush=True)


if __name__=='__main__':main()
