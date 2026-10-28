"""Archive only a fresh, timing-clean COLOR_COMPARE_V1 build and its evidence."""
import json,hashlib,re,shutil,datetime,subprocess,zipfile
from build_color_compare_v1 import ROOT,P,OUT,snapshot,sha

def main():
    frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text());current=snapshot()
    for key in ('files','al_sha256','old_bits'):assert current[key]==frozen[key],key
    full=json.loads((ROOT/'tmp/color_compare_v1/full_results.json').read_text())
    assert full['stream']==dict(width=1280,height=720,beats=1152000,packed_words=864000,compare_enabled=True)
    for path,digest in full['sources'].items():assert sha(ROOT/path)==digest,path
    formatter=json.loads((ROOT/'tmp/color_compare_v1/formatter_results.json').read_text());assert formatter['passed'] and formatter['fields']==2398
    for stage in ('syn','phy','bit'):
        text=(OUT/(stage+'_stdout.txt')).read_text(errors='replace')
        assert stage.upper()+'_COMPLETE' in text and not re.search(r'\bERROR\s*:',text),stage
    selected=json.loads((OUT/'SELECTED_ROUTE.json').read_text()) if (OUT/'SELECTED_ROUTE.json').exists() else None
    timing=Path(selected['timing_report']) if selected else OUT/'phy_camera_to_dsi_display_phy.ts'
    sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',timing.read_text()))
    assert sw>=0 and hw>=0 and st==ht==0
    area=(Path(selected['area_report']) if selected else OUT/'phy_camera_to_dsi_display_phy.area').read_text()
    def number(n):return int(re.search(r'^#'+re.escape(n)+r'\s+(\d+)',area,re.M)[1])
    resources={k:number(n) for k,n in [('slice','slice'),('lut6','lut6'),('ff','reg'),('eram','eram'),('dsp','dsp')]}
    assert resources['slice']<=21216 and resources['eram']<=108 and resources['dsp']<=40
    bit=OUT/'camera_to_dsi_display.bit';assert bit.stat().st_size>1_000_000 and sha(bit) not in frozen['old_bits'].values()
    assert bit.stat().st_mtime>=datetime.datetime.fromisoformat(frozen['time']).timestamp()
    result=dict(version='COLOR_COMPARE_V1',branch='codex/main/color-compare-v1',source_commit=frozen['source_commit'],
        archive_driver_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        tag='color-compare-v1-candidate',bit_sha256=sha(bit),resources=resources,setup_wns_ns=sw,hold_wns_ns=hw,
        setup_tns_ns=st,hold_tns_ns=ht,board_test='NOT_RUN',extra_stream_cycles=2,
        route_db_sha256=selected['database_sha256'] if selected else (OUT/'ROUTE_DB_SHA256.txt').read_text().strip(),
        baseline='edge-style-fill-v2-candidate',measurement='same complete pre-effect post-AWB frame, both 128x128 ROIs; LAST labels previous sample frame; not CIE Delta E')
    result['resource_delta_vs_STYLE_V2']={k:resources[k]-v for k,v in dict(slice=18140,lut6=17170,ff=16814,eram=85,dsp=21).items()}
    logs='\n'.join((OUT/(s+'_stdout.txt')).read_text(errors='replace') for s in ('syn','phy','bit'))
    if (OUT/'polish01/stdout.txt').exists():logs+='\n'+(OUT/'polish01/stdout.txt').read_text(errors='replace')
    result['critical_warning_types']=sorted(set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',logs)))
    oldlogs='\n'.join(p.read_text(errors='replace') for p in (ROOT/'artifacts/bitstreams/EDGE_STYLE_FILL_V2/build_evidence').glob('*.log'))
    result['new_critical_warning_types']=sorted(set(result['critical_warning_types'])-set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',oldlogs)))
    dest=ROOT/'artifacts/bitstreams/COLOR_COMPARE_V1';assert not dest.exists(),'never overwrite historical bit'
    evidence=dest/'build_evidence';evidence.mkdir(parents=True);shutil.copy2(bit,dest/bit.name)
    for file in OUT.iterdir():
        if file.is_file() and file.suffix in ('.txt','.json','.tcl','.cfg','.area','.ts','.rpt','.qor','.timing','.prj'):shutil.copy2(file,evidence/file.name)
    if (OUT/'polish01').exists():
        sub=evidence/'polish01';sub.mkdir()
        for f in (OUT/'polish01').iterdir():
            if f.is_file() and f.suffix!='.db':shutil.copy2(f,sub/f.name)
    for name in ('full_results.json','full_console.txt','small_results.json','small_console.txt','legacy_console.txt','formatter_results.json','formatter_console.txt','style_unit_console.txt','build_syn_console.txt'):
        if (ROOT/'tmp/color_compare_v1'/name).exists():shutil.copy2(ROOT/'tmp/color_compare_v1'/name,evidence/name)
    (evidence/'VECTOR_DIGESTS.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'tmp/color_compare_v1/full').glob('*.txt')},indent=2)+'\n')
    # The actual full Icarus run passed original RTL. Optional native compiler
    # acceleration attempts are not treated as validation passes.
    (evidence/'VALIDATION_SCOPE.md').write_text('Full five-mode pass uses actual, unmodified production RTL in Icarus. Demosaic/AWB are explicit post-AWB boundary stubs. No physical MIPI/DDR/HDMI or board proof. Optional ModelSim acceleration: first two compilation attempts rejected an existing forward low_threshold declaration; a declaration-order-only simulation copy was attempted, then its duplicate run was stopped once original Icarus passed. These native attempts are not counted as PASS. Source RTL was not changed for this compiler issue.\n')
    (dest/'BUILD_INFO.json').write_text(json.dumps(result,indent=2)+'\n')
    info=f'''# COLOR_COMPARE_V1 BUILD_INFO

- Version: COLOR_COMPARE_V1 / MAIN
- Branch: codex/main/color-compare-v1
- Actual TD source commit: {frozen['source_commit']}
- Candidate tag: color-compare-v1-candidate (created separately after archive review)
- Build time: {datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()}
- Device / Top: PH1P35MDG324 speed3 / design_top_wrapper
- Baseline: edge-style-fill-v2-candidate (8d26c6eba95f07723b0f634efa82ed1424218975)
- Original bit path: {bit.as_posix()}
- Bit SHA-256: {sha(bit)}
- Resources: {json.dumps(resources)}
- Delta versus STYLE_V2: {json.dumps(result['resource_delta_vs_STYLE_V2'])}
- Routed Setup WNS: {sw:+.3f}ns; Hold WNS: {hw:+.3f}ns; Setup/Hold TNS: {st}/{ht}ns
- Build: Synthesis -> Physical Design -> final Timing Check -> bitgen PASS
- Critical warnings: {result['critical_warning_types']}; new types: {result['new_critical_warning_types']}
- Frame/line cache, algorithms, Sensor/ISP, DDR/MIPI/HDMI, clocks and SDC are unchanged from STYLE_V2; only comparison overlay adds two stream clocks. No TARGET ledger or diagnostic ROI capture included.
- Known inherited risk: FIFO overflow sticky/Gray-pointer constraint coverage are not fixed or board-validated by this task. New color modules introduce no CDC or framebuffer. See design/board-test documents.
- Board Test Status: NOT_RUN. Full post-AWB model/RTL/packer regression and STA do not prove actual camera/display or calibrated color accuracy.
- Metrics: camera RGB means/differences and nine coarse classes; MATCH max channel difference <=12 is a demo criterion, not CIE Lab/Delta E or industrial conformance.
- Rollback: artifacts/bitstreams/EDGE_STYLE_FILL_V2/camera_to_dsi_display.bit, SHA256 CFB7435648ED50310F053AFE138702F2094B0061B6A7DD68B3B064B6B3D88F51.
'''
    (dest/'BUILD_INFO.md').write_text(info,encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
