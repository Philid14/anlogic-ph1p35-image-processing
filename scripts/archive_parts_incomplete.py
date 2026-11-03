"""Preserve a bounded, non-candidate build; never creates a bit/tag.

Use ONLY after the active native PHY has ended or was explicitly terminated
for persistent congestion. A manual stop is not proof of unroutability.
"""
import json,shutil
from pathlib import Path
from build_inspection_parts_motion import ROOT,OUT,CHANGED,snapshot,regression_gate
from archive_latency_performance import copy_reports

def main():
 status=json.loads((OUT/'INCOMPLETE.json').read_text())
 assert status['candidate_issued'] is False and status['bit_generated'] is False
 assert not (OUT/'camera_to_dsi_display.bit').exists()
 assert 'PHY_COMPLETE' not in (OUT/'phy_stdout.txt').read_text()
 now=snapshot();frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text())
 for key in ('files','al_sha256','old_bits'):assert now[key]==frozen[key]
 gates=regression_gate();assert len(gates)==56
 dest=ROOT/'docs/evidence/INSPECTION_PARTS_MOTION_V1/INCOMPLETE_BUILD'
 assert not dest.exists(),'Never overwrite preserved evidence'
 copy_reports(OUT,dest/'full_r2')
 (dest/'REGRESSION_GATE.json').write_text(json.dumps(gates,indent=2)+'\n')
 for rel in gates:
  folder=(ROOT/rel).parent
  copy_reports(folder,dest/'verification'/folder.relative_to(ROOT/'tmp'))
 attempts=('resource_r0','resource_r1','resource_r2','resource_paged','resource_paged_opt','resource_paged_opt2','resource_compact','resource_payload18','resource_payload18_r1','payload18_native','full_r0','full_r1')
 for name in attempts:
  src=ROOT/'tmp/inspection_parts_motion'/name
  if not src.exists():continue
  target=dest/'attempts'/name;copy_reports(src,target)
  for rel in CHANGED:
   p=src/'inputs'/rel
   if p.exists():
    q=target/'changed_inputs'/Path(rel).relative_to('in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source')
    q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 # The staged18bit helper also has a stand-alone native source manifest.
 helper=ROOT/'tmp/inspection_parts_motion/payload18_staging_r1/vision/inspection_payload_delay.v'
 if helper.exists():shutil.copy2(helper,dest/'attempts/payload18_native/inspection_payload_delay.v')
 (dest/'STATUS.json').write_text(json.dumps(dict(status,source_commit=frozen['source_commit'],inputs_verified=len(frozen['files']),historical_bits_unchanged=len(frozen['old_bits']),verification_hashes=len(gates)),indent=2)+'\n')
 assert snapshot()['files']==frozen['files']
 print('Preserved incomplete evidence; NO candidate, NO bit, NO tag:',dest)

if __name__=='__main__':main()
