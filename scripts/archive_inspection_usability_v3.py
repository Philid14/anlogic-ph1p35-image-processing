"""Archive final checked source, timing-clean fresh bit and reproducible evidence."""
from pathlib import Path
import json,re,shutil,datetime,subprocess
from build_inspection_usability_v3 import ROOT,OUT,snapshot,sha
VERSION='INSPECTION_USABILITY_V3'
def main():
    frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text());now=snapshot()
    for k in ('files','al_sha256','old_bits'):assert now[k]==frozen[k],k
    for result in ('full_results.json','unit/ruler_results.json','controls/results.json','SOURCE_SCOPE.json'):
        a=json.loads((ROOT/'tmp/inspection_v3'/result).read_text());assert a['passed'],result
        for name,digest in a.get('sources',{}).items():assert sha(ROOT/name)==digest,name
    full=json.loads((ROOT/'tmp/inspection_v3/full_results.json').read_text())
    assert full['beats']==2073600 and full['words']==1555200
    for stage in ('syn','phy','bit'):
        log=(OUT/(stage+'_stdout.txt')).read_text(errors='replace')
        assert stage.upper()+'_COMPLETE' in log and not re.search(r'\bERROR\s*:',log),stage
    ts=(OUT/'phy_camera_to_dsi_display_phy.ts').read_text()
    sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',ts))
    assert sw>=0 and hw>=0 and st==ht==0
    area=(OUT/'phy_camera_to_dsi_display_phy.area').read_text()
    resources={k:int(re.search(r'^#'+n+r'\s+(\d+)',area,re.M)[1]) for k,n in [('slice','slice'),('lut6','lut6'),('ff','reg'),('eram','eram'),('dsp','dsp')]}
    assert resources['slice']<=21216 and resources['eram']<=108 and resources['dsp']<=40
    bit=OUT/'camera_to_dsi_display.bit';assert bit.stat().st_size>1_000_000 and sha(bit) not in frozen['old_bits'].values()
    previous=json.loads((ROOT/'artifacts/bitstreams/INSPECTION_AUTO_DIMENSION_V2/BUILD_INFO.json').read_text())
    logs='\n'.join((OUT/(s+'_stdout.txt')).read_text(errors='replace') for s in ('syn','phy','bit'))
    critical=sorted(set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',logs)))
    info=dict(version=VERSION,branch='codex/main/inspection-usability-v3',source_commit=frozen['source_commit'],
      archive_driver_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      tag='inspection-usability-v3-candidate',build_time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
      device='PH1P35MDG324 speed3',top='design_top_wrapper',original_bit_path=bit.as_posix(),bit_sha256=sha(bit),
      resources=resources,resource_delta_vs_V2={k:resources[k]-v for k,v in previous['resources'].items()},
      setup_wns_ns=sw,setup_tns_ns=st,hold_wns_ns=hw,hold_tns_ns=ht,critical_warning_types=critical,
      new_critical_warning_types=sorted(set(critical)-set(previous['critical_warning_types'])),board_test='NOT_RUN',
      high_density_warning='PHY-7022' in logs,
      extra_common_pixel_cycles=0,measurement_age='previous complete capture frame, plus inherited DDR display latency',
      calibration='K4 next complete frame; twelve row search, per-line contrast and dominant interval confidence; two readable lines agree; common X/Y scalar, no perspective correction',
      annotation='outer axis-aligned W/H plus measured center-line gaps; no height/CAD reconstruction',
      route_db_sha256=(OUT/'ROUTE_DB_SHA256.txt').read_text().strip())
    dest=ROOT/'artifacts/bitstreams'/VERSION;assert not dest.exists(),'Never overwrite candidate archive'
    ev=dest/'build_evidence';ev.mkdir(parents=True);shutil.copy2(bit,dest/bit.name)
    def copy_reports(src,dst):
        dst.mkdir(parents=True,exist_ok=True)
        for f in src.iterdir():
            if f.is_file() and f.suffix in ('.txt','.json','.tcl','.cfg','.area','.ts','.rpt','.qor','.timing','.prj') and f.name not in ('vectors.txt','stim.txt','pack.txt','ruler_vectors.txt','stats.txt','formatter.txt'):
                shutil.copy2(f,dst/f.name)
    copy_reports(OUT,ev)
    copy_reports(ROOT/'tmp/inspection_v3/r0',ev/'r0_six_rows_withdrawn')
    (ev/'r0_six_rows_withdrawn/README.md').write_text('267a478 completed SYN and nine-frame regression only; no PHY/bitgen. Vertical coverage model showed 6px scan spacing misses short tick bands. Final r1 uses twelve rows at 3px spacing and fresh synthesis/regression.\n')
    for name in ('unit','controls','full'):copy_reports(ROOT/'tmp/inspection_v3'/name,ev/name)
    for name in ('full_results.json','SOURCE_SCOPE.json','MODEL_COMPARISON.json','VERTICAL_COVERAGE.json'):shutil.copy2(ROOT/'tmp/inspection_v3'/name,ev/name)
    for name,src in [('legacy_ui',ROOT/'tmp/metrology_v1/ui'),('legacy_geometry',ROOT/'tmp/metrology_v1/unit'),
                     ('legacy_ruler',ROOT/'tmp/auto_dimension_v2/unit'),('legacy_drawing',ROOT/'tmp/auto_dimension_v2/drawing')]:copy_reports(src,ev/name)
    for name in ('formatter_console.txt','formatter_results.json'):shutil.copy2(ROOT/'tmp/color_compare_v1'/name,ev/('color_'+name))
    (ev/'VECTOR_DIGESTS.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha(p) for sub in ('unit','controls','full') for p in (ROOT/'tmp/inspection_v3'/sub).glob('*.txt')},indent=2)+'\n')
    (dest/'BUILD_INFO.json').write_text(json.dumps(info,indent=2)+'\n')
    text=f'''# {VERSION} BUILD_INFO

- Version / Role: {VERSION} / MAIN
- Branch: {info['branch']}
- Actual TD source commit: {info['source_commit']}
- Tag: {info['tag']} (created after archive)
- Build time: {info['build_time']}
- Device / Top: {info['device']} / {info['top']}
- Original bit: {info['original_bit_path']}
- Bit SHA256: {info['bit_sha256']}
- Resource: {resources}
- Delta vs V2: {info['resource_delta_vs_V2']}
- Setup WNS/TNS: {sw:+.3f}ns / {st}; Hold WNS/TNS: {hw:+.3f}ns / {ht}
- Synthesis -> Physical Design -> final Timing Check -> bitgen: PASS
- Critical warning types: {critical}; new: {info['new_critical_warning_types']}
- High density warning PHY-7022: {info['high_density_warning']}; routed pass does not establish thermal/board stability.
- Board Test Status: NOT_RUN. Independent ruler scale and measurement accuracy remain unverified.
- Common pixel delay unchanged (31 cycles). No frame cache; twelve 512px grayscale scan lines only.
- K4 short obtains a validated next-frame ruler measurement in ORIGIN/CAL; switch exit does not confirm.
- Shared X/Y scale requires perpendicular view and equal magnification; no perspective/distortion correction or metrology precision claim.
- Annotation uses actual measured bbox and gap endpoints, transparent glyphs; no automatic CAD/height/multi-hole reconstruction.
- Original five algorithms, color classifier/MAX12, Sensor/ISP parameters, video, Logo/CNT, key semantics, pins/PLL/SDC frozen. Color sampling/drawing is 32x32 at unchanged centers. SW diagnostics expose logical inputs, not a guessed physical map.
- Physical switch mapping remains pending board SW-bit observations; FIFO B/S and Gray-pointer coverage risks inherited. R6 is an explicit video-integrity rejection.
- Rollback: historical INSPECTION_AUTO_DIMENSION_V2 bit/tag; SHA256 {previous['bit_sha256']}.
- r0 six-row SYN-only implementation withdrawn; no failed/withdrawn bit generated, no historical tag moved. No PR merged.
'''
    (dest/'BUILD_INFO.md').write_text(text,encoding='utf-8');print(json.dumps(info,indent=2))
if __name__=='__main__':main()
