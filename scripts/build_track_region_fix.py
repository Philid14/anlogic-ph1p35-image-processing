"""TRACK_REGION_FIX_V1 build with explicit SYN/PHY/STA/bitgen gates, never stale bit.

Only MAIN target observation changes; imported TARGET RTL and all other inputs frozen.
User dirty research notes are preserved and excluded from actual TD inputs.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,shutil,datetime
import prepare_td_runs
ROOT=Path(__file__).resolve().parents[1]
P=prepare_td_runs.PROJECT
OUT=ROOT/'tmp/track_region_fix/full_r1'
HDL='in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/'
BASE='4d0f779cefd680363b8a3f0d4d5c33a42d81197f'
CHANGED={HDL+'vision/vision_source_observer.v'}
ADDED=set()
TD=Path('D:/TD/bin/td_commands_prompt.exe')
FLOW=Path('D:/TD/doc/scripts/DefaultFlow.tcl')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)

def snapshot():
    head=git('rev-parse','HEAD').decode().strip()
    entries=re.findall(r'<File Path="([^"]+)"',(P/'camera_to_dsi_display.al').read_text(encoding='utf-8'))
    assert len(entries)==86 and not any('temporal_roi' in x or 'target_frame_system' in x for x in entries)
    baseline=json.loads((ROOT/'artifacts/bitstreams/INSPECTION_SHAPE_TRACK_V1/build_evidence/SOURCE_MANIFEST.json').read_text())['files']
    files={}
    for entry in entries:
        path=(P/entry).resolve();rel=path.relative_to(ROOT).as_posix()
        assert path.read_bytes().replace(b'\r\n',b'\n')==git('show',head+':'+rel).replace(b'\r\n',b'\n'),rel+' is not committed'
        files[rel]=sha(path)
        if rel in baseline and rel not in CHANGED:
            # Windows checkout may expand LF to CRLF; prove the committed
            # baseline content instead of mistaking line endings for RTL edits.
            original=git('show',BASE+':'+rel)
            assert path.read_bytes().replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n'),rel+' changed from INSPECTION_SHAPE_TRACK_V1'
    provenance=json.loads((ROOT/'docs/evidence/VISION_TRACK_MOTION_V1/TARGET_SOURCE.json').read_text())
    for item in provenance['files']:
        assert sha(ROOT/item['path'])==item['sha256'],item['path']
    for name in ('vision_logo_index.dath','vision_logo_palette.dath','inspection_font.dath'):
        rel=HDL+'vision/'+name;path=ROOT/rel
        assert path.read_bytes().replace(b'\r\n',b'\n')==git('show',head+':'+rel).replace(b'\r\n',b'\n')
        files[rel]=sha(path)
    assert set(files)==set(baseline)|ADDED
    for run,name in [('syn_1','syn_settings.cfg'),('phy_1','phy_settings.cfg')]:
        assert (P/'camera_to_dsi_display_Runs'/run/'settings.cfg').read_bytes()==(ROOT/'artifacts/bitstreams/INSPECTION_SHAPE_TRACK_V1/build_evidence'/name).read_bytes(),run+' settings changed'
    # Formal main ownership: teammate directories, Sensor, DDR, MIPI and HDMI
    # are also frozen by source diff, not just the directly listed .al files.
    changed=git('diff','--name-only',BASE,'--',HDL,HDL.replace('user_source/hdl_source/','user_source/ip_source/')).decode().splitlines()
    assert set(changed)<=CHANGED|ADDED,changed
    return dict(source_commit=head,files=files,al_sha256=sha(P/'camera_to_dsi_display.al'),old_bits={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'artifacts/bitstreams').glob('*/*.bit')},time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),baseline=BASE,unchanged_baseline_inputs=len(baseline)-len(CHANGED))

def run(stage,flow,working):
    script=OUT/(stage+'.tcl');script.write_text(flow)
    with (OUT/(stage+'_stdout.txt')).open('wb') as log:
        rc=subprocess.run([TD.as_posix(),script.as_posix()],cwd=working,stdout=log,stderr=subprocess.STDOUT).returncode
    text=(OUT/(stage+'_stdout.txt')).read_text(errors='replace')
    assert rc==0 and stage.upper()+'_COMPLETE' in text and not re.search(r'\bERROR\s*:',text),(stage,rc)

def main():
    a=argparse.ArgumentParser();a.add_argument('--stage',choices=['syn','phy','bit'],required=True);args=a.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    current=snapshot();manifest=OUT/'SOURCE_MANIFEST.json'
    if args.stage=='syn':
        assert not manifest.exists(),'Do not overwrite a build attempt'
        manifest.write_text(json.dumps(current,indent=2)+'\n')
    else:
        frozen=json.loads(manifest.read_text())
        for k in ('files','al_sha256','old_bits'):assert current[k]==frozen[k],k
    syn=P/'camera_to_dsi_display_Runs/syn_1';phy=P/'camera_to_dsi_display_Runs/phy_1'
    if args.stage=='syn':
        prepare_td_runs.main()
        run('syn','source {'+FLOW.as_posix()+'}\nputs "SYN_COMPLETE"\nexit\n',syn)
        (OUT/'SYN_DB_SHA256.txt').write_text(sha(syn/'camera_to_dsi_display_gate.db')+'\n')
        for name in ('camera_to_dsi_display_gate.area','camera_to_dsi_display_gate.ts','camera_to_dsi_display.prj','settings.cfg'):
            shutil.copy2(syn/name,OUT/('syn_'+name))
    elif args.stage=='phy':
        assert sha(syn/'camera_to_dsi_display_gate.db')==(OUT/'SYN_DB_SHA256.txt').read_text().strip()
        text=FLOW.read_text();old='if { ![info exists alRun] } { source ./settings.cfg }';assert old in text
        text=text.replace(old,'source ./settings.cfg\nset end_step opt_route',1)
        text+='\nreport_timing_summary -file final_timing.rpt -ep_num 10 -path_num 1\nreport_timing_ignored -file ignored_timing.rpt\nputs "PHY_COMPLETE"\nexit\n'
        run('phy',text,phy)
        for name in ('camera_to_dsi_display_phy.area','camera_to_dsi_display_phy.ts','route.qor','final_timing.rpt','ignored_timing.rpt','camera_to_dsi_display_exception.timing','route_clock_utilization.txt','settings.cfg'):
            shutil.copy2(phy/name,OUT/('phy_'+name))
        (OUT/'ROUTE_DB_SHA256.txt').write_text(sha(phy/'camera_to_dsi_display_pr.db')+'\n')
        timing=(OUT/'phy_camera_to_dsi_display_phy.ts').read_text();print(timing,flush=True)
        sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',timing))
        assert sw>=0 and hw>=0 and st==ht==0,'Timing failed; no bitgen'
    else:
        for path in ('tmp/track_region_fix/shape','tmp/track_region_fix/font','tmp/track_region_fix/legacy','tmp/track_region_fix/track','tmp/track_region_fix/drawing','tmp/track_region_fix/integrated','tmp/track_region_fix/reset','tmp/track_region_fix/config','tmp/track_region_fix/background_full','tmp/track_region_fix/select','tmp/track_region_fix/contract','tmp/track_region_fix/track_stream','tmp/track_region_fix/region','tmp/track_region_fix/region_full'):
            check=json.loads((ROOT/path/'results.json').read_text());assert check['passed']
            for rel,digest in check['sources'].items():assert sha(ROOT/rel)==digest,rel
        for path in ('tmp/track_region_fix/shape','tmp/track_region_fix/font','tmp/track_region_fix/legacy','tmp/track_region_fix/track','tmp/track_region_fix/drawing','tmp/track_region_fix/integrated','tmp/track_region_fix/reset','tmp/track_region_fix/config','tmp/track_region_fix/background_full','tmp/track_region_fix/track_stream','tmp/track_region_fix/region','tmp/track_region_fix/region_full'):
            native=json.loads((ROOT/path/'SIM_SOURCE_MANIFEST.json').read_text())
            for rel,digest in native.items():assert sha(Path(rel))==digest,rel
        selected=json.loads((OUT/'SELECTED_ROUTE.json').read_text()) if (OUT/'SELECTED_ROUTE.json').exists() else None
        database=Path(selected['route_database']) if selected else phy/'camera_to_dsi_display_pr.db'
        assert sha(database)==(selected['database_sha256'] if selected else (OUT/'ROUTE_DB_SHA256.txt').read_text().strip())
        timing=Path(selected['timing_report']) if selected else OUT/'phy_camera_to_dsi_display_phy.ts'
        sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',timing.read_text()))
        assert sw>=0 and hw>=0 and st==ht==0
        bit=OUT/'camera_to_dsi_display.bit';assert not bit.exists()
        text='source ./settings.cfg\nimport_device ph1_35p.db -package PH1P35MDG324 -speed 3\nopen_project camera_to_dsi_display.prj -noanalyze\nimport_db {'+database.as_posix()+'}\ncommit_param -step bitgen\nbitgen -bit {'+bit.as_posix()+'}\nexport_bitgen_param -file {'+(OUT/'bitgen_params.txt').as_posix()+'}\nputs "BIT_COMPLETE"\nexit\n'
        run('bit',text,phy)
        assert bit.is_file() and bit.stat().st_size>1_000_000 and sha(bit) not in current['old_bits'].values()
    after=snapshot()
    for key in ('files','al_sha256','old_bits'):assert after[key]==current[key],key+' changed during build'
    print('PASS',args.stage,'actual TD inputs unchanged; board NOT_RUN',flush=True)
if __name__=='__main__':main()
