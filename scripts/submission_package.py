"""Portable final-source verifier and real RAR5 packager; no build/RTL mutation."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess,sys,tempfile,datetime
ROOT=Path(__file__).resolve().parents[1]
VERSION='FINAL_SUBMISSION_V1_1'
MAX_BYTES=200_000_000
CODE={'.v','.sv','.vh','.vhd','.py','.ps1','.tcl','.al','.adc','.sdc','.xml','.dath','.mem','.mif','.cfg','.scad','.bat','.sh','.h','.c','.cpp','.json','.toml','.yml','.yaml'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
def manifest():return json.loads((ROOT/'submission/MANIFEST.json').read_text(encoding='utf-8'))
def verify():
 m=manifest();bad=[]
 for rel,h in (m['formal_inputs']|m.get('auxiliary_ip_inputs',{})).items():
  if not (ROOT/rel).is_file() or sha(ROOT/rel)!=h:bad.append(rel)
 for rel,h in [(m['project_entry'],m['project_entry_sha256']),(m['bit_path'],m['bit_sha256'])]:
  if not (ROOT/rel).is_file() or sha(ROOT/rel)!=h:bad.append(rel)
 for rel in m['formal_inputs']:
  if rel.endswith(('.v','.sv')):
   text=(ROOT/rel).read_text(errors='replace')
   if re.search(r'demo_next_latency|demo_random|demo_minimum|DEMO ONLY',text):bad.append(rel+' randomized latency')
 assert not bad,bad
 print('PASS95 formal inputs + .al + real bit; no random-latency logic',flush=True)
 return m
def files():
 m=manifest()
 selected=set(m['formal_inputs'])|set(m.get('auxiliary_ip_inputs',{}))
 selected|={m['project_entry'],m['bit_path'],
  'artifacts/bitstreams/LATENCY_FRAME_FIX_V1/BUILD_INFO.md',
  'submission/MANIFEST.json','submission/PACKAGE_README.md','submission/ACCEPTANCE.md',
  'submission/build/syn_settings.cfg','submission/build/phy_settings.cfg',
  'scripts/submission_package.py','scripts/build_submission.py','scripts/prepare_td_runs.py'}
 for rel in selected:assert (ROOT/rel).is_file(),rel
 assert not any(re.search(r'latency[-_]demo',p,re.I) for p in selected)
 return sorted(selected)
def secrets(names):
 patterns=[re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}'),re.compile(rb'github_pat_[A-Za-z0-9_]{50,}'),re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),re.compile(rb'AKIA[A-Z0-9]{16}')]
 hits=[]
 for rel in names:
  p=ROOT/rel
  if p.stat().st_size<4_000_000 and p.suffix.lower() in CODE|{'.md','.txt'}:
   data=p.read_bytes()
   if any(x.search(data) for x in patterns):hits.append(rel)
 assert not hits,'Possible credential in '+str(hits)
 return dict(passed=True,files_scanned=len(names),patterns='GitHub PAT, private-key headers, AWS access keys; no values printed')
def rar():
 m=verify();names=files();scan=secrets(names)
 assert set(m['formal_inputs'])|{m['project_entry'],m['bit_path']}<=set(names)
 # Completeness is the active TD dependency closure, not every experiment.
 assert set(m['formal_inputs'])|set(m.get('auxiliary_ip_inputs',{}))<=set(names)
 exe=next((p for p in [Path('C:/Program Files/WinRAR/Rar.exe'),Path('C:/Program Files (x86)/WinRAR/Rar.exe')] if p.is_file()),None)
 if exe is None:
  found=shutil.which('rar');assert found,'Install licensed WinRAR/rar to create actual RAR5';exe=Path(found)
 out=ROOT/'dist';out.mkdir(exist_ok=True);dest=out/'PH1P35_FINAL_SUBMISSION_V1_1.rar'
 assert not dest.exists(),'Do not silently overwrite an existing delivery archive'
 source_commit=git('rev-parse','HEAD').decode().strip()
 with tempfile.TemporaryDirectory(prefix='ph1p35_submission_') as temp:
  staging=Path(temp);tree=staging/VERSION;tree.mkdir();hashes={}
  for rel in names:
   p=tree/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p);hashes[rel]=sha(p)
  package=dict(version=VERSION,repository=m['repository'],source_commit=source_commit,hardware_source_commit=m['hardware_source_commit'],bit_sha256=m['bit_sha256'],files=hashes,credential_scan=scan,board_test=m['board_test'])
  (tree/'DELIVERY_MANIFEST.json').write_text(json.dumps(package,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  subprocess.run([str(exe),'a','-ma5','-m5','-s','-idq','-r',str(dest),VERSION],cwd=staging,check=True)
  assert dest.stat().st_size<MAX_BYTES,'RAR exceeds200MB'
  with dest.open('rb') as f:assert f.read(8)==b'Rar!\x1a\x07\x01\x00','Not genuine RAR5'
  subprocess.run([str(exe),'t','-idq',str(dest)],check=True)
  extracted=staging/'verify';extracted.mkdir()
  subprocess.run([str(exe),'x','-idq',str(dest),str(extracted)+'\\'],check=True)
  root=extracted/VERSION
  for rel,h in hashes.items():assert (root/rel).is_file() and sha(root/rel)==h,rel
  assert json.loads((root/'DELIVERY_MANIFEST.json').read_text(encoding='utf-8'))==package
  # A judge can run the verifier offline with no .git or historical caches.
  subprocess.run([sys.executable,'-B','-X','utf8',str(root/'scripts/submission_package.py'),'verify'],cwd=root,check=True)
  subprocess.run([sys.executable,'-B','-X','utf8',str(root/'scripts/build_submission.py'),'--prepare-only'],cwd=root,check=True)
 result=dict(passed=True,version=VERSION,rar_path=str(dest),format='RAR5',size_bytes=dest.stat().st_size,limit_bytes=MAX_BYTES,sha256=sha(dest),source_commit=source_commit,file_count=len(names)+1,all_active_project_code_and_ip_included=True,extraction_all_hashes_passed=True,offline_verification_passed=True,credential_scan=scan,bit_sha256=m['bit_sha256'],board_test=m['board_test'])
 (out/'RAR_VERIFICATION_V1_1.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('command',choices=['verify','rar']);args=a.parse_args()
 if args.command=='verify':verify()
 else:rar()
