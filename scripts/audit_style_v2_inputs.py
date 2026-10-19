"""Verify all frozen TD inputs/options against the actual four-mode candidate."""
from pathlib import Path
import re,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
BASE='edge-style-fill-v1-candidate'
HDL='in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/'
AL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.al'
ALLOW={HDL+'isp/style_fill_96.v'}
def audit():
    baseline=json.loads((ROOT/'artifacts/bitstreams/EDGE_STYLE_FILL_V1/build_evidence/SOURCE_MANIFEST.json').read_text())
    frozen={}
    for rel in baseline['files']:
        if rel in ALLOW:continue
        current=(ROOT/rel).read_bytes().replace(b'\r\n',b'\n')
        saved=subprocess.check_output(['git','show',BASE+':'+rel],cwd=ROOT).replace(b'\r\n',b'\n')
        assert current==saved,rel
        frozen[rel]=hashlib.sha256(current).hexdigest()
    # TD native XML has an ampersand in an attribute value, escaped only for
    # structural validation here; do not rewrite its actual vendor format.
    import xml.etree.ElementTree as ET
    ET.fromstring(AL.read_text(encoding='utf-8').replace('::','__').replace('&','_and_'))
    entries=re.findall(r'<File Path="([^"]+)"',AL.read_text(encoding='utf-8'))
    assert len(entries)==66 and len(set(entries))==66
    for run,name in (('syn_1','syn_settings.cfg'),('phy_1','phy_settings.cfg')):
        current=AL.parent/'camera_to_dsi_display_Runs'/run/'settings.cfg'
        assert current.read_bytes()==(ROOT/'artifacts/bitstreams/EDGE_STYLE_FILL_V1/build_evidence'/name).read_bytes()
    out=ROOT/'tmp/edge_style_fill_v2';out.mkdir(exist_ok=True,parents=True)
    result=dict(baseline_tag=BASE,frozen_td_inputs=frozen,allowed_modified_inputs=sorted(ALLOW),
                td_input_count=len(entries),native_project_structure='PASS',td_options_unchanged=True)
    (out/'frozen_inputs.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS frozen TD inputs',len(frozen),'mode integration inputs',len(ALLOW),'STYLE only; TD options unchanged')
if __name__=='__main__':audit()
