"""Create the final acceptance record from actual, immutable test reports.

Requires a completed routed CDC audit; cannot produce PASS from synthesis or
placement alone. Every runtime source manifest is checked against current bytes.
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
from build_style_v2_target_v1 import ROOT, snapshot

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--synthesis',required=True)
    ap.add_argument('--route',required=True);ap.add_argument('--physical-cdc',type=Path,required=True)
    ap.add_argument('--final-system',default='final_system_09')
    ap.add_argument('--fault-system',default='fault_system_13')
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    evidence=ROOT/'docs/evidence/STYLE_V2_TARGET_V1';hashes={}
    def remember(p):hashes[p.relative_to(ROOT).as_posix()]=digest(p)
    def load(p):remember(p);return json.loads(p.read_text())
    before=snapshot();frozen=load(evidence/a.synthesis/'SOURCE_MANIFEST.json')
    for key in ('files','al_sha256','historical_bits'):assert before[key]==frozen[key],key
    for name in (a.final_system,a.fault_system):
        folder=evidence/name;summary=load(folder/'summary.json')
        assert summary['passed'] and summary['source_unchanged']
        sources=load(folder/'SOURCE_MANIFEST.json')
        for rel,expected in sources.items():assert digest(ROOT/rel)==expected,rel
        binding=load(folder/'COMMIT_BINDING.json');assert binding.get('all_project_input_content_matches_commit',binding['all_input_content_matches_commit'])
        remember(folder/'stage_2.txt')
    modes=load(evidence/'five_modes_alignment_10/summary.json');assert modes['passed']
    assert any(j['width']==1280 and j['height']==720 and j['packed_words']==864000 for j in modes['streams'])
    for rel,expected in modes['source_sha256'].items():assert digest(ROOT/rel)==expected,rel
    for name in ('cdc_pulse_11','cdc_registered_11','display_pipeline_09','display_legacy_09',
                 'ledger_latest_eq_08','alignment_full_line_eq_11','alignment_short_eq_12'):
        summary=load(evidence/name/'summary.json');assert summary['passed'],name
    assert load(evidence/'target_handoff_20261022.json')['checks_status']=='PASS'
    cdc_path=a.physical_cdc.resolve();cdc=load(cdc_path)
    assert cdc['passed'] and cdc['database_sha256']==digest(ROOT/'tmp/style_v2_target_v1'/a.route/'route.db')
    assert cdc['implementation_sdc_sha256']==digest(ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.sdc')
    for p in cdc_path.parent.iterdir():
        if p.is_file() and p.suffix in ('.zip','.tcl','.sdc'):remember(p)
    result=dict(passed=True,source_commit=frozen['source_commit'],verification_commit=before['source_commit'],
        full_720p_final_hdmi=True,fault_matrix=True,cdc_review=True,baseline_modes=True,
        physical_cdc_summary=cdc_path.relative_to(ROOT).as_posix(),evidence_sha256=hashes,
        board_test='NOT_RUN',scope='Digital MAIN integration plus unit contracts and as-built routed CDC. See VERIFICATION.md for explicit coverage limits.')
    assert snapshot()==before
    a.out.write_text(json.dumps(result,indent=2)+'\n');print('PASS release gates; board NOT_RUN; source',frozen['source_commit'])

if __name__=='__main__':main()
