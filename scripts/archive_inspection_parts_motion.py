"""Archive only an actually routed/timed candidate, preserving rejected trials."""
import datetime,json,re,shutil
from pathlib import Path
from build_inspection_parts_motion import ROOT,OUT,BASE,CHANGED,snapshot,regression_gate,build
from archive_latency_performance import copy_reports
VERSION='INSPECTION_PARTS_MOTION_V1'
def main():
 frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text());current=snapshot()
 for key in ('files','al_sha256','old_bits'):assert current[key]==frozen[key]
 tests=regression_gate();assert tests==json.loads((OUT/'REGRESSION_GATE.json').read_text())
 for stage in ('syn','phy','bit'):
  text=(OUT/(stage+'_stdout.txt')).read_text();assert stage.upper()+'_COMPLETE' in text and not re.search(r'\bERROR\s*:',text)
 sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',(OUT/'phy_camera_to_dsi_display_phy.ts').read_text()))
 assert sw>=0 and hw>=0 and st==ht==0
 area=(OUT/'phy_camera_to_dsi_display_phy.area').read_text()
 resources={k:int(re.search(r'^#'+n+r'\s+(\d+)',area,re.M)[1]) for k,n in [('slice','slice'),('lut6','lut6'),('ff','reg'),('eram','eram'),('dsp','dsp')]}
 assert resources['slice']<=21216 and resources['eram']<=108 and resources['dsp']<=40
 prior=json.loads((ROOT/'artifacts/bitstreams/LATENCY_PERFORMANCE_V1/BUILD_INFO.json').read_text())
 cdc=json.loads((OUT/'cdc/results.json').read_text());assert cdc['passed'] and cdc['route_db_sha256']==(OUT/'ROUTE_DB_SHA256.txt').read_text().strip()
 bit=OUT/'camera_to_dsi_display.bit';assert bit.stat().st_size>1_000_000 and build.sha(bit) not in frozen['old_bits'].values()
 logs='\n'.join((OUT/(s+'_stdout.txt')).read_text() for s in ('syn','phy','bit'))
 critical=sorted(set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',logs)))
 info=dict(version=VERSION,role='MAIN',branch='codex/main/inspection-parts-motion-v1',baseline_commit=BASE,
  source_commit=frozen['source_commit'],archive_driver_commit=build.git('rev-parse','HEAD').decode().strip(),tag='inspection-parts-motion-v1-candidate',
  draft_pr='https://github.com/Philid14/anlogic-ph1p35-image-processing/pull/31',build_time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
  device='PH1P35MDG324 speed3',top='design_top_wrapper',original_bit_path=str(bit),bit_sha256=build.sha(bit),resources=resources,
  resource_delta_vs_LATENCY_PERFORMANCE={k:resources[k]-v for k,v in prior['resources'].items()},setup_wns_ns=sw,hold_wns_ns=hw,setup_tns_ns=st,hold_tns_ns=ht,
  sta_coverage_percent=float(re.search(r'STA coverage\s*:\s*([\d.]+)%',(OUT/'phy_final_timing.rpt').read_text())[1]),
  board_test='NOT_RUN',critical_warning_types=critical,new_critical_warning_types=sorted(set(critical)-set(prior['critical_warning_types'])),
  common_pixel_cycles=31,extra_common_pixel_cycles=0,motion='FF3000; 8px lattice, 3x3 dots; prior complete motion map; original32x16/TH12 detection',
  parts='Two stable nested row bands; single thin axis-aligned T/L; original ruler/background. Cycling W/H, S/V, W/T, A/T, B/T; 32 captured-frame supplementary dwell, zero-side fallback.',
  validation_hashes=len(tests),validation='15 profile cases,168 view cases,13 full720p overlay frames,8 actual31-cycle streams, original18 full720p reference frames and application/latency regression',
  route_db_sha256=cdc['route_db_sha256'],cdc_audit=cdc,
  limitations=['Board NOT_RUN; noise/reflectance/accuracy need user evaluation','T crossbar horizontal; no arbitrary rotation/contour/CAD fitting','4px horizontal section coordinates, not0.1mm physical accuracy',
   'Dense motion is prior completed map; more display dots do not improve detection resolution','No new globalCDC constraints or inherited FIFO/long-run/PVT fix','Seven dimensions available over views, not simultaneously; R0 simultaneous view rejected at21710Slice'],
  rollback_tag='latency-performance-v1-candidate',rollback_bit_sha256=prior['bit_sha256'])
 dest=ROOT/'artifacts/bitstreams'/VERSION;assert not dest.exists(),'Do not overwrite an archive'
 ev=dest/'build_evidence';ev.mkdir(parents=True);shutil.copy2(bit,dest/bit.name);copy_reports(OUT,ev);copy_reports(OUT/'cdc',ev/'cdc')
 for rel in tests:
  src=(ROOT/rel).parent;copy_reports(src,ev/'verification'/src.relative_to(ROOT/'tmp'))
 for name in ('resource_r0','resource_r1','resource_r2','resource_paged','resource_paged_opt','resource_paged_opt2','resource_compact','full_r0','full_r1'):
  src=ROOT/'tmp/inspection_parts_motion'/name
  if src.exists():
   target=ev/'attempts'/name;copy_reports(src,target)
   for rel in CHANGED:
    p=src/'inputs'/rel
    if p.exists():
     q=target/'changed_inputs'/Path(rel).relative_to(Path(build.HDL));q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 for src in (ROOT/'tmp/inspection_parts_motion/all_at_once_validation').rglob('*'):
  if src.is_dir():copy_reports(src,ev/'attempts/all_at_once_validation'/src.relative_to(ROOT/'tmp/inspection_parts_motion/all_at_once_validation'))
 (dest/'BUILD_INFO.json').write_text(json.dumps(info,indent=2)+'\n')
 (dest/'BUILD_INFO.md').write_text(f'''# {VERSION} BUILD_INFO

- Branch: {info['branch']}; baseline: {BASE}; role MAIN.
- Actual compiled source: {info['source_commit']}; archive driver: {info['archive_driver_commit']}.
- Tag: {info['tag']}; Draft PR31 depends on unmerged30. No merge.
- Build time: {info['build_time']}; device/top: {info['device']} / {info['top']}.
- Original bit: {info['original_bit_path']}; SHA256: {info['bit_sha256']}.
- Final resources: {resources}; delta vs LATENCY_PERFORMANCE: {info['resource_delta_vs_LATENCY_PERFORMANCE']}.
- Setup WNS/TNS {sw:+.3f}ns/{st}; Hold WNS/TNS {hw:+.3f}ns/{ht}; STA coverage {info['sta_coverage_percent']}%.
- Complete SYN/PHY/final STA/bitgen PASS. Clock/PLL/pin/SDC, Sensor/ISP and original application controls unchanged.
- Critical warnings: {critical}; new types: {info['new_critical_warning_types']}.
- Common pixel stream31cycles, extra0; original pixel/DDR throughput and video format unchanged.
- Verification: {info['validation']}; {len(tests)} result/native-source hashes. Software/RTL/TD, not physical camera/DDR/HDMI evidence.
- Board Test NOT_RUN; follow docs/INSPECTION_PARTS_MOTION_V1_BOARD_TEST.md.
- CDC: exact routed DB inspected; inherited Gray/long-run hardware risks remain.
- Rejected R0 at21710Slice and resource attempts preserved under build_evidence/attempts; no rejected trial bit.
- Rollback: {info['rollback_tag']}, SHA256 {info['rollback_bit_sha256']}.
- Remote publication is recorded separately after actual push.
''')
 print(json.dumps(info,indent=2))
if __name__=='__main__':main()
