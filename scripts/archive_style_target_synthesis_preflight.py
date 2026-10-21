"""Archive resource measurements without creating a candidate/bit tag."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--attempt',required=True);a=ap.parse_args()
src=ROOT/'tmp/style_v2_target_v1'/a.attempt
dst=ROOT/'docs/evidence/STYLE_V2_TARGET_V1'/a.attempt
dst.mkdir(exist_ok=False)
run=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/syn_1'
manifest=json.loads((src/'SOURCE_MANIFEST.json').read_text())
files=[src/'SOURCE_MANIFEST.json',src/'stages.json',src/'flow.tcl',src/'syn_1_stdout.txt',
       run/'camera_to_dsi_display_gate.area',run/'camera_to_dsi_display_rtl.area',run/'gate.qor',run/'camera_to_dsi_display_gate.ts']
copied=[]
for p in files:
    if p.is_file():
        shutil.copy2(p,dst/p.name)
        copied.append(dict(name=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
result=dict(kind='SYNTHESIS_PREFLIGHT_ONLY',source_commit=manifest['source_commit'],
            p_and_r='NOT_RUN',bit='NOT_GENERATED',board='NOT_RUN',files=copied)
(dst/'INDEX.json').write_text(json.dumps(result,indent=2)+'\n')
print('Archived synthesis-only evidence',a.attempt,manifest['source_commit'])
