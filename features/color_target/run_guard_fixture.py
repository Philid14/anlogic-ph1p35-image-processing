"""Public-output wiring test for the default 64-bit synthesis fixture only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'tools'))
from simlib import add_args,pick,find_iverilog
from run_track_guard_contract import stage


def main():
    ap=argparse.ArgumentParser(description=__doc__);add_args(ap)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();kind,info=pick(args.sim,args.msim)
    if kind is None:ap.error(info)
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    sources=[HERE/'rtl/color_target_track.v',HERE/'rtl/color_target_track_guard.v',
             HERE/'tools/guard_synth_top.v',HERE/'tb/tb_guard_synth_fixture.v']
    bound=sources+[Path(__file__),HERE/'run_track_guard_contract.py',HERE/'tools/simlib.py']
    def hashes():return {str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in bound}
    before=hashes();stages=[];text=''
    with tempfile.TemporaryDirectory(prefix='guard_fixture_') as tmp:
        work=Path(tmp);env=dict(os.environ)
        if kind=='modelsim':
            sim=Path(info[0]);env['PATH']=str(sim)+os.pathsep+env.get('PATH','')
            commands=[('vlib',[sim/'vlib.exe','work']),
                ('vlog',[sim/'vlog.exe','-quiet',*sources]),
                ('vsim',[sim/'vsim.exe','-c','-quiet','work.tb_guard_synth_fixture','-do','run -all; quit -f'])]
        else:
            iv,vvp,_=find_iverilog()
            commands=[('iverilog',[iv,'-g2005','-s','tb_guard_synth_fixture','-o',work/'fixture.vvp',*sources]),
                      ('vvp',[vvp,work/'fixture.vvp'])]
        for label,command in commands:
            got,text=stage(command,work,out/(label+'.log'),120,env);stages.append(got)
            if not got['passed']:break
    complete=re.findall(r'^(?:#\s*)?GUARD_FIXTURE_COMPLETE checks=(\d+) failures=(\d+)$',text,re.M)
    passed=all(s['passed'] for s in stages) and complete==[('6','0')] and before==hashes()
    report=dict(scope='Synthesis fixture wiring only; existing production guard contracts not rerun',
        simulator=kind,source_hashes=before,source_unchanged=before==hashes(),stages=stages,
        complete=complete,passed=passed,integration_verified=False)
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('GUARD_FIXTURE_WIRING passed='+str(passed)+' completion='+str(complete))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
