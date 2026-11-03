"""Extract final routed V2 evidence without assuming V1 critical paths/slack."""
from pathlib import Path
import collections,json,re
ROOT=Path(__file__).resolve().parents[1]
NEW=ROOT/'artifacts/bitstreams/EDGE_STYLE_FILL_V2/build_evidence'
OLD=ROOT/'artifacts/bitstreams/EDGE_STYLE_FILL_V1/build_evidence'
def warnings(folder):
    return [l for p in folder.glob('*.log') if p.name.startswith(('syn_td_','phy_td_'))
            for l in p.read_text(errors='replace').splitlines()
            if re.search(r'\w+-\d+ (?:CRITICAL-)?WARNING:',l)]
def main():
    checks=json.loads((NEW/'FINAL_CHECKS.json').read_text())
    oldchecks=json.loads((OLD/'FINAL_CHECKS.json').read_text())
    new,old=warnings(NEW),warnings(OLD)
    code=lambda l:re.search(r'\w+-\d+',l)[0]
    nc,oc=collections.Counter(map(code,new)),collections.Counter(map(code,old))
    normalize=lambda s:re.sub(r'_syn_\d+','_syn_N',s)
    timing=(NEW/'final_timing.rpt').read_text(errors='replace')
    slack=f"{checks['setup_wns_ns']:.3f}"
    match=re.search(r'Slack\s*:\s*'+re.escape(slack)+r'ns',timing)
    assert match,'cannot locate actual worst setup path'
    part=timing[match.start():match.start()+1300]
    fields={k:re.search(k+r'\s*:\s*([^\n]+)',part)[1].strip() for k in ('Slack','Begin Point','End Point')}
    area=(NEW/'camera_to_dsi_display_phy.area').read_text()
    module=next(l for l in area.splitlines() if '|style_fill_96 ' in l)
    exception=(NEW/'camera_to_dsi_display_exception.timing').read_text()
    for value in ('14.700','13.033'):
        assert re.search(r'18\s+0\s+0\s+18\s+set_max_delay[^\n]*'+value,exception),value
    result=dict(warning_counts_new=nc,warning_counts_baseline=oc,
        warning_count_delta={k:nc[k]-oc[k] for k in nc.keys()|oc.keys() if nc[k]!=oc[k]},
        added_normalized_warning_contexts=sorted(set(map(normalize,new))-set(map(normalize,old))),
        new_style_warning_contexts=[l for l in new if 'style_fill_96.v' in l],
        critical_setup_path=fields,style_routed_area_row=module,
        sta_coverage_new=checks['sta_coverage'],sta_coverage_baseline=oldchecks['sta_coverage'],
        gray_max_delay=dict(path_counts=[18,18],limits_ns=[14.700,13.033],ignored=[18,18],status='existing unresolved risk'),
        clock_region_warning=dict(buffer='u_uicfgcs500/u_i2c/scl_clk_created_gclkinst',
            driver_region='TOP',buffer_region='BOTTOM',source='analyze_clock -detail on final routed DB; clock_review.log',
            source_rtl_unchanged=True,board_cold_start_check='required; do not treat clock region warning as resolved'),
        note='Whole-design resource delta includes TD remapping/packing. Gate RAM inspection is not SDF simulation. Hardware image quality and B/S remain unverified.')
    (NEW/'BUILD_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
