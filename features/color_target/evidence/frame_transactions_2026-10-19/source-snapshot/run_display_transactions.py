"""Exercise production TARGET RTL in a test-only, dual-clock display proposal.

All MAIN scheduling/transfer logic lives in the testbench, not in production.
Five harness mutations must fail the same public-port assertions. Tool failure
does not count as a successful mutation witness.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from run_track_guard_contract import stage

HERE=Path(__file__).resolve().parent
CASES={'startup_missing','text_preparation_barrier','same_frame_public_outputs',
 'newer_result_during_scan','late_result_boundary','slot_generation_mismatch',
 'hold_keeps_true_box_identity','identity_and_disposition','frame_wrap_requires_session',
 'session_barrier_masks_inflight','whole_scan_age_budget','observation_clock_stop_display_watchdog',
 'independent_time_loss_masks_all','global_reset_masks_all'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--msim',required=True,type=Path);ap.add_argument('--timeout-sec',type=int,default=60)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    rtl=[HERE/'rtl'/name for name in ['color_target_track.v','color_target_track_guard.v',
        'color_target_overlay.v','color_target_text_overlay.v']]
    tb=HERE/'tb/tb_display_transactions.v'
    sources=rtl+[tb,Path(__file__),HERE/'run_track_guard_contract.py']
    hashes=lambda:{str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in sources}
    before=hashes();rows=[]
    for mode,name in [(0,'baseline'),(1,'ignore_slot_generation'),(2,'live_box_during_scan'),
                      (3,'ignore_frame_identity'),(4,'skip_text_preparation_barrier'),
                      (5,'freeze_age_with_observation_clock')]:
        work=args.out/name;work.mkdir();logs=work/'logs';logs.mkdir()
        stages=[];text='';tool_ok=True
        commands=[('vlib',[args.msim/'vlib.exe','work']),
            ('vlog',[args.msim/'vlog.exe','-sv','-work','work',*rtl,tb]),
            ('vsim',[args.msim/'vsim.exe','-c','-onfinish','stop','work.tb_display_transactions',
             f'-GMUTATION={mode}','-do','onerror {quit -code 2}; run -all; quit -f -code 0'])]
        for label,cmd in commands:
            item,text=stage(cmd,work,logs/(label+'.log'),args.timeout_sec)
            stages.append(item)
            # Expected functional FAIL lines are examined separately from tool
            # errors; a compiler/crash/nonzero simulator exit is never evidence.
            raw_ok=item['exit_code']==0 and not re.search(r'^(?:#\s*)?(?:\*\*\s+(?:Error|Fatal):|Error:)',text,re.M)
            if not raw_ok:tool_ok=False;break
        marks=re.findall(r'^(?:#\s*)?DISPLAY_TX_COMPLETE checks=(\d+) failures=(\d+)$',text,re.M)
        cases=re.findall(r'^(?:#\s*)?CASE ([a-z_]+)$',text,re.M)
        complete=(len(marks)==1 and len(cases)==len(CASES) and set(cases)==CASES)
        checks,failures=map(int,marks[0]) if len(marks)==1 else (0,0)
        functional=tool_ok and complete and checks>0 and failures==0
        expected_match=functional if mode==0 else tool_ok and complete and checks>0 and failures>0
        row=dict(name=name,mutation=mode,tool_ok=tool_ok,complete=complete,
            checks=checks,failures=failures,expected='PASS' if mode==0 else 'functional assertion failure',
            matched=bool(expected_match),stages=stages,cases=cases)
        rows.append(row);print(('PASS ' if expected_match else 'FAIL ')+name+f' checks={checks} failures={failures}',flush=True)
    unchanged=before==hashes()
    report=dict(schema=1,created_utc=datetime.now(timezone.utc).isoformat(),
        scope='Production TARGET RTL + TEST-ONLY atomic transfer/display scheduler; no physical CDC/DDR/MAIN/board proof',
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=HERE,text=True).strip(),
        source_sha256_lf=before,source_unchanged=unchanged,python=sys.version,
        clock_period_ns=dict(observation=10,display=14),
        fixtures=dict(max_target_age=10000,max_reliable_age=10000,text_settle_display_clocks=141),
        jobs=rows,passed=unchanged and all(x['matched'] for x in rows),integration_ready=False)
    (args.out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"DISPLAY_TRANSACTIONS_COMPLETE jobs={len(rows)} matched={sum(x['matched'] for x in rows)} source_unchanged={unchanged}")
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
