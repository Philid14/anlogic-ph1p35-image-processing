"""Pinned public-port LATENCY review. Boundary probes are not silently waived."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
EXPECT={
    'normal_first_count':1,'normal_valid':1,'normal_no_fatal':0,'repeat_not_recounted':1,'repeat_age_event':1,
    'resync_count_zero':0,'resync_sum_zero':0,'resync_invalid':0,'resync_clean_pair':1,
    'two_losses_counted':2,'two_losses_visible':1,'two_losses_one_delivery':1,
    'queue_full_lost_four':4,'queue_full_accounted':20,
    'foreign_counted':1,'foreign_not_inserted':0,'foreign_invalid':0,'authoritative_pair_recovers':1,
    'overflow_latched_fatal':1,'alarm_clear_not_recovery':0,'fatal_survives_alarm_clear':1,'fatal_resync_recovers':1,
    'destination_reset_no_old_replay':0,'destination_reset_new_event':1,
    'loss_wrap_still_visible':1,'loss_wrap_deliveries':16}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--msim',type=Path,required=True)
    a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    revision='87bb9a5375843c4f3e9696eb0dbd028f3e364f47'
    files=[]
    for name in ('frame_event_bridge.v','latency_meter.v'):
        rel='features/latency_view/rtl/'+name
        raw=subprocess.check_output(['git','show',revision+':'+rel],cwd=ROOT)
        blob=subprocess.check_output(['git','rev-parse',revision+':'+rel],cwd=ROOT,text=True).strip()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=blob:raise ValueError('Git byte binding failed')
        p=out/name;p.write_bytes(raw);files.append(p)
    tb=out/'tb_latency_review_v2.sv';tb.write_bytes((HERE.parent/'tb'/tb.name).read_bytes());files.append(tb)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (out/'SOURCE_MANIFEST.json').write_text(json.dumps(hashes,indent=2)+'\n')
    env=dict(os.environ);env['PATH']=str(a.msim)+os.pathsep+env.get('PATH','')
    commands=[[str(a.msim/'vlib.exe'),'work'],[str(a.msim/'vlog.exe'),'-sv',*map(str,files)],
        [str(a.msim/'vsim.exe'),'-c','-quiet','tb_latency_review_v2','-do','onerror {quit -code 2}; run -all; quit -f -code 0']]
    stages=[]
    for i,cmd in enumerate(commands):
        p=subprocess.run(cmd,cwd=out,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (out/f'stage_{i}.txt').write_bytes(p.stdout);s=p.stdout.decode(errors='replace')
        ok=p.returncode==0 and '** Error:' not in s and '** Fatal:' not in s
        stages.append(dict(argv=cmd,exit_code=p.returncode,tool_ok=ok))
        if not ok:break
    text=(out/'stage_2.txt').read_text(errors='replace') if (out/'stage_2.txt').exists() else ''
    checks=[dict(name=n,expected=int(e),actual=int(v),reported_pass=bool(int(p))) for n,e,v,p in re.findall(r'CHECK (\w+) expected=(\d+) actual=(\d+) pass=([01])',text)]
    marks=re.findall(r'LATENCY_V2_REVIEW_COMPLETE checks=(\d+) failures=(\d+)',text)
    valid=(len(stages)==3 and all(s['tool_ok'] for s in stages) and len(checks)==len(EXPECT)
        and len({c['name'] for c in checks})==len(EXPECT) and {c['name'] for c in checks}==set(EXPECT)
        and all(c['expected']==EXPECT[c['name']] and c['reported_pass']==(c['actual']==c['expected']) for c in checks)
        and len(marks)==1 and int(marks[0][0])==len(checks)
        and int(marks[0][1])==sum(c['actual']!=c['expected'] for c in checks)
        and hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    control_ok=valid and all(c['actual']==c['expected'] for c in checks if c['name']!='loss_wrap_still_visible')
    result=dict(evidence_valid=valid,normal_controls_satisfied=control_ok,
        all_probes_satisfied=valid and all(c['actual']==c['expected'] for c in checks),revision=revision,
        checks=checks,stages=stages,scope='Public-port isolated digital review; no MAIN wiring or physical CDC/board proof')
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return 2 if not valid else 0 if result['all_probes_satisfied'] else 1


if __name__=='__main__':raise SystemExit(main())
