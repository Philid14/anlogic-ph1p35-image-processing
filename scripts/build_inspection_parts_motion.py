"""Exact committed inputs, unchanged constraints, bounded full candidate build."""
import json,re,sys
from pathlib import Path
import build_track_region_fix as build
ROOT=build.ROOT;P=build.P;HDL=build.HDL
BASE='6ad4f7cd70b5614240c07db2a16775aa492d9f14'
OUT=ROOT/'tmp/inspection_parts_motion/full_r0'
CHANGED={HDL+n for n in ('vision/vision_motion_grid.v','vision/vision_source_observer.v','isp/edge_control_stream.v','isp/planar_measure_stats.v','isp/color_compare_osd.v','isp/engineering_dimension_marks.v')}
def snapshot():
 head=build.git('rev-parse','HEAD').decode().strip()
 old=json.loads((ROOT/'artifacts/bitstreams/LATENCY_PERFORMANCE_V1/build_evidence/SOURCE_MANIFEST.json').read_text())
 entries=re.findall(r'<File Path="([^"]+)"',(P/'camera_to_dsi_display.al').read_text())
 files={}
 for entry in entries+[f'../user_source/hdl_source/vision/{n}' for n in ('vision_logo_index.dath','vision_logo_palette.dath','inspection_font.dath','latency_font.dath')]:
  path=(P/entry).resolve();rel=path.relative_to(ROOT).as_posix();data=path.read_bytes().replace(b'\r\n',b'\n')
  assert data==build.git('show',head+':'+rel).replace(b'\r\n',b'\n'),rel+' uncommitted'
  if rel not in CHANGED:assert data==build.git('show',BASE+':'+rel).replace(b'\r\n',b'\n'),rel+' out of scope'
  files[rel]=build.sha(path)
 assert len(entries)==91 and set(files)==set(old['files'])
 assert build.sha(P/'camera_to_dsi_display.al')==old['al_sha256']
 for run,name in [('syn_1','syn_settings.cfg'),('phy_1','phy_settings.cfg')]:
  assert (P/'camera_to_dsi_display_Runs'/run/'settings.cfg').read_bytes()==(ROOT/'artifacts/bitstreams/LATENCY_PERFORMANCE_V1/build_evidence'/name).read_bytes()
 changed=build.git('diff','--name-only',BASE,'--',HDL,HDL.replace('hdl_source/','ip_source/'),'features').decode().splitlines()
 assert set(changed)<=CHANGED,changed
 return dict(source_commit=head,baseline=BASE,files=files,al_sha256=old['al_sha256'],old_bits={p.relative_to(ROOT).as_posix():build.sha(p) for p in (ROOT/'artifacts/bitstreams').glob('*/*.bit')})
def regression_gate():
 folders=[ROOT/'tmp/inspection_parts_motion'/x for x in ('motion','profile','drawing','stream')]
 folders +=[ROOT/'tmp/inspection_parts_motion/regression'/x for x in ('font','shape','drawing','track','config','reset','select','contract','legacy','integrated','background_full','track_stream')]
 folders +=[ROOT/'tmp/latency_performance'/x for x in ('memory','rows','units','fifo','osd','video_path')]
 hashes={}
 for folder in folders:
  result=folder/'results.json';data=json.loads(result.read_text());assert data['passed'],str(folder)
  for rel,digest in data.get('sources',{}).items():assert build.sha(ROOT/rel)==digest,rel
  hashes[result.relative_to(ROOT).as_posix()]=build.sha(result)
  for manifest in folder.rglob('SIM_SOURCE_MANIFEST.json'):
   for rel,digest in json.loads(manifest.read_text()).items():
    path=Path(rel);assert build.sha(path)==digest,rel
    if '/retime_staging/' in path.as_posix():assert build.sha(ROOT/HDL/path.relative_to(ROOT/'tmp/latency_performance/retime_staging'))==digest
   hashes[manifest.relative_to(ROOT).as_posix()]=build.sha(manifest)
 return hashes
def bit():
 before=snapshot();frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text())
 for k in ('files','al_sha256','old_bits'):assert before[k]==frozen[k]
 tests=regression_gate();(OUT/'REGRESSION_GATE.json').write_text(json.dumps(tests,indent=2)+'\n')
 cdc=json.loads((OUT/'cdc/results.json').read_text());assert cdc['passed']
 phy=P/'camera_to_dsi_display_Runs/phy_1';database=phy/'camera_to_dsi_display_pr.db'
 assert cdc['route_db_sha256']==build.sha(database)==(OUT/'ROUTE_DB_SHA256.txt').read_text().strip()
 sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',(OUT/'phy_camera_to_dsi_display_phy.ts').read_text()))
 assert sw>=0 and hw>=0 and st==ht==0
 bitfile=OUT/'camera_to_dsi_display.bit';assert not bitfile.exists()
 text='source ./settings.cfg\nimport_device ph1_35p.db -package PH1P35MDG324 -speed 3\nopen_project camera_to_dsi_display.prj -noanalyze\nimport_db {'+database.as_posix()+'}\ncommit_param -step bitgen\nbitgen -bit {'+bitfile.as_posix()+'}\nexport_bitgen_param -file {'+(OUT/'bitgen_params.txt').as_posix()+'}\nputs "BIT_COMPLETE"\nexit\n'
 build.run('bit',text,phy)
 assert bitfile.stat().st_size>1_000_000 and build.sha(bitfile) not in before['old_bits'].values()
 assert regression_gate()==tests
 after=snapshot()
 for k in ('files','al_sha256','old_bits'):assert after[k]==before[k]
 print('PASS bit; board NOT_RUN')
if __name__=='__main__':
 build.OUT=OUT;build.snapshot=snapshot
 if sys.argv[-1]=='bit':bit()
 else:build.main()
