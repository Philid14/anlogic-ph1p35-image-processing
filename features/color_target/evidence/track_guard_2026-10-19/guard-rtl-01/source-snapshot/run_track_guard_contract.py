"""Strict tool-exit and literal RTL contract checks for the independent guard.

No main wiring, CDC, DDR, video or physical timing proof is implied. Each --out
must be new. Every vlib/vlog/vsim or iverilog/vvp stage retains its raw output
and exit code; successful terminal text cannot override a failing tool exit.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE/'tools'))
from simlib import add_args,pick,find_iverilog

MAIN_CASES={
    'no_implicit_session','duplicate_reorder_and_payload','independent_age_and_high_water',
    'invalid_cancel_and_absence','no_target_never_refreshes_positive_age','invalid_stream_timeout',
    'late_future_and_unavailable_identity','explicit_session_authority','repeated_empty_epoch_barriers',
    'session_reuse_rejected','simultaneous_control_and_data','time_valid_loss_and_recovery',
    'clock_rollback','clock_wrap','frame_id_wrap','counter_saturation',
    'one_result_per_clock','simultaneous_expiry_and_fresh_result'}
ERROR=re.compile(r'^(?:#\s*)?(?:FAIL\b|\*\*\s+(?:Error|Fatal):|Error:)',re.M)

def stage(argv,cwd,log,timeout,env=None):
    try:
        process=subprocess.run([str(x) for x in argv],cwd=cwd,env=env,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        raw=process.stdout;code=process.returncode;failure=None if code==0 else 'nonzero_exit'
    except subprocess.TimeoutExpired as exc:
        raw=exc.stdout or b'';code=None;failure='timeout'
    except OSError as exc:
        raw=str(exc).encode('utf-8');code=None;failure='launch_error'
    log.write_bytes(raw)
    text=raw.decode('utf-8',errors='replace').replace('\r\n','\n')
    if failure is None and ERROR.search(text):failure='error_marker'
    return dict(command=[str(x) for x in argv],cwd=str(cwd),exit_code=code,
                failure=failure,passed=failure is None,log=log.name),text

def verify_completion(text,expected_cases):
    matches=re.findall(r'^(?:#\s*)?GUARD_COMPLETE checks=(\d+) failures=(\d+)$',text,re.M)
    cases=re.findall(r'^(?:#\s*)?CASE ([a-z_]+)$',text,re.M)
    if ERROR.search(text):return False,'error_marker',None
    if len(matches)!=1 or int(matches[0][0])<1 or int(matches[0][1])!=0:
        return False,'incomplete_or_failing_checks',None
    if len(cases)!=len(set(cases)) or set(cases)!=set(expected_cases):
        return False,'missing_or_duplicate_scenarios',None
    return True,None,dict(checks=int(matches[0][0]),cases=cases)

def selftest(out):
    rows=[]
    for name,code,want in [('tool_success',"print('GUARD_COMPLETE checks=1 failures=0')",True),
         ('tool_exit_after_completion',"print('GUARD_COMPLETE checks=1 failures=0');raise SystemExit(7)",False),
         ('tool_error_after_completion',"print('GUARD_COMPLETE checks=1 failures=0');print('** Error: injected')",False)]:
        got,_=stage([sys.executable,'-B','-c',code],ROOT,out/(name+'.log'),10)
        rows.append(dict(name=name,expected_pass=want,observed_pass=got['passed'],matched=got['passed']==want,stage=got))
    for name,text in [('missing_completion','CASE sample\n'),
        ('zero_checks','CASE sample\nGUARD_COMPLETE checks=0 failures=0\n'),
        ('duplicate_case','CASE sample\nCASE sample\nGUARD_COMPLETE checks=2 failures=0\n')]:
        passed,reason,_=verify_completion(text,{'sample'})
        rows.append(dict(name=name,expected_pass=False,observed_pass=passed,matched=not passed,failure=reason))
    report=dict(kind='VERIFICATION TOOL SELFTEST; not RTL',checks=rows,passed=all(r['matched'] for r in rows))
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('TOOL_SELFTEST_COMPLETE checks=6 failures='+str(sum(not r['matched'] for r in rows)))
    return 0 if report['passed'] else 1

def main():
    ap=argparse.ArgumentParser(description=__doc__);add_args(ap)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--selftest-tools',action='store_true')
    ap.add_argument('--timeout-sec',type=float,default=120)
    args=ap.parse_args()
    if args.timeout_sec<=0:ap.error('--timeout-sec must be positive')
    args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=False)
    if args.selftest_tools:return selftest(args.out)
    kind,info=pick(args.sim,args.msim)
    if kind is None:ap.error(info)
    sources=[HERE/'rtl/color_target_track.v',HERE/'rtl/color_target_track_guard.v',HERE/'tb/tb_color_target_track_guard.v']
    bound_sources=sources+[Path(__file__),HERE/'tools/simlib.py']
    def hashes():return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in bound_sources}
    before=hashes();jobs=[]
    for width in (8,64):jobs.append((f'core_time{width}','tb_color_target_track_guard',dict(TIME_W=width),MAIN_CASES))
    for name,t,r,mode,case in [
        ('positive_limit',3,7,1,'positive_age_independent_of_reliable_age'),
        ('reliable_limit',7,3,2,'reliable_watchdog_independent_of_target_limit'),
        ('target_disabled',0,5,0,'disabled_or_unrepresentable_limits'),
        ('reliable_disabled',5,0,0,'disabled_or_unrepresentable_limits'),
        ('negative_limit',-1,5,0,'disabled_or_unrepresentable_limits'),
        ('overflow_limit',256,5,0,'disabled_or_unrepresentable_limits'),
        ('largest_limit',255,255,3,'largest_unsigned_age_then_time_wrap')]:
        jobs.append((name,'tb_color_target_track_guard_limits',dict(TARGET_AGE=t,RELIABLE_AGE=r,MODE=mode),{case}))
    results=[]
    for name,top,params,cases in jobs:
        logs=args.out/name;logs.mkdir();stages=[];text='';passed=True
        with tempfile.TemporaryDirectory(prefix='ct_guard_') as tmp:
            work=Path(tmp);env=dict(os.environ)
            if kind=='modelsim':
                sim_root=Path(info[0]);env['PATH']=str(sim_root)+os.pathsep+env.get('PATH','')
                commands=[('vlib',[sim_root/'vlib.exe','work']),('vlog',[sim_root/'vlog.exe','-quiet','-work','work',*sources]),
                    ('vsim',[sim_root/'vsim.exe','-c','-quiet',*[f'-g{k}={v}' for k,v in params.items()],
                             'work.'+top,'-do','run -all; quit -f'])]
            else:
                iv,vvp,_=find_iverilog()
                commands=[('iverilog',[iv,'-g2005','-Wall','-s',top,*[f'-P{top}.{k}={v}' for k,v in params.items()],'-o',work/'guard.vvp',*sources]),
                          ('vvp',[vvp,work/'guard.vvp'])]
            for label,command in commands:
                got,text=stage(command,work,logs/(label+'.log'),args.timeout_sec,env)
                stages.append(got)
                if not got['passed']:passed=False;break
        completion,why,details=verify_completion(text,cases) if passed else (False,'tool_stage_failure',None)
        result=dict(name=name,top=top,parameters=params,passed=passed and completion,failure=why,details=details,stages=stages)
        results.append(result);print(('PASS' if result['passed'] else 'FAIL')+' '+name+(' '+str(details['checks'])+' checks' if details else ' '+str(why)),flush=True)
    unchanged=before==hashes()
    report=dict(schema=1,created_utc=datetime.now(timezone.utc).isoformat(),
        kind='INDEPENDENT GUARD RTL; no CDC/DDR/main/video/physical/board proof',
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        worktree=subprocess.check_output(['git','status','--porcelain=v1'],cwd=ROOT,text=True),
        simulator=kind,python=sys.version,source_sha256_lf=before,source_unchanged=unchanged,
        jobs=results,passed=unchanged and all(r['passed'] for r in results),
        integration_ready=False,production_thresholds='UNSET; testbench limits are fixtures')
    (args.out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"GUARD_CONTRACT_COMPLETE jobs={len(results)} passed={sum(r['passed'] for r in results)} source_unchanged={unchanged}")
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
