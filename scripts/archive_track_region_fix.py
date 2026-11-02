"""Archive timing-clean TRACK repair with immutable input and regression proofs."""
import json,re,shutil,datetime,subprocess
from pathlib import Path
from build_track_region_fix import ROOT,OUT,snapshot,sha,BASE
VERSION='TRACK_REGION_FIX_V1'
CASES=('font','shape','background_full','drawing','track','track_stream','config','reset','select','contract','legacy','integrated','region','region_full','red_equivalence')
def copy_reports(src,dst):
 dst.mkdir(parents=True,exist_ok=True)
 for p in src.iterdir():
  if p.is_file() and p.suffix in ('.txt','.json','.tcl','.cfg','.area','.ts','.rpt','.qor','.timing','.prj','.png') and p.name not in ('stim.txt','pack.txt','gold.txt','stats.txt','formatter.txt'):
   shutil.copy2(p,dst/p.name)
def main():
 frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text());now=snapshot()
 for key in ('files','al_sha256','old_bits'):assert now[key]==frozen[key],key
 for case in CASES:
  folder=ROOT/'tmp/track_region_fix'/case;result=json.loads((folder/'results.json').read_text());assert result['passed']
  for rel,digest in result['sources'].items():assert sha(ROOT/rel)==digest,rel
  native=folder/'SIM_SOURCE_MANIFEST.json'
  if native.exists():
   for rel,digest in json.loads(native.read_text()).items():assert sha(Path(rel))==digest,rel
 for case in ('legacy','integrated'):
  r=json.loads((ROOT/'tmp/track_region_fix'/case/'results.json').read_text());assert (r['frames'],r['beats'],r['words'])==(9,2073600,1555200)
 for case in ('region','region_full','red_equivalence'):
  assert json.loads((ROOT/'tmp/track_region_fix'/case/'results.json').read_text())['legacy_reproduced']
 logs='\n'.join((OUT/(s+'_stdout.txt')).read_text(errors='replace') for s in ('syn','phy','bit'))
 for stage in ('SYN','PHY','BIT'):assert stage+'_COMPLETE' in logs
 assert not re.search(r'\bERROR\s*:',logs)
 sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',(OUT/'phy_camera_to_dsi_display_phy.ts').read_text()))
 assert sw>=0 and hw>=0 and st==ht==0
 area=(OUT/'phy_camera_to_dsi_display_phy.area').read_text()
 resources={k:int(re.search(r'^#'+n+r'\s+(\d+)',area,re.M)[1]) for k,n in [('slice','slice'),('lut6','lut6'),('ff','reg'),('eram','eram'),('dsp','dsp')]}
 assert resources['slice']<=21216 and resources['eram']<=108 and resources['dsp']<=40
 previous=json.loads((ROOT/'artifacts/bitstreams/INSPECTION_SHAPE_TRACK_V1/BUILD_INFO.json').read_text())
 bit=OUT/'camera_to_dsi_display.bit';assert bit.stat().st_size>1_000_000 and sha(bit) not in frozen['old_bits'].values()
 critical=sorted(set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',logs)))
 info=dict(version=VERSION,role='MAIN',branch='codex/main/track-region-fix-v1',baseline_commit=BASE,
  source_commit=frozen['source_commit'],archive_driver_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
  tag='track-region-fix-v1-candidate',build_time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
  device='PH1P35MDG324 speed3',top='design_top_wrapper',original_bit_path=bit.as_posix(),bit_sha256=sha(bit),
  resources=resources,resource_delta_vs_INSPECTION_SHAPE_TRACK={k:resources[k]-v for k,v in previous['resources'].items()},
  setup_wns_ns=sw,hold_wns_ns=hw,setup_tns_ns=st,hold_tns_ns=ht,board_test='NOT_RUN',
  critical_warning_types=critical,new_critical_warning_types=sorted(set(critical)-set(previous['critical_warning_types'])),
  high_density_warning='PHY-7022' in logs,common_pixel_cycles=31,extra_common_pixel_cycles=0,
  extra_eram=resources['eram']-previous['resources']['eram'],extra_dsp=resources['dsp']-previous['resources']['dsp'],
  sta_coverage_percent=float(re.search(r'STA coverage\s*:\s*([\d.]+)%',(OUT/'phy_final_timing.rpt').read_text())[1]),
  implemented=['Exhaustively equivalent MAIN-specialized red30 predicate and R-relative dominance','3-of4 block/8px row run/4-row coherent chain; largest support area','Single registered atomic LAST result; no new image RAM or pixel latency'],
  validation='15 native groups; independent model16 frames+7 full720p frames with old RTL failure;18 full720p ISP/packer regression; exact MAIN31cycle TRACK; inherited dimension/BG/format/reset/font tests rerun',
  limitations=['Not general CCL: one longest run per row; solid single red object on non-red background','Pale pink, thin/hollow targets or glare holes can under-detect; similarly sized red objects can swap','N is selected chain support area in4px groups, not raw red count or calibrated object area','LAST bbox may lag one capture frame; no new DDR/display identity association','Inherited FIFO/Gray coverage, high-density, thermal and long-run risks require board tests'],
  route_db_sha256=(OUT/'ROUTE_DB_SHA256.txt').read_text().strip(),rollback_tag='inspection-shape-track-v1-candidate',rollback_bit_sha256=previous['bit_sha256'])
 dest=ROOT/'artifacts/bitstreams'/VERSION;assert not dest.exists(),'Never overwrite archive'
 ev=dest/'build_evidence';ev.mkdir(parents=True);shutil.copy2(bit,dest/bit.name);copy_reports(OUT,ev)
 for case in CASES:
  folder=ROOT/'tmp/track_region_fix'/case;copy_reports(folder,ev/'regression'/case)
  # Preserve nested native/tight/contract sources and logs too.
  for p in folder.rglob('SIM_SOURCE_MANIFEST.json'):
   nested=ev/'regression'/case/p.parent.relative_to(folder);copy_reports(p.parent,nested)
 for p in (ROOT/'tmp/track_region_fix').glob('full_r*'):
  if p!=OUT:copy_reports(p,ev/'attempts'/p.name)
 for failed in (ROOT/'tmp/track_region_fix').glob('r[0-9]*_regression'):
  for p in failed.iterdir():
   if p.is_dir():copy_reports(p,ev/'attempts'/failed.name/p.name)
 (dest/'BUILD_INFO.json').write_text(json.dumps(info,indent=2)+'\n')
 (dest/'BUILD_INFO.md').write_text(f'''# {VERSION} BUILD_INFO

- Branch: {info['branch']}; baseline {BASE}; dependent on unmerged Draft PR28.
- Actual build source commit: {info['source_commit']}
- Archive driver commit: {info['archive_driver_commit']}; tag: {info['tag']}
- Time: {info['build_time']}; device/top: {info['device']} / {info['top']}
- Original bit: {info['original_bit_path']}
- SHA256: {info['bit_sha256']}
- Final routed resources: {resources}
- Delta vs INSPECTION_SHAPE_TRACK_V1: {info['resource_delta_vs_INSPECTION_SHAPE_TRACK']}
- Setup WNS/TNS: {sw:+.3f}ns/{st}; Hold WNS/TNS: {hw:+.3f}ns/{ht}; coverage {info['sta_coverage_percent']}%.
- Complete SYN / PHY / final STA / bitgen PASS; constraints, clocks, Sensor and teammate RTL unchanged.
- Common pixel path31 clocks, extra0; no added image RAM/DSP; result one clock after EOF.
- Critical warnings: {critical}; new types: {info['new_critical_warning_types']}.
- Validation: {info['validation']}. Scope: post-AWB/synchronized UI, not physical MIPI/DDR/HDMI validation.
- Board Test NOT_RUN; no statement of real-camera improvement before user tests.
- Limits: {info['limitations']}
- Rollback: {info['rollback_tag']}; SHA256 {info['rollback_bit_sha256']}.
- Packing failures r0=21312/r1=21226 >21216 preserved; no failed-build bit released.

See DESIGN / REPORT / BOARD_TEST. Remote publication is separately confirmed after actual push.
''')
 print(json.dumps(info,indent=2))
if __name__=='__main__':main()
