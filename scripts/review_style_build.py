"""Compare actual routed resources, warning contexts and critical path."""
from pathlib import Path
import collections,json,re
ROOT=Path(__file__).resolve().parents[1]
NEW=ROOT/'artifacts/bitstreams/EDGE_STYLE_FILL_V1/build_evidence'
OLD=ROOT/'artifacts/bitstreams/EDGE_MULTI_MODE_V1/build_evidence'
def warning_lines(folder):
    return [line for p in folder.glob('*.log') if p.name.startswith(('syn_td_','phy_td_'))
        for line in p.read_text(errors='replace').splitlines()
        if re.search(r'\w+-\d+ (?:CRITICAL-)?WARNING:',line)]
def main():
    new,old=warning_lines(NEW),warning_lines(OLD)
    code=lambda line:re.search(r'\w+-\d+',line)[0]
    nc,oc=collections.Counter(map(code,new)),collections.Counter(map(code,old))
    delta={k:nc[k]-oc[k] for k in sorted(nc.keys()|oc.keys()) if nc[k]!=oc[k]}
    normalize=lambda s:re.sub(r'_syn_\d+','_syn_N',s)
    old_context=set(map(normalize,old))
    added=sorted(set(map(normalize,new))-old_context)
    timing=(NEW/'final_timing.rpt').read_text(errors='replace')
    p=timing.index('Slack               : 0.104ns')
    part=timing[p:p+1300]
    fields={key:re.search(key+r'\s*:\s*([^\n]+)',part)[1].strip() for key in ('Slack','Begin Point','End Point')}
    area=(NEW/'camera_to_dsi_display_phy.area').read_text()
    module=next(line for line in area.splitlines() if '|style_fill_96 ' in line)
    result=dict(warning_counts_new=nc,warning_counts_baseline=oc,warning_count_delta=delta,
        added_normalized_warning_contexts=added,new_style_warning_contexts=[x for x in new if 'style_fill_96.v' in x],
        critical_setup_path=fields,style_routed_area_row=module,
        sta_coverage_new='95.99%',sta_coverage_baseline='96.16%',
        gray_max_delay=dict(path_counts=[18,18],limits_ns=[14.700,13.033],ignored=[18,18],status='existing unresolved risk'),
        note='Whole-design resource deltas include TD optimization and packing; local STYLE is not free. STA coverage remains incomplete; no global SDC changes.')
    (NEW/'BUILD_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
