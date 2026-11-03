"""Read-only candidate source/bit/tag/remote closure, optional publication receipt."""
import datetime,gzip,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'artifacts/bitstreams/INSPECTION_PARTS_MOTION_V1'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
 info=json.loads((DEST/'BUILD_INFO.json').read_text());source=json.loads((DEST/'build_evidence/SOURCE_MANIFEST.json').read_text())
 assert info['source_commit']==source['source_commit'] and info['board_test']=='NOT_RUN'
 bit=DEST/'camera_to_dsi_display.bit';assert sha(bit.read_bytes())==info['bit_sha256']
 for rel,digest in source['files'].items():
  data=(ROOT/rel).read_bytes();assert sha(data)==digest,rel
  assert data.replace(b'\r\n',b'\n')==git('show',info['source_commit']+':'+rel).replace(b'\r\n',b'\n'),rel
 al='in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.al'
 assert sha((ROOT/al).read_bytes())==source['al_sha256']
 for rel,digest in source['old_bits'].items():assert sha((ROOT/rel).read_bytes())==digest,rel
 gates=json.loads((DEST/'build_evidence/REGRESSION_GATE.json').read_text())
 for rel,digest in gates.items():
  p=DEST/'build_evidence/verification'/Path(rel).relative_to('tmp')
  data=p.read_bytes() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes())
  assert sha(data)==digest,rel
 cdc=json.loads((DEST/'build_evidence/cdc/results.json').read_text());assert cdc['passed'] and cdc['route_db_sha256']==info['route_db_sha256']
 assert info['setup_wns_ns']>=0 and info['hold_wns_ns']>=0 and info['setup_tns_ns']==info['hold_tns_ns']==0
 for stage in ('syn','phy','bit'):assert stage.upper()+'_COMPLETE' in (DEST/'build_evidence'/f'{stage}_stdout.txt').read_text()
 local=dict(bit_sha256=info['bit_sha256'],inputs_verified=len(source['files']),historical_bits_unchanged=len(source['old_bits']),verification_hashes=len(gates),cdc_passed=True)
 if '--local' in sys.argv:print(json.dumps(dict(local_passed=True,**local),indent=2));return
 tag=info['tag'];branch=info['branch'];head=git('rev-parse','HEAD').decode().strip()
 assert git('branch','--show-current').decode().strip()==branch
 assert set(git('diff','--name-only').decode().splitlines())<= {'docs/GITHUB_REFERENCE_RESEARCH.md'}
 assert not git('diff','--cached','--name-only').strip()
 for rel in list(source['files'])+[al]:
  assert (ROOT/rel).read_bytes().replace(b'\r\n',b'\n')==git('show',tag+':'+rel).replace(b'\r\n',b'\n'),rel
 assert sha(git('show',tag+':'+bit.relative_to(ROOT).as_posix()))==info['bit_sha256']
 for rel,digest in gates.items():
  p=DEST/'build_evidence/verification'/Path(rel).relative_to('tmp')
  if p.exists():data=git('show',tag+':'+p.relative_to(ROOT).as_posix())
  else:data=gzip.decompress(git('show',tag+':'+(Path(str(p)+'.gz')).relative_to(ROOT).as_posix()))
  assert sha(data)==digest,'Tag changed raw native verification evidence: '+rel
 remote=git('remote','get-url','origin').decode().strip();assert remote=='https://github.com/Philid14/anlogic-ph1p35-image-processing.git'
 refs=dict(line.split()[::-1] for line in git('ls-remote','origin','refs/heads/'+branch,'refs/tags/'+tag,'refs/tags/'+tag+'^{}').decode().splitlines())
 archive=git('rev-parse',tag+'^{}').decode().strip();tagobj=git('rev-parse',tag).decode().strip()
 assert refs['refs/heads/'+branch]==head and refs['refs/tags/'+tag]==tagobj and refs['refs/tags/'+tag+'^{}']==archive
 result=dict(version=info['version'],time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),remote=remote,branch=branch,remote_head=head,source_commit=info['source_commit'],archive_commit=archive,tag=tag,tag_object=tagobj,push_status='SUCCESS',board_test='NOT_RUN',draft_pr=info['draft_pr'],**local)
 if '--check' not in sys.argv:
  out=ROOT/'docs/evidence/INSPECTION_PARTS_MOTION_V1/REMOTE_RECEIPT.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
