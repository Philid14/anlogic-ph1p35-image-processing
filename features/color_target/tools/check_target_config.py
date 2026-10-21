"""Check an explicit TARGET configuration declaration and RTL source binding.

This does NOT parse/elaborate MAIN or certify its connections. Missing decisions
are UNKNOWN; declarations never prove CDC, identity, clocks or atomic display.
Exit 0: declaration checks satisfied; 1: invalid; 2: incomplete/unverified gate.
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
FIXED=dict(schema=1,time_w=64,counter_w=16,xw=11,yw=10,width=1280,height=720,
           ppc=4,pixel_format='RGB888',lane_order='MSB_FIRST',
           filter_enable=False,display_policy='STRICT_SAME_FRAME')
NUMBERS=('acq_frames','lost_frames','max_target_age_ticks','max_reliable_age_ticks',
         'tick_hz','max_capture_to_display_start_ticks','max_scan_ticks')
OBLIGATIONS=[
    'Parameters must be checked against the actual elaborated MAIN instance',
    'Actual clock/timebase and transferred timestamps must match the declaration',
    'SOF/EOL/EOF, complete/cancel and DDR generation/read lease must be verified',
    'CDC whole-packet service/reset/epoch behavior must pass actual adapter tests',
    'Box/cross/text/count/state must use one committed observation and common final mask',
    'Display watchdog must expire annotations even if the observation clock stops',
    'New whole-system P&R and version-bound bit/board acceptance remain required']


def load_config(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate configuration key: '+key)
            result[key]=value
        return result
    def reject_constant(value):raise ValueError('non-JSON constant: '+value)
    return json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique,parse_constant=reject_constant)


def evaluate(config):
    if type(config) is not dict:raise ValueError('configuration must be a JSON object')
    rows=[]
    def add(name,status,detail):rows.append(dict(name=name,status=status,detail=detail))
    for name in sorted(set(config)-set(FIXED)-set(NUMBERS)):
        add(name,'FAIL','unknown field; possible misspelling')
    for name,expected in FIXED.items():
        got=config.get(name)
        if got is None:add(name,'UNKNOWN','required declaration missing')
        elif type(got) is not type(expected) or got!=expected:
            add(name,'FAIL',f'current delivery contract requires {expected!r}')
        else:add(name,'PASS','matches current delivery contract')
    values={}
    for name in NUMBERS:
        got=config.get(name)
        if got is None:add(name,'UNKNOWN','requires MAIN decision/measurement');continue
        if type(got) is not int:
            add(name,'FAIL','must be an integer; booleans/floats/strings are rejected');continue
        lower=0 if name=='max_capture_to_display_start_ticks' else 1
        upper=255 if name in ('acq_frames','lost_frames') else (1<<64)-1
        if not lower<=got<=upper:
            add(name,'FAIL',f'outside {lower}..{upper}');continue
        values[name]=got;add(name,'PASS','explicit in-range declaration')
    required=('max_capture_to_display_start_ticks','max_scan_ticks',
              'max_target_age_ticks','max_reliable_age_ticks')
    budget=None
    if all(name in values for name in required):
        elapsed=values[required[0]]+values[required[1]]
        fits=elapsed<=min(values[required[2]],values[required[3]])
        # Excess age means hide the whole group; it is NOT permission to raise
        # limits or a proof that an actually selected scan will be fresh.
        add('declared_full_scan_budget','PASS' if fits else 'WARN',
            'declared worst-case scan fits both ages' if fits else
            'some scans exceed age limits and must hide the complete annotation group')
        budget=dict(capture_to_scan_end_ticks=elapsed,fits_both_limits=fits)
    status='FAIL' if any(r['status']=='FAIL' for r in rows) else (
        'UNKNOWN' if any(r['status']=='UNKNOWN' for r in rows) else 'PASS')
    return dict(configuration_status=status,checks=rows,declared_budget=budget,
        declaration_only=True,elaborated_parameters_verified=False,
        integration_verified=False,unverified_obligations=OBLIGATIONS,
        configuration=config)


def source_binding(root):
    manifest_path=HERE/'board/TARGET_DELIVERY.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    rows=[]
    for item in manifest['files']:
        path=(root/item['path']).resolve()
        row=dict(path=item['path'],expected_sha256_lf=item['sha256_lf'])
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            row.update(matched=False,reason='missing_or_escaping_source')
        else:
            raw=path.read_bytes().replace(b'\r\n',b'\n')
            actual=hashlib.sha256(raw).hexdigest()
            row.update(sha256_lf=actual,matched=actual==item['sha256_lf'])
        rows.append(row)
    return dict(scope='TARGET delivery RTL only; not MAIN sources/build/bit binding',
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        files=rows,matched=bool(rows) and all(r['matched'] for r in rows))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config',type=Path,required=True)
    ap.add_argument('--source-root',type=Path,default=HERE.parents[1])
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--gate',choices=['configuration','integration'],default='configuration')
    args=ap.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    raw=args.config.read_bytes()
    try:report=evaluate(load_config(raw))
    except (ValueError,UnicodeError) as exc:
        report=dict(configuration_status='FAIL',error=str(exc),integration_verified=False)
    report.update(schema=1,config_sha256=hashlib.sha256(raw).hexdigest(),
                  source_binding=source_binding(args.source_root),gate=args.gate)
    if not report['source_binding']['matched']:code=1
    elif report['configuration_status']=='FAIL':code=1
    elif report['configuration_status']=='UNKNOWN' or args.gate=='integration':code=2
    else:code=0
    report['exit_code']=code
    (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('TARGET_PREFLIGHT configuration='+report['configuration_status']+
          ' source_bound='+str(report['source_binding']['matched'])+' integration=UNVERIFIED exit='+str(code))
    return code


if __name__=='__main__':raise SystemExit(main())
