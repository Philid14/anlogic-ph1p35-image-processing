"""Fast, isolated latency fix build. No changes to video payload or constraints."""
import json,re,sys,shutil
from pathlib import Path
import build_track_region_fix as build
ROOT=build.ROOT;P=build.P;HDL=build.HDL
BASE='793c9d3de58420524007474bafb2125cbad104f1'
OUT=ROOT/'tmp/latency_frame_fix/full_r0'
CHANGED={HDL+n for n in ('design_top_wrapper.v','hdmi_mixer.v','vision/latency_capture_tag.v','vision/latency_slot_journal.v','vision/latency_osd.v')}
def snapshot():
 head=build.git('rev-parse','HEAD').decode().strip()
 prior=json.loads((ROOT/'artifacts/bitstreams/INSPECTION_PARTS_MOTION_V1/build_evidence/SOURCE_MANIFEST.json').read_text())
 files={}
 for rel in prior['files']:
  p=ROOT/rel;data=p.read_bytes().replace(b'\r\n',b'\n')
  assert data==build.git('show',head+':'+rel).replace(b'\r\n',b'\n'),rel+' uncommitted'
  if rel not in CHANGED:assert data==build.git('show',BASE+':'+rel).replace(b'\r\n',b'\n'),rel+' out of scope'
  files[rel]=build.sha(p)
 assert build.sha(P/'camera_to_dsi_display.al')==prior['al_sha256']
 for run,name in [('syn_1','syn_settings.cfg'),('phy_1','phy_settings.cfg')]:
  assert (P/'camera_to_dsi_display_Runs'/run/'settings.cfg').read_bytes()==(ROOT/'artifacts/bitstreams/INSPECTION_PARTS_MOTION_V1/build_evidence'/name).read_bytes()
 return dict(source_commit=head,baseline=BASE,files=files,al_sha256=prior['al_sha256'],old_bits={p.relative_to(ROOT).as_posix():build.sha(p) for p in (ROOT/'artifacts/bitstreams').glob('*/*.bit')})
def bit():
 current=snapshot();frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text())
 for k in ('files','al_sha256','old_bits'):assert current[k]==frozen[k]
 hashes={}
 for name in ('blanking','units','osd','osd_diagnostic','video_path'):
  f=ROOT/'tmp/latency_frame_fix'/name/'results.json';assert json.loads(f.read_text())['passed'];hashes[f.relative_to(ROOT).as_posix()]=build.sha(f)
  for manifest in f.parent.rglob('SIM_SOURCE_MANIFEST.json'):
   for rel,digest in json.loads(manifest.read_text()).items():assert build.sha(Path(rel))==digest,rel
   hashes[manifest.relative_to(ROOT).as_posix()]=build.sha(manifest)
 (OUT/'REGRESSION_GATE.json').write_text(json.dumps(hashes,indent=2)+'\n')
 phy=P/'camera_to_dsi_display_Runs/phy_1';db=phy/'camera_to_dsi_display_pr.db'
 assert build.sha(db)==(OUT/'ROUTE_DB_SHA256.txt').read_text().strip()
 sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',(OUT/'phy_camera_to_dsi_display_phy.ts').read_text()))
 assert sw>=0 and hw>=0 and st==ht==0
 bitfile=OUT/'camera_to_dsi_display.bit';assert not bitfile.exists()
 text='source ./settings.cfg\nimport_device ph1_35p.db -package PH1P35MDG324 -speed 3\nopen_project camera_to_dsi_display.prj -noanalyze\nimport_db {'+db.as_posix()+'}\ncommit_param -step bitgen\nbitgen -bit {'+bitfile.as_posix()+'}\nputs "BIT_COMPLETE"\nexit\n'
 build.run('bit',text,phy)
 assert bitfile.stat().st_size>1000000 and build.sha(bitfile) not in current['old_bits'].values()
 print('PASS fresh bit',build.sha(bitfile))
if __name__=='__main__':
 build.OUT=OUT;build.snapshot=snapshot
 if sys.argv[-1]=='bit':bit()
 else:build.main()
