"""Archive a fresh timing-clean build and exact functional evidence."""
from pathlib import Path
import datetime,json,re,shutil,subprocess
from build_inspection_ui_dimension_v1 import ROOT,P,OUT,snapshot,sha
VERSION='INSPECTION_UI_DIMENSION_V1'
def main():
    frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text());now=snapshot()
    for key in ('files','al_sha256','old_bits'):assert now[key]==frozen[key],key
    full=json.loads((ROOT/'tmp/metrology_v1/full_results.json').read_text())
    assert full['passed'] and full['beats']==1382400 and full['words']==1036800
    for path,digest in full['sources'].items():assert sha(ROOT/path)==digest,path
    mixer=json.loads((ROOT/'tmp/metrology_v1/mixer/results.json').read_text());assert mixer['passed']
    for path,digest in mixer['sources'].items():assert sha(ROOT/path)==digest,path
    unit=json.loads((ROOT/'tmp/metrology_v1/unit/results.json').read_text());assert unit['passed'] and unit['frames']==160
    ui=json.loads((ROOT/'tmp/metrology_v1/ui/results.json').read_text());assert ui['passed'] and ui['full_frame_beats']==691200
    scope=json.loads((ROOT/'tmp/metrology_v1/SOURCE_SCOPE.json').read_text());assert scope['passed']
    for stage in ('syn','phy','bit'):
        text=(OUT/(stage+'_stdout.txt')).read_text(errors='replace')
        assert stage.upper()+'_COMPLETE' in text and not re.search(r'\bERROR\s*:',text),stage
    selected=json.loads((OUT/'SELECTED_ROUTE.json').read_text()) if (OUT/'SELECTED_ROUTE.json').exists() else None
    timing=(Path(selected['timing_report']) if selected else OUT/'phy_camera_to_dsi_display_phy.ts').read_text()
    sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',timing))
    assert sw>=0 and hw>=0 and st==ht==0
    area=(Path(selected['area_report']) if selected else OUT/'phy_camera_to_dsi_display_phy.area').read_text()
    number=lambda n:int(re.search(r'^#'+re.escape(n)+r'\s+(\d+)',area,re.M)[1])
    resources={k:number(n) for k,n in [('slice','slice'),('lut6','lut6'),('ff','reg'),('eram','eram'),('dsp','dsp')]}
    assert resources['slice']<=21216 and resources['eram']<=108 and resources['dsp']<=40
    bit=OUT/'camera_to_dsi_display.bit'
    assert bit.stat().st_size>1_000_000 and sha(bit) not in frozen['old_bits'].values()
    assert bit.stat().st_mtime>=datetime.datetime.fromisoformat(frozen['time']).timestamp()
    result=dict(version=VERSION,branch='codex/main/inspection-ui-dimension-v1',
        source_commit=frozen['source_commit'],archive_driver_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        tag='inspection-ui-dimension-v1-candidate',bit_sha256=sha(bit),resources=resources,
        setup_wns_ns=sw,hold_wns_ns=hw,setup_tns_ns=st,hold_tns_ns=ht,board_test='NOT_RUN',
        extra_stream_cycles_vs_COLOR_COMPARE_V1=0,baseline='color-compare-v1-candidate',
        route_db_sha256=selected['database_sha256'] if selected else (OUT/'ROUTE_DB_SHA256.txt').read_text().strip(),
        selected_post_route_polish=bool(selected),
        dimensions='single thin silhouette, axis-aligned extents and center-line gaps; manual two-axis 100mm ruler calibration; 0.1mm display is not accuracy')
    previous=json.loads((ROOT/'artifacts/bitstreams/COLOR_COMPARE_V1/BUILD_INFO.json').read_text())
    result['resource_delta_vs_COLOR_COMPARE_V1']={k:resources[k]-v for k,v in previous['resources'].items()}
    logs='\n'.join((OUT/(s+'_stdout.txt')).read_text(errors='replace') for s in ('syn','phy','bit'))
    result['critical_warning_types']=sorted(set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',logs)))
    result['new_critical_warning_types']=sorted(set(result['critical_warning_types'])-set(previous['critical_warning_types']))
    dest=ROOT/'artifacts/bitstreams'/VERSION;assert not dest.exists(),'Never overwrite old artifacts'
    evidence=dest/'build_evidence';evidence.mkdir(parents=True);shutil.copy2(bit,dest/bit.name)
    for f in OUT.iterdir():
        if f.is_file() and f.suffix in ('.txt','.json','.tcl','.cfg','.area','.ts','.rpt','.qor','.timing','.prj'):
            shutil.copy2(f,evidence/f.name)
    if (OUT/'polish01').exists():
        target=evidence/'polish01';target.mkdir()
        for f in (OUT/'polish01').iterdir():
            if f.is_file() and f.suffix!='.db':shutil.copy2(f,target/f.name)
    failed=ROOT/'tmp/metrology_v1/r0';failure=evidence/'r0_adc_comment_failure';failure.mkdir()
    for name in ('SOURCE_MANIFEST.json','syn.tcl','syn_stdout.txt'):
        if(failed/name).exists():shutil.copy2(failed/name,failure/name)
    (failure/'README.md').write_text('First SYN stopped on a newly added // ADC comment (ADC is Tcl). No implementation or bit. Changed only that comment to #, committed 103f625 and rebuilt as r1. Failure preserved.\n')
    withdrawn=ROOT/'tmp/metrology_v1/r1';target=evidence/'r1_withdrawn';target.mkdir()
    for f in withdrawn.iterdir():
        if f.is_file() and f.suffix in ('.txt','.json','.tcl','.cfg','.area','.ts','.rpt','.qor','.timing','.prj'):
            shutil.copy2(f,target/f.name)
    (target/'README.md').write_text('r1 source 103f625, functional full six-frame regression passed, but routed setup -1.276ns failed in the original Logo ROM address path. Also withdrew proposed A9/K2 pin after detailed supply review revealed 1.5V pull-up. No bitgen or board use. r2 reuses C7/K4, updates CAL labels and retimes only Logo address into an existing pipeline slot; mixer cycle-equivalence is gated before bitgen.\n')
    for sub in ('unit','ui','legacy','full','small','mixer'):
        d=ROOT/'tmp/metrology_v1'/sub;target=evidence/sub;target.mkdir()
        for f in d.glob('*.txt'):
            if f.name.endswith('_console.txt') or f.name=='console.txt':shutil.copy2(f,target/f.name)
        for f in d.glob('*.json'):shutil.copy2(f,target/f.name)
    for name in ('full_results.json','small_results.json','SOURCE_SCOPE.json'):
        shutil.copy2(ROOT/'tmp/metrology_v1'/name,evidence/name)
    # Original STYLE pixel regression evidence was regenerated with frozen RTL.
    shutil.copy2(ROOT/'tmp/edge_style_fill_v2/unit_results.json',evidence/'STYLE_UNIT_RESULTS.json')
    for name in ('formatter_results.json','formatter_console.txt'):
        shutil.copy2(ROOT/'tmp/color_compare_v1'/name,evidence/('color_'+name))
    (evidence/'VECTOR_DIGESTS.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'tmp/metrology_v1/full').glob('*.txt')},indent=2)+'\n')
    (dest/'BUILD_INFO.json').write_text(json.dumps(result,indent=2)+'\n')
    info=f'''# {VERSION} BUILD_INFO

- Version / Role: {VERSION} / MAIN
- Branch: codex/main/inspection-ui-dimension-v1
- Actual TD source commit: {frozen['source_commit']}
- Candidate tag: inspection-ui-dimension-v1-candidate (created after archive)
- Build time: {datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()}
- Device / Top: PH1P35MDG324 speed3 / design_top_wrapper
- Original bit path: {bit.as_posix()}
- Bit SHA256: {sha(bit)}
- Resource: {json.dumps(resources)}
- Delta vs COLOR_COMPARE_V1: {json.dumps(result['resource_delta_vs_COLOR_COMPARE_V1'])}
- Setup WNS / TNS: {sw:+.3f}ns / {st}; Hold WNS / TNS: {hw:+.3f}ns / {ht}
- Synthesis -> Physical Design -> final STA -> bitgen: PASS
- Critical warning types: {result['critical_warning_types']}; new: {result['new_critical_warning_types']}
- Board Test Status: NOT_RUN. User must validate switches/pins, display, dimensional accuracy, lighting and long-term stability.
- No extra pixel latency vs COLOR_COMPARE_V1; same 31-cycle five-mode/OSD alignment (including its two comparison clocks). Metrics describe preceding completed capture frame, not same-frame tracking.
- Color means/classifier/tolerance preserved, all original five algorithms/Sensor/ISP/DDR/MIPI/PLL/SDC frozen. HDMI external data/sync/latency unchanged; only Logo address retimed with cycle-equivalence proof. Four switch pins verified; K4 reuses existing C7, neither 1.5V K1/K2 is used.
- Manual 100mm ruler calibration in X/Y; no guessed scale. 0.1mm displayed resolution is NOT established accuracy. Thin single workpiece, plain contrast background, axis alignment; GAPX/Y are cross-sections, no circle fitting or multi-hole recognition.
- No additional frame RAM. Constant scale multiplication may map to DSP; actual counts above govern.
- Historical FIFO B/S and Gray-pointer constraint coverage risks remain. New UI only synchronizes human inputs, no new video CDC or frame gating.
- Rollback: artifacts/bitstreams/COLOR_COMPARE_V1/camera_to_dsi_display.bit SHA256 {previous['bit_sha256']}; historical artifacts/tags unchanged.
- Full simulation boundaries: explicit post-AWB RGB and synchronized control/calibration values. Actual control debounce/ruler UI tested independently. No physical Sensor/DDR/HDMI simulation or board claim.
'''
    (dest/'BUILD_INFO.md').write_text(info,encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
