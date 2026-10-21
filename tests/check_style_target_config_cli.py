"""Run actual configuration CLI rejection/UNKNOWN/source-binding witnesses."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    good=json.loads((ROOT/'docs/STYLE_V2_TARGET_V1_CONFIG.json').read_text())
    cases=[('pending',ROOT/'features/color_target/integration/TARGET_CONFIG_PENDING.json',[],2),
        ('declared',ROOT/'docs/STYLE_V2_TARGET_V1_CONFIG.json',[],0),
        ('integration',ROOT/'docs/STYLE_V2_TARGET_V1_CONFIG.json',['--gate','integration'],2)]
    for name,value in [('zero_age',0),('boolean_age',True)]:
        conf=dict(good,max_target_age_ticks=value);p=a.out/(name+'.json');p.write_text(json.dumps(conf))
        cases.append((name,p,[],1))
    duplicate=a.out/'duplicate_key.json';duplicate.write_text('{"tick_hz":1,"tick_hz":2}')
    cases.append(('duplicate_key',duplicate,[],1))
    invalid_root=a.out/'source_mismatch'
    delivery=json.loads((ROOT/'features/color_target/board/TARGET_DELIVERY.json').read_text())
    for item in delivery['files']:
        dest=invalid_root/item['path'];dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes((ROOT/item['path']).read_bytes())
    changed=invalid_root/delivery['files'][0]['path']
    changed.write_bytes(changed.read_bytes()+b'\n// Negative binding witness only\n')
    cases.append(('source_mismatch',ROOT/'docs/STYLE_V2_TARGET_V1_CONFIG.json',['--source-root',str(invalid_root)],1))
    results=[]
    for name,path,extra,expected in cases:
        command=[sys.executable,'-B','-X','utf8',str(ROOT/'features/color_target/tools/check_target_config.py'),
            '--config',str(path),'--out',str(a.out/(name+'_result')),*extra]
        r=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (a.out/(name+'_stdout.txt')).write_bytes(r.stdout)
        results.append(dict(name=name,argv=command,expected_exit=expected,actual_exit=r.returncode,matched=r.returncode==expected))
        assert r.returncode==expected,(name,expected,r.returncode)
    (a.out/'summary.json').write_text(json.dumps(dict(passed=True,cases=results,integration_verified=False),indent=2)+'\n')
    print('PASS configuration CLI: 7 actual exit-code witnesses; integration remains UNVERIFIED')

if __name__=='__main__':main()
