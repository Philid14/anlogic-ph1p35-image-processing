"""Immutable bit/source/report archive after real final STA and release gates."""
import json,re,shutil,datetime,subprocess,gzip
from pathlib import Path
from build_latency_performance import ROOT,OUT,BASE,snapshot,regression_gate,build
VERSION='LATENCY_PERFORMANCE_V1'

def copy_reports(source,dest):
    dest.mkdir(parents=True,exist_ok=True)
    skip={'stim.txt','pack.txt','gold.txt','pixels.txt','stats.txt','formatter.txt','unit.txt','gaussian.txt'}
    for p in source.iterdir():
        if p.is_file() and p.suffix in ('.txt','.json','.tcl','.cfg','.area','.ts','.rpt','.qor','.timing','.prj','.png') and p.name not in skip:
            if p.stat().st_size>5_000_000:
                with p.open('rb') as src,gzip.open(dest/(p.name+'.gz'),'wb') as dst:shutil.copyfileobj(src,dst)
            else:shutil.copy2(p,dest/p.name)

def main():
    frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text());now=snapshot()
    for key in ('files','al_sha256','old_bits'):assert now[key]==frozen[key]
    tests=regression_gate()
    assert tests==json.loads((OUT/'REGRESSION_GATE.json').read_text())
    for stage in ('syn','phy','bit'):
        text=(OUT/(stage+'_stdout.txt')).read_text(errors='replace')
        assert stage.upper()+'_COMPLETE' in text and not re.search(r'\bERROR\s*:',text)
    timing=(OUT/'phy_camera_to_dsi_display_phy.ts').read_text()
    sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',timing))
    assert sw>=0 and hw>=0 and st==ht==0
    area=(OUT/'phy_camera_to_dsi_display_phy.area').read_text()
    resources={k:int(re.search(r'^#'+n+r'\s+(\d+)',area,re.M)[1]) for k,n in [('slice','slice'),('lut6','lut6'),('ff','reg'),('eram','eram'),('dsp','dsp')]}
    assert resources['slice']<=21216 and resources['eram']<=108 and resources['dsp']<=40
    prior=json.loads((ROOT/'artifacts/bitstreams/TRACK_REGION_FIX_V1/BUILD_INFO.json').read_text())
    bit=OUT/'camera_to_dsi_display.bit'
    assert bit.stat().st_size>1_000_000 and build.sha(bit) not in frozen['old_bits'].values()
    logs='\n'.join((OUT/(s+'_stdout.txt')).read_text(errors='replace') for s in ('syn','phy','bit'))
    critical=sorted(set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',logs)))
    cdc=OUT/'cdc/results.json';assert cdc.exists(),'Explicit new CDC audit required'
    cdc_result=json.loads(cdc.read_text());assert cdc_result['passed']
    assert cdc_result['route_db_sha256']==(OUT/'ROUTE_DB_SHA256.txt').read_text().strip()
    info=dict(version=VERSION,role='MAIN',branch='codex/main/latency-performance-v1',baseline_commit=BASE,
        source_commit=frozen['source_commit'],archive_driver_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        tag='latency-performance-v1-candidate',draft_pr='https://github.com/Philid14/anlogic-ph1p35-image-processing/pull/30',
        build_time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),device='PH1P35MDG324 speed3',
        top='design_top_wrapper',original_bit_path=bit.as_posix(),bit_sha256=build.sha(bit),resources=resources,
        resource_delta_vs_TRACK_REGION_FIX={k:resources[k]-v for k,v in prior['resources'].items()},
        setup_wns_ns=sw,hold_wns_ns=hw,setup_tns_ns=st,hold_tns_ns=ht,board_test='NOT_RUN',
        critical_warning_types=critical,new_critical_warning_types=sorted(set(critical)-set(prior['critical_warning_types'])),
        sta_coverage_percent=float(re.search(r'STA coverage\s*:\s*([\d.]+)%',(OUT/'phy_final_timing.rpt').read_text())[1]),
        common_pixel_cycles=31,extra_common_pixel_cycles=0,configured_reference_hz=75000000,timestamp_resolution_us=10,
        measurement_boundary='decoded RAW first valid -> same image HDMI transmitter input first DE; excludes exposure and monitor',
        validation='18 full720p reference ISP/packer frames, 4147200beats/3110400words; native Gaussian/NMS/link/cache/FIFO/journal/meter/OSD; native 1280x4 actual DDR-command FIFO/readout/mixer path; original applications/reset/font regression',
        cdc_audit=cdc_result,
        limitations=['Configured clock, not calibrated absolute timing','BAD retains previous qualified values; startup invalid count is separated from steady increases',
          'All inherited long-run FIFO/Gray constraint and hardware PVT risks remain subject to board testing',
          'F is RAW latency identity; existing TRACK LAST counter is a different observation point',
          'No exposure, DDR scheduling, algorithm change or claim of lower end-to-end latency'],
        route_db_sha256=(OUT/'ROUTE_DB_SHA256.txt').read_text().strip(),rollback_tag='track-region-fix-v1-candidate',rollback_bit_sha256=prior['bit_sha256'])
    dest=ROOT/'artifacts/bitstreams'/VERSION;assert not dest.exists(),'Never overwrite an archive'
    ev=dest/'build_evidence';ev.mkdir(parents=True);shutil.copy2(bit,dest/bit.name);copy_reports(OUT,ev)
    copy_reports(OUT/'cdc',ev/'cdc')
    for result in tests:
        src=(ROOT/result).parent;relative=src.relative_to(ROOT/'tmp/latency_performance')
        copy_reports(src,ev/'verification'/relative)
    # Preserve preliminary resource/routing evidence without stale databases/bits.
    for name in ('memory_syn_r0','integrated_syn_r2','integrated_syn_r3','integrated_syn_r4','integrated_syn_r5','retime_syn','full_r0'):
        attempt=ROOT/'tmp/latency_performance'/name
        if attempt.exists() and attempt!=OUT:copy_reports(attempt,ev/'attempts'/name)
    (dest/'BUILD_INFO.json').write_text(json.dumps(info,indent=2)+'\n')
    (dest/'BUILD_INFO.md').write_text(f'''# {VERSION} BUILD_INFO

- Version/branch: {VERSION} / {info['branch']}
- Actual compiled source: {info['source_commit']}; baseline: {BASE}
- Archive driver: {info['archive_driver_commit']}; tag: {info['tag']}; Draft PR30, depends on29. No merge.
- Build time: {info['build_time']}; device/top: {info['device']} / {info['top']}
- Original bit: {info['original_bit_path']}
- SHA256: {info['bit_sha256']}
- Final routed resources: {resources}
- Delta vs TRACK_REGION_FIX_V1: {info['resource_delta_vs_TRACK_REGION_FIX']}
- Setup WNS/TNS: {sw:+.3f}ns/{st}; Hold WNS/TNS: {hw:+.3f}ns/{ht}; coverage: {info['sta_coverage_percent']}%.
- SYN/PHY/final STA/bitgen PASS. Original PLL, pin and SDC files unchanged.
- Critical warning types: {critical}; new types: {info['new_critical_warning_types']}.
- Common post-AWB stream31cycles, extra0. No frame-buffer policy or pixel throughput changes.
- Tick10us from configured75MHz; end-to-end same-frame sample, repetitions counted as AGE only.
- Validation: {info['validation']}. These are software/RTL/TD results, not physical camera/DDR/HDMI verification.
- Board Test: NOT_RUN. Follow docs/LATENCY_PERFORMANCE_V1_BOARD_TEST.md.
- CDC: see build_evidence/cdc; inherited constraints/long-run risks are not silently declared fixed.
- Rollback: {info['rollback_tag']}, SHA256 {info['rollback_bit_sha256']}.
- Remote publication receipt is recorded separately after actual push.
''')
    print(json.dumps(info,indent=2))
if __name__=='__main__':main()
