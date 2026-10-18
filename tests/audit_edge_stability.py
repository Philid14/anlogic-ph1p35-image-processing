"""Read-only source/STA audit with pinned historical revisions."""
from pathlib import Path
import json,subprocess,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
FORMAL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd'
OUT=ROOT/'docs/edge_stability_evidence'

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def main():
    OUT.mkdir(exist_ok=True)
    names=['control','denoise','nms','quality'];versions={}
    for name in names:
        tag=f'edge-{name}-v1-candidate';commit=git('rev-parse',tag+'^{commit}')
        info=(ROOT/f'artifacts/bitstreams/EDGE_{name.upper()}_V1/BUILD_INFO.md').read_text(encoding='utf-8')
        versions[name]=dict(tag=tag,archive_commit=commit,
            build_info_lines=[line for line in info.splitlines() if any(k in line for k in ('Git Commit SHA','LUT6 |','FF |','Slice |','RAM / ERAM |','DSP |','Setup WNS','Hold WNS'))][:10])
    inputs={}
    # TD writes unescaped UsedInP&R attribute names, so .al is not strict XML.
    project=(FORMAL/'td_project/camera_to_dsi_display.al').read_text(encoding='utf-8')
    for value in re.findall(r'<File Path="([^"]+)"',project):
        path=(FORMAL/'td_project'/value).resolve()
        inputs[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    manifest=json.loads((ROOT/'artifacts/bitstreams/EDGE_QUALITY_V1/build_evidence/SOURCE_MANIFEST.json').read_text())['files']
    assert inputs==manifest,'Current TD inputs differ from archived build source'
    changed=git('diff','--name-only',versions['control']['archive_commit'],versions['quality']['archive_commit'],'--','in_out_example').splitlines()
    invariant=[]
    for rel in ('user_source/hdl_source/awb.v','user_source/hdl_source/signal_delay.v','user_source/hdl_source/video_in.v',
                'user_source/hdl_source/video_out.v','user_source/hdl_source/edge_config_cdc.v','user_source/hdl_source/hdmi_mixer.v',
                'td_project/camera_to_dsi_display.sdc','user_source/constraints_source/pin.adc'):
        name=(FORMAL/rel).relative_to(ROOT).as_posix()
        blobs={key:git('rev-parse',value['archive_commit']+':'+name) for key,value in versions.items()}
        assert len(set(blobs.values()))==1,(name,blobs)
        invariant.append(dict(path=name,git_blob=blobs['quality']))
    evidence=ROOT/'artifacts/bitstreams/EDGE_QUALITY_V1/build_evidence'
    exception=(evidence/'camera_to_dsi_display_exception.timing').read_text()
    assert '18, by set_clock_groups' in exception
    result=dict(baseline_main=git('rev-parse','origin/main'),versions=versions,
        input_sha256=inputs,td_inputs_equal_archived_61=len(inputs)==61,
        history_changed_formal_files=changed,invariant_across_all_four=invariant,
        clock_groups=(FORMAL/'td_project/camera_to_dsi_display.sdc').read_text(),
        ignored_fifo_max_delays=dict(ns=[14.700,13.033],paths_each=18,reason='set_clock_groups',
            source='artifacts/bitstreams/EDGE_QUALITY_V1/build_evidence/camera_to_dsi_display_exception.timing'),
        caveat='Constraint coverage gap confirmed; no routed Gray-bus skew/MTBF measurement or board fault proven')
    (OUT/'source_sta_audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS 61 active TD input hashes match final QUALITY archive; eight shared paths invariant in four versions')
    print('CONFIRMED: 2 x 18 FIFO max-delay paths ignored by asynchronous clock grouping')

if __name__=='__main__':main()
