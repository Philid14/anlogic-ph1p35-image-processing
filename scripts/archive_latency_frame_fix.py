"""Minimal immutable archive for expedited latency board test; no old bit reuse."""
import datetime,json,re,shutil
from build_latency_frame_fix import ROOT,OUT,BASE,snapshot,build
from archive_latency_performance import copy_reports
VERSION='LATENCY_FRAME_FIX_V1'
def main():
 frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text());now=snapshot()
 for k in ('files','al_sha256','old_bits'):assert now[k]==frozen[k]
 for s in ('syn','phy','bit'):
  log=(OUT/(s+'_stdout.txt')).read_text();assert s.upper()+'_COMPLETE' in log and not re.search(r'\bERROR\s*:',log)
 sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',(OUT/'phy_camera_to_dsi_display_phy.ts').read_text()))
 assert sw>=0 and hw>=0 and st==ht==0
 area=(OUT/'phy_camera_to_dsi_display_phy.area').read_text()
 resources={k:int(re.search(r'^#'+n+r'\s+(\d+)',area,re.M)[1]) for k,n in [('slice','slice'),('lut6','lut6'),('ff','reg'),('eram','eram'),('dsp','dsp')]}
 bit=OUT/'camera_to_dsi_display.bit';digest=build.sha(bit);assert digest not in frozen['old_bits'].values()
 dest=ROOT/'artifacts/bitstreams'/VERSION;assert not dest.exists()
 ev=dest/'build_evidence';ev.mkdir(parents=True);shutil.copy2(bit,dest/bit.name);copy_reports(OUT,ev)
 (dest/'.gitattributes').write_text('build_evidence/** -text\n')
 for n in ('blanking','old_failure','units','osd','osd_diagnostic','video_path'):
  folder=ROOT/'tmp/latency_frame_fix'/n
  copy_reports(folder,ev/'verification'/n)
  for sub in folder.iterdir():
   if sub.is_dir() and (sub/'SIM_SOURCE_MANIFEST.json').exists():copy_reports(sub,ev/'verification'/n/sub.name)
 if (ROOT/'tmp/latency_frame_fix/old_failure/latency_capture_tag_baseline.v').exists():shutil.copy2(ROOT/'tmp/latency_frame_fix/old_failure/latency_capture_tag_baseline.v',ev/'verification/old_failure/latency_capture_tag_baseline.v')
 prior=json.loads((ROOT/'artifacts/bitstreams/INSPECTION_PARTS_MOTION_V1/BUILD_INFO.json').read_text())
 logs='\n'.join((OUT/(s+'_stdout.txt')).read_text() for s in ('syn','phy','bit'))
 critical=sorted(set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',logs)))
 info=dict(version=VERSION,role='MAIN',branch='codex/main/latency-frame-fix-v1',baseline=BASE,source_commit=frozen['source_commit'],tag='latency-frame-fix-v1-candidate',build_time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),device='PH1P35MDG324 speed3',top='design_top_wrapper',original_bit_path=str(bit),bit_sha256=digest,resources=resources,resource_delta={k:v-prior['resources'][k] for k,v in resources.items()},setup_wns_ns=sw,hold_wns_ns=hw,setup_tns_ns=st,hold_tns_ns=ht,critical_warning_types=critical,new_critical_warning_types=sorted(set(critical)-set(prior['critical_warning_types'])),board_test='NOT_RUN',push_status='PENDING',draft_pr='DEFERRED per user expedited-bit request',regression='Native old-fails/new-passes blanking ownership; active source/line/full rejection; journal/display units; exact native5-line OSD raster; actual240-word DDR FIFO/mixer path12commits10samples',limits='Specific board root not yet proved; C/W/D needed if BAD persists. Full unrelated regression and physical long-run/PVT deferred. Unchanged production video clocks/SDC/payload and existing CDC risk; added diagnostic bit synchronizers not an atomic measurement bus.')
 (dest/'BUILD_INFO.json').write_text(json.dumps(info,indent=2)+'\n')
 (dest/'BUILD_INFO.md').write_text(f"""# {VERSION}

- Source commit: {info['source_commit']}; baseline: {BASE}; branch: {info['branch']}.
- Tag: {info['tag']}; Draft PR deferred by user's fastest-bit request. No merge.
- Build time: {info['build_time']}; {info['device']}; top {info['top']}.
- Original bit: {bit}; archived bit: {dest/bit.name}.
- SHA256: {digest}.
- SYN/PHY/STA/bitgen PASS; Setup {sw:+.3f}ns, Hold {hw:+.3f}ns; TNS0.
- Routed resources: {resources}; delta: {info['resource_delta']}.
- Critical warnings: {critical}; new types: {info['new_critical_warning_types']}.
- Validation: {info['regression']}.
- Limitations: {info['limits']}
- Board NOT_RUN. PROGRAM_SRAM; after5s inspect N/status/C/W/D. Do not call zero a valid latency.
- Rollback: inspection-parts-motion-v1-candidate. Historical bits unchanged.
- Push status pending, report actual result separately.
""")
 print(json.dumps(info,indent=2))
if __name__=='__main__':main()
