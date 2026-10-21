"""Preserve failed implementation evidence; never invent a candidate/bit."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
TMP=ROOT/'tmp/style_v2_target_v1'
DEST=ROOT/'docs/evidence/STYLE_V2_TARGET_V1'
RUN=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/syn_1'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    folder=DEST/'resource_failure'; folder.mkdir(exist_ok=False)
    manifest=json.loads((TMP/'syn_preflight_03/SOURCE_MANIFEST.json').read_text())
    assert manifest['source_commit']=='0342a0bc4a1040f92c1d6a2a118409debb8a3c8d'
    place=(TMP/'place_preflight_03_stdout.txt').read_text(errors='replace')
    assert 'PHY-9053 ERROR' in place and '21825' in place and 'PLACEMENT_PREFLIGHT_FAILED' in place
    area=(DEST/'syn_preflight_03/camera_to_dsi_display_gate.area').read_text()
    assert '#slice*                 22754' in area and '#eram                      89' in area
    for p in [TMP/'place_preflight_03_stdout.txt',TMP/'place_preflight_03.tcl',
              RUN/'camera_to_dsi_display_gate.timing',TMP/'syn_preflight_01/syn_1_stdout.txt']:
        name='unexecuted_first_td_call.txt' if p.parent.name=='syn_preflight_01' else p.name
        shutil.copy2(p,folder/name)
    inputs=dict(gate_source_commit=manifest['source_commit'],gate_database_sha256=sha(RUN/'camera_to_dsi_display_gate.db'),
        placement='FAILED_PHY_9053',physical_slice_after_packing=21825,device_slice_limit=21216,
        slice_excess=609,route='NOT_RUN',routed_setup_wns=None,routed_hold_wns=None,
        bit='NOT_GENERATED',candidate_tag='NOT_CREATED',board='NOT_RUN',
        synthesis_timing=dict(setup_wns_ns=-1.724,hold_wns_ns=0.114,confidence='Synthesized',sta_coverage_percent=94.34))
    (folder/'PLACEMENT_RESULT.json').write_text(json.dumps(inputs,indent=2)+'\n')
    cases=[]
    for run in ('system_01','system_02','system_msim_01','system_msim_02'):
        src=TMP/run; dest=folder/run; dest.mkdir()
        for p in src.glob('*'):
            if p.suffix in ('.json','.txt'):shutil.copy2(p,dest/p.name)
        text='\n'.join(p.read_text(errors='replace') for p in src.glob('stage_*.txt'))
        progress=[int(n) for n in re.findall(r'SIM_PROGRESS_NS (\d+)',text)]
        cases.append(dict(run=run,status=('COMPILE_FAILED_DECLARATION_ORDER_FIXED' if run=='system_msim_01'
            else 'INTERRUPTED_NOT_COMPLETED'),last_reported_simulation_ns=max(progress) if progress else None,
            passed=False,explanation='Raw attempts retained. The final integration gate is not passed.'))
    (folder/'INCOMPLETE_SYSTEM_RUNS.json').write_text(json.dumps(cases,indent=2)+'\n')
    with zipfile.ZipFile(folder/'configuration_cli.zip','x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted((TMP/'config_cli_01').rglob('*')):
            if p.is_file() and p.suffix!='.v':z.write(p,p.relative_to(TMP/'config_cli_01').as_posix())
    for name,script in [('simlib','test_simlib_failures.py'),('runner','test_verification_runner.py'),('engineering','test_guard_engineering.py')]:
        cmd=[sys.executable,'-B','-X','utf8',str(ROOT/'features/color_target/tb'/script)]
        r=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (folder/(name+'_tool_selftests.txt')).write_bytes(r.stdout)
        assert r.returncode==0,script
    for rel,expected in manifest['historical_bits'].items():assert sha(ROOT/rel)==expected,rel
    (folder/'HISTORICAL_BITS_UNCHANGED.json').write_text(json.dumps(manifest['historical_bits'],indent=2)+'\n')
    index={p.relative_to(folder).as_posix():sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    (folder/'SHA256.json').write_text(json.dumps(index,indent=2)+'\n')
    print('Saved physical capacity failure, incomplete runs, configuration exits and tool witnesses; old bits unchanged')

if __name__=='__main__':main()
