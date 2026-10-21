"""Save independent check evidence, explicitly without certifying integration."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import argparse

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'docs/evidence/STYLE_V2_TARGET_V1'
parser=argparse.ArgumentParser()
parser.add_argument('--handoff',type=Path,required=True)
HANDOFF=parser.parse_args().handoff.resolve()
DEST.mkdir(parents=True,exist_ok=True)
r=json.loads((HANDOFF/'summary.json').read_text())
assert r['checks_status']=='PASS' and r['source_unchanged_during_run']
assert not r['integration_ready'] and len(r['checks'])==16
assert all(x['passed'] for x in r['checks'])
archive=DEST/'independent_target_handoff.zip'
assert not archive.exists()
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(HANDOFF.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(HANDOFF).as_posix())
shutil.copy2(HANDOFF/'summary.json',DEST/'target_handoff_summary.json')
for run in ('adapters_01','ledger_03'):
    src=ROOT/'tmp/style_v2_target_v1'/run
    q=json.loads((src/'summary.json').read_text()); assert q['passed']
    folder=DEST/run; folder.mkdir(exist_ok=False)
    for p in src.iterdir():
        if p.suffix in ('.txt','.json'):shutil.copy2(p,folder/p.name)
failed=json.loads((ROOT/'tmp/style_v2_target_v1/handoff_01/summary.json').read_text())
witness=dict(first_handoff=dict(checks_status=failed['checks_status'],
    source_unchanged=failed['source_unchanged_during_run'],
    checks=[{k:x[k] for k in ('name','passed','exit_code','failure')} for x in failed['checks']],
    explanation='Whole-worktree snapshot changed while MAIN adapter files were added. Not a passing total gate. Fixed checkout rerun retained separately.'),
    ledger_first_attempt=dict(status='FAIL',check=41,
        explanation='Test expected 7 drops, independently enumerated stimulus has 6. Corrected expectation; RTL behavior unchanged for this correction.'),
    integration_ready=False,main_system_fault_matrix='NOT_RUN',physical_cdc='NOT_RUN',board_test='NOT_RUN')
(DEST/'FAILED_ATTEMPTS.json').write_text(json.dumps(witness,indent=2)+'\n')
(DEST/'CHECKPOINT_STATUS.json').write_text(json.dumps(dict(
    target_independent_checks='PASS',main_adapter_checks='PASS within individual stated scope',
    full_main_system='NOT_RUN',p_and_r='NOT_RUN',bit='NOT_GENERATED',board='NOT_RUN',
    archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),indent=2)+'\n')
print('Saved independent handoff and MAIN component evidence; whole system NOT certified')
