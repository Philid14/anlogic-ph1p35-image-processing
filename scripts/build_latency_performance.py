"""Committed production SYN/PHY/STA/bitgen, strict baseline and regression gates."""
import json,re,sys,shutil
from pathlib import Path
import build_track_region_fix as build
ROOT=build.ROOT;P=build.P;HDL=build.HDL
BASE='072bc0f8858ceb3009659f8df7cb02b9da05ed36'
OUT=ROOT/'tmp/latency_performance/full_r1'
CHANGED={HDL+p for p in ('design_top_wrapper.v','video_in.v','video_out.v','mc_to_user_interface.v','hdmi_mixer.v',
 'isp/edge_link_pair_3x3.v','isp/gaussian_pair_3x3.v','isp/nms_gradient_pair_3x3.v','vision/inspection_config_delay.v')}
ADDED={HDL+'vision/'+p for p in ('edge_row_history.v','latency_capture_tag.v','latency_slot_journal.v','latency_tagged_fifo.v','latency_osd.v','latency_font.dath')}
EXPERIMENTAL={HDL+'vision/inspection_payload_delay.v'} # Not a formal compilation input.

def snapshot():
    head=build.git('rev-parse','HEAD').decode().strip()
    entries=re.findall(r'<File Path="([^"]+)"',(P/'camera_to_dsi_display.al').read_text(encoding='utf-8'))
    assert len(entries)==91
    baseline=json.loads((ROOT/'artifacts/bitstreams/TRACK_REGION_FIX_V1/build_evidence/SOURCE_MANIFEST.json').read_text())['files']
    files={}
    for entry in entries+[f'../user_source/hdl_source/vision/{n}' for n in ('vision_logo_index.dath','vision_logo_palette.dath','inspection_font.dath','latency_font.dath')]:
        path=(P/entry).resolve();rel=path.relative_to(ROOT).as_posix()
        data=path.read_bytes().replace(b'\r\n',b'\n')
        assert data==build.git('show',head+':'+rel).replace(b'\r\n',b'\n'),rel+' not committed'
        if rel in baseline and rel not in CHANGED:
            assert data==build.git('show',BASE+':'+rel).replace(b'\r\n',b'\n'),rel+' changed outside scope'
        files[rel]=build.sha(path)
    assert set(files)==set(baseline)|ADDED
    for run,name in [('syn_1','syn_settings.cfg'),('phy_1','phy_settings.cfg')]:
        assert (P/'camera_to_dsi_display_Runs'/run/'settings.cfg').read_bytes()==(ROOT/'artifacts/bitstreams/TRACK_REGION_FIX_V1/build_evidence'/name).read_bytes(),run+' settings changed'
    changed=build.git('diff','--name-only',BASE,'--',HDL,HDL.replace('hdl_source/','ip_source/')).decode().splitlines()
    assert set(changed)<=CHANGED|ADDED|EXPERIMENTAL,changed
    provenance=json.loads((ROOT/'docs/evidence/VISION_TRACK_MOTION_V1/TARGET_SOURCE.json').read_text())
    for item in provenance['files']:assert build.sha(ROOT/item['path'])==item['sha256']
    return dict(source_commit=head,baseline=BASE,files=files,al_sha256=build.sha(P/'camera_to_dsi_display.al'),
      old_bits={p.relative_to(ROOT).as_posix():build.sha(p) for p in (ROOT/'artifacts/bitstreams').glob('*/*.bit')})

def regression_gate():
    folders=[ROOT/'tmp/latency_performance'/p for p in ('memory','rows','units','fifo','osd','video_path')]
    folders +=[ROOT/'tmp/latency_performance/regression'/p for p in ('font','shape','drawing','track','config','reset','select','contract','legacy','integrated','background_full','track_stream')]
    evidence={}
    for folder in folders:
        result=folder/'results.json';data=json.loads(result.read_text());assert data['passed'],folder
        for name,digest in data.get('sources',{}).items():assert build.sha(ROOT/name)==digest,name+' changed after test'
        evidence[result.relative_to(ROOT).as_posix()]=build.sha(result)
        native=list(folder.rglob('SIM_SOURCE_MANIFEST.json'))
        if folder.name!='contract':assert native,folder
        for manifest in native:
            hashes=json.loads(manifest.read_text())
            for name,digest in hashes.items():
                path=Path(name);assert build.sha(path)==digest,name+' changed after test'
                for staging in ('staging','retime_staging'):
                    stage=ROOT/'tmp/latency_performance'/staging
                    if path.is_relative_to(stage):
                        actual=ROOT/HDL/path.relative_to(stage)
                        assert build.sha(actual)==digest,'staging differs from formal source '+name
            evidence[manifest.relative_to(ROOT).as_posix()]=build.sha(manifest)
    return evidence

def bit():
    current=snapshot();frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text())
    for key in ('files','al_sha256','old_bits'):assert current[key]==frozen[key]
    tests=regression_gate()
    phy=P/'camera_to_dsi_display_Runs/phy_1';database=phy/'camera_to_dsi_display_pr.db'
    assert build.sha(database)==(OUT/'ROUTE_DB_SHA256.txt').read_text().strip()
    cdc=json.loads((OUT/'cdc/results.json').read_text())
    assert cdc['passed'] and cdc['route_db_sha256']==build.sha(database),'New CDC audit must cover this exact route'
    timing=(OUT/'phy_camera_to_dsi_display_phy.ts').read_text()
    sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',timing))
    assert sw>=0 and hw>=0 and st==ht==0
    target=OUT/'camera_to_dsi_display.bit';assert not target.exists()
    text='source ./settings.cfg\nimport_device ph1_35p.db -package PH1P35MDG324 -speed 3\nopen_project camera_to_dsi_display.prj -noanalyze\nimport_db {'+database.as_posix()+'}\ncommit_param -step bitgen\nbitgen -bit {'+target.as_posix()+'}\nexport_bitgen_param -file {'+(OUT/'bitgen_params.txt').as_posix()+'}\nputs "BIT_COMPLETE"\nexit\n'
    build.run('bit',text,phy)
    assert target.stat().st_size>1000000 and build.sha(target) not in current['old_bits'].values()
    assert regression_gate()==tests
    (OUT/'REGRESSION_GATE.json').write_text(json.dumps(tests,indent=2)+'\n')
    after=snapshot()
    for key in ('files','al_sha256','old_bits'):assert after[key]==current[key]
    print('PASS bitgen; board NOT_RUN')

if __name__=='__main__':
    build.OUT=OUT;build.snapshot=snapshot
    if sys.argv[-1]=='bit':bit()
    else:build.main()
