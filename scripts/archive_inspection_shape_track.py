"""Archive only the final timing-clean database/bit and actual frozen inputs."""
from pathlib import Path
import json,re,shutil,datetime,subprocess
from build_inspection_shape_track import ROOT,OUT,snapshot,sha
VERSION='INSPECTION_SHAPE_TRACK_V1'
CASES=('font','shape','background_full','drawing','track','track_stream','config','reset','select','contract','legacy','integrated')
def copy_reports(src,dst):
 dst.mkdir(parents=True,exist_ok=True)
 for p in src.iterdir():
  if p.is_file() and p.suffix in ('.txt','.json','.tcl','.cfg','.area','.ts','.rpt','.qor','.timing','.prj','.png') and p.name not in ('stim.txt','pack.txt','gold.txt','stats.txt','formatter.txt'):
   shutil.copy2(p,dst/p.name)
def main():
 frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text());now=snapshot()
 for k in ('files','al_sha256','old_bits'):assert now[k]==frozen[k],k
 for case in CASES:
  folder=ROOT/'tmp/inspection_shape_track'/case;result=json.loads((folder/'results.json').read_text());assert result['passed']
  for rel,digest in result['sources'].items():assert sha(ROOT/rel)==digest,rel
  native=folder/'SIM_SOURCE_MANIFEST.json'
  if native.exists():
   for rel,digest in json.loads(native.read_text()).items():assert sha(Path(rel))==digest,rel
 for case in ('legacy','integrated'):
  result=json.loads((ROOT/'tmp/inspection_shape_track'/case/'results.json').read_text());assert (result['frames'],result['beats'],result['words'])==(9,2073600,1555200)
 logs='\n'.join((OUT/(s+'_stdout.txt')).read_text(errors='replace') for s in ('syn','phy','bit'))
 for stage in ('SYN','PHY','BIT'):assert stage+'_COMPLETE' in logs
 assert not re.search(r'\bERROR\s*:',logs)
 sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',(OUT/'phy_camera_to_dsi_display_phy.ts').read_text()))
 assert sw>=0 and hw>=0 and st==ht==0
 area=(OUT/'phy_camera_to_dsi_display_phy.area').read_text()
 resources={k:int(re.search(r'^#'+n+r'\s+(\d+)',area,re.M)[1]) for k,n in [('slice','slice'),('lut6','lut6'),('ff','reg'),('eram','eram'),('dsp','dsp')]}
 assert resources['slice']<=21216 and resources['eram']<=108 and resources['dsp']<=40
 previous=json.loads((ROOT/'artifacts/bitstreams/RULER_CM_CAL_V1/BUILD_INFO.json').read_text())
 bit=OUT/'camera_to_dsi_display.bit';assert bit.stat().st_size>1_000_000 and sha(bit) not in frozen['old_bits'].values()
 critical=sorted(set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',logs)))
 info=dict(version=VERSION,role='MAIN',branch='codex/main/inspection-shape-track-v1',source_commit=frozen['source_commit'],
  archive_driver_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
  tag='inspection-shape-track-v1-candidate',build_time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
  device='PH1P35MDG324 speed3',top='design_top_wrapper',original_bit_path=bit.as_posix(),bit_sha256=sha(bit),
  resources=resources,resource_delta_vs_RULER_CM={k:resources[k]-v for k,v in previous['resources'].items()},
  setup_wns_ns=sw,hold_wns_ns=hw,setup_tns_ns=st,hold_tns_ns=ht,board_test='NOT_RUN',
  critical_warning_types=critical,new_critical_warning_types=sorted(set(critical)-set(previous['critical_warning_types'])),
  high_density_warning='PHY-7022' in logs,common_pixel_cycles=31,extra_common_pixel_cycles=0,extra_measurement_statistic_cycles=2,
  implemented=['4-point cell reference on empty plane; per-pixel bipolar difference12','Explicit K4 long W/H or D/R mode; NOT automatic circle or arc fitting','Previous-complete-frame LAST red bbox, red interior preserved','Original shared logic fonts and exact per-clock config RAM delay'],
  diagnostic_only=['Automatic near-round classifier was rejected for area; SHAPE_ENABLE=0 in production','COMPACT_FONT=0: ERAM-font attempt stopped during long routing, not a released candidate'],
  limitations=['Smooth fixed background/light/camera; retrain empty plane after changes; no invisible/clipped-edge recovery',
   'Operator chooses round mode for a known planar circle; D is horizontal exterior span and R=D/2',
   'LAST bbox can lag moving targets; stale DDR repeats may retain old box with SOURCE STALE warning',
   'Only one total red bbox, not independent multi-target tracking',
   'FIFO/Gray coverage, high density, thermal/long-run and physical measurement accuracy remain unverified'],
  route_db_sha256=(OUT/'ROUTE_DB_SHA256.txt').read_text().strip(),rollback_bit_sha256=previous['bit_sha256'])
 dest=ROOT/'artifacts/bitstreams'/VERSION;assert not dest.exists(),'Never overwrite archive'
 ev=dest/'build_evidence';ev.mkdir(parents=True);shutil.copy2(bit,dest/bit.name);copy_reports(OUT,ev)
 for case in CASES:copy_reports(ROOT/'tmp/inspection_shape_track'/case,ev/'regression'/case)
 for attempt in (ROOT/'tmp/inspection_shape_track').glob('*_r[0-9]*'):
  if attempt.is_dir() and attempt!=OUT:copy_reports(attempt,ev/'attempts'/attempt.name)
 (dest/'BUILD_INFO.json').write_text(json.dumps(info,indent=2)+'\n')
 (dest/'BUILD_INFO.md').write_text(f'''# {VERSION} BUILD_INFO

- Role / Branch: MAIN / {info['branch']}
- Actual TD source commit: {info['source_commit']}
- Archive driver commit: {info['archive_driver_commit']}
- Candidate tag: {info['tag']}
- Build time: {info['build_time']}
- Device / Top: {info['device']} / {info['top']}
- Original bit: {info['original_bit_path']}
- Bit SHA256: {info['bit_sha256']}
- Routed resources: {resources}
- Delta vs RULER_CM_CAL_V1: {info['resource_delta_vs_RULER_CM']}
- Setup WNS/TNS: {sw:+.3f}ns / {st}; Hold WNS/TNS: {hw:+.3f}ns / {ht}
- SYN → PHY → final Timing Check → bitgen: PASS. No changed SDC, clocks, Sensor, DDR or teammate RTL.
- Critical warning types: {critical}; new types: {info['new_critical_warning_types']}.
- Common pixel path: 31 clocks, extra0; only measurement-statistics branch +2 clocks.
- Validation: native vendor ERAM/GSR; old/new9frame720p ISP/packer=18frames,4147200beats/3110400words; D/R two full720p frames; BG four720p frames/all1152cells; actual MAIN TRACK128x96;160-frame geometry/240 formatter cases; font4096; config/reset/selection tests.
- Scope: post-AWB/UI simulation boundaries, not physical MIPI/DDR-controller/HDMI validation. Full720p ruler288-row search inherited unchanged; integrated tests use12 search rows for runtime.
- D/R is EXPLICIT operator mode, not automatic circle/arc detection. Automatic near-round attempt not used.
- Board Test Status: NOT_RUN. FIFO/CDC and high-density physical risks remain.
- Rollback: RULER_CM_CAL_V1 / ruler-cm-cal-v1-candidate / {previous['bit_sha256']}.

See docs/INSPECTION_SHAPE_TRACK_V1_DESIGN.md and BOARD_TEST.md. Historical bits/tags are unchanged. Remote publication status is recorded after actual push; this file is not proof of push.
''')
 print(json.dumps(info,indent=2))
if __name__=='__main__':main()
