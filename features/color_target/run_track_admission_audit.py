"""Characterize unmodified TRACK RTL; matching known behavior is NOT closure."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'tools'))
from simlib import add_args,simulate

def main():
    ap=argparse.ArgumentParser();add_args(ap);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    srcs=[HERE/'rtl/color_target_track.v',HERE/'tb/tb_track_admission_audit.v']
    with tempfile.TemporaryDirectory(prefix='ct_track_audit_') as wd:
        ok,out,err=simulate(srcs,'tb_track_admission_audit',{}, {},requested=args.sim,msim_root=args.msim,workdir=wd)
    (args.out/'transcript.log').write_text(out+err,encoding='utf-8')
    observed={}
    for line in out.splitlines():
        m=re.match(r'(?:# )?S (\w+) ([0-9 ]+)$',line.strip())
        if m:observed[m[1]]=list(map(int,m[2].split()))
    characterized={'DUPLICATE':[2,1,1,99],'REORDER':[2,1,1,1],
        'INVALID_RUN':[2,1,1,3],'SILENCE':[2,1,1,3],
        'SESSION_INVALID':[2,1,1,3],'SESSION_VALID':[1,0,2,1],
        'OLD_SESSION_RETURN':[1,0,1,99],'ABSENT_FIRST':[3,1,1,3],'ABSENT_SECOND':[0,0,1,3]}
    gaps={
        'DUPLICATE':'OPEN: duplicate frame confirms target; admission owner not implemented',
        'REORDER':'OPEN: decreasing identities accepted; ordering owner not implemented',
        'INVALID_RUN':'OPEN: no observation age mechanism; no approved timeout value',
        'SILENCE':'OPEN: no wall-clock expiry; 20 cycles are a fixture, not an approved limit',
        'SESSION_INVALID':'OPEN: session clear requires valid strobe; explicit epoch authority absent',
        'OLD_SESSION_RETURN':'OPEN: retired session can re-enter through a valid result',
    }
    report=dict(kind='CURRENT RTL CHARACTERIZATION, NOT REQUIREMENTS PASS',observed=observed,
        characterized=characterized,open_gaps=gaps,source_sha256_lf={p.name:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in srcs},
        trace_matched=ok and 'TRACK_AUDIT_COMPLETE' in out and observed==characterized)
    (args.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for name,values in observed.items():print(name,values,gaps.get(name,'CHARACTERIZED control; not full integration proof'))
    print('Trace matched:',report['trace_matched'],'Open gaps:',len(gaps))
    return 0 if report['trace_matched'] else 1

if __name__=='__main__':raise SystemExit(main())
