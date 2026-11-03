"""Reproducible standalone guard+TRACK gate measurement, never MAIN P&R.

Input shadow and output capture/mux logic are INCLUDED in top-level figures.
Hierarchy columns are retained in their native units; logic LUT/ripple are not
interchangeable with the top-level #lut total. No board clock is inferred.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PROFILES={'active64':(64,1),'active32':(32,1),'disabled64':(64,0)}
SOURCES=[HERE/'rtl/color_target_track.v',HERE/'rtl/color_target_track_guard.v',
         HERE/'tools/guard_synth_top.v',HERE/'tools/synth_guard.tcl',Path(__file__)]
ERROR=re.compile(r'(?m)^(?:.*\bERROR\b.*|FAIL_GUARD_SYNTH.*|.*invalid command name.*)$')


def digest(path):
    raw=path.read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(),
                sha256_lf=hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest())


def parse_reports(log,area,timing,summary,tw,enabled):
    end=re.findall(r'^GUARD_SYNTH_COMPLETE time_w=(\d+) enabled=([01])$',log,re.M)
    if end!=[(str(tw),str(enabled))] or ERROR.search(log):
        raise ValueError('missing/duplicate/wrong completion or TD error')
    resources={}
    for key in ('lut','reg','eram','dsp','slice'):
        pattern=r'slice\*?' if key=='slice' else re.escape(key)
        hits=re.findall(r'^#'+pattern+r'\s+(\d+)\b',area,re.M)
        if len(hits)!=1:raise ValueError('missing/duplicate area field '+key)
        resources[key]=int(hits[0])
    hierarchy=[]
    for line in area.splitlines():
        columns=[s.strip() for s in line.strip('|').split('|')]
        if len(columns)==13 and columns[0] and columns[2].isdigit():
            hierarchy.append(dict(instance=columns[0],module=columns[1],
                logic_lut=int(columns[2]),ripple=int(columns[3]),seq=int(columns[4]),
                eram=int(columns[5]),dsp=int(columns[6])))
    for module in ('guard_synth_top','color_target_track_guard'):
        if len([h for h in hierarchy if h['module']==module])!=1:
            raise ValueError('missing/duplicate hierarchy '+module)
    if enabled:
        track=[h for h in hierarchy if h['module']=='color_target_track']
        if len(track)!=1 or track[0]['seq']==0:raise ValueError('TRACK optimized away')
    slack={}
    for key in ('SWNS','HWNS'):
        hits=re.findall(r'\b'+key+r':\s*([+-]?\d+(?:\.\d+)?)ns',timing)
        if len(hits)!=1:raise ValueError('missing/duplicate timing field '+key)
        slack[key+'_ns']=float(hits[0])
    coverage=re.findall(r'^STA coverage\s*:\s*(\d+(?:\.\d+)?)%',summary,re.M)
    starts=re.findall(r'^Begin Point\s*:\s*(.+)$',summary,re.M)
    ends=re.findall(r'^End Point\s*:\s*(.+)$',summary,re.M)
    levels=re.findall(r'^Logic Level\s*:\s*(.+)$',summary,re.M)
    if len(coverage)!=1 or not starts or not ends or not levels:
        raise ValueError('missing STA coverage/actual critical path')
    return dict(top_level=resources,hierarchy=hierarchy,**slack,
                sta_coverage_percent=float(coverage[0]),
                first_setup_path=dict(begin=starts[0],end=ends[0],logic_levels=levels[0]),
                experimental_gate_timing_met=all(v>=0 for v in slack.values()))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--td',type=Path,required=True,help='explicit td_commands_prompt.exe')
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--profiles',nargs='+',choices=PROFILES,default=list(PROFILES))
    ap.add_argument('--timeout-sec',type=float,default=600)
    args=ap.parse_args()
    if not args.td.is_file():ap.error('TD executable not found')
    if args.timeout_sec<=0:ap.error('timeout must be positive')
    if len(set(args.profiles))!=len(args.profiles):ap.error('duplicate profiles')
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before={p.relative_to(ROOT).as_posix():digest(p) for p in SOURCES}
    rows=[]
    for name in args.profiles:
        tw,enabled=PROFILES[name];work=out/name;work.mkdir()
        env=dict(os.environ,COLOR_GUARD_TIME_W=str(tw),COLOR_GUARD_ENABLED=str(enabled))
        command=[str(args.td.resolve()),(HERE/'tools/synth_guard.tcl').as_posix()]
        failure=None;code=None
        try:
            process=subprocess.run(command,cwd=work,env=env,stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,timeout=args.timeout_sec)
            raw=process.stdout;code=process.returncode
            if code!=0:failure='nonzero_exit'
        except subprocess.TimeoutExpired as exc:
            raw=exc.stdout or b'';failure='timeout'
        except OSError as exc:
            raw=str(exc).encode('utf-8');failure='launch_error'
        (work/'synthesis.log').write_bytes(raw)
        log=raw.decode('utf-8',errors='replace').replace('\r\n','\n')
        row=dict(name=name,time_w=tw,counter_w=16,enabled=enabled,
            experimental_target_age_ticks=1000003 if enabled else 0,
            experimental_reliable_age_ticks=2000003 if enabled else 0,
            period_ns=10.0,command=command,cwd=str(work),exit_code=code,
            failure=failure,warnings=[s for s in log.splitlines() if re.search(r'(?:CRITICAL-)?WARNING:',s)])
        if failure is None:
            try:
                for filename in ('guard_summary.txt','guard_test.sdc'):
                    if not (work/filename).is_file() or not (work/filename).stat().st_size:
                        raise ValueError('missing/empty report '+filename)
                row['measurement']=parse_reports(log,(work/'guard_gate.area').read_text(),
                    (work/'guard_gate.ts').read_text(),(work/'guard_summary.txt').read_text(),tw,enabled)
            except (ValueError,OSError) as exc:row['failure']='invalid_evidence: '+str(exc)
        row['evidence_valid']=row['failure'] is None
        row['reports']={p.name:digest(p) for p in work.iterdir() if p.is_file() and p.suffix!='.db'}
        rows.append(row)
        print(('MEASURED ' if row['evidence_valid'] else 'FAIL ')+name+' '+str(row.get('measurement',row['failure'])),flush=True)
    after={p.relative_to(ROOT).as_posix():digest(p) for p in SOURCES}
    unchanged=before==after
    report=dict(schema=1,created_utc=datetime.now(timezone.utc).isoformat(),
        scope='Standalone guard+TRACK gate estimates including fixture; no P&R/Fmax/bit/board proof',
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        worktree=subprocess.check_output(['git','status','--porcelain=v1'],cwd=ROOT,text=True),
        source_hashes=before,source_unchanged=unchanged,profiles=rows,
        evidence_valid=unchanged and all(r['evidence_valid'] for r in rows),
        production_limits_confirmed=False,integration_ready=False,
        io_timing='Top fixture I/O and async reset are not board-constrained; registered guard boundaries use the synthetic clock')
    (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('GUARD_MEASUREMENTS_COMPLETE evidence_valid='+str(report['evidence_valid']))
    return 0 if report['evidence_valid'] else 1


if __name__=='__main__':raise SystemExit(main())
