"""Read-only local/tag/remote closure check; writes a receipt only on success."""
import json,hashlib,subprocess,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 d=json.loads((ROOT/'artifacts/bitstreams/TRACK_REGION_FIX_V1/BUILD_INFO.json').read_text())
 tag=d['tag'];branch=d['branch'];head=git('rev-parse','HEAD').decode().strip()
 assert git('branch','--show-current').decode().strip()==branch
 dest=ROOT/'artifacts/bitstreams/TRACK_REGION_FIX_V1';bit=dest/'camera_to_dsi_display.bit'
 bit_rel=bit.relative_to(ROOT).as_posix();assert sha(bit.read_bytes())==d['bit_sha256']==sha(git('show',tag+':'+bit_rel))
 source=json.loads((dest/'build_evidence/SOURCE_MANIFEST.json').read_text())
 for rel,digest in source['files'].items():
  current=(ROOT/rel).read_bytes();assert sha(current)==digest,rel
  for rev in (d['source_commit'],tag):assert current.replace(b'\r\n',b'\n')==git('show',rev+':'+rel).replace(b'\r\n',b'\n'),(rev,rel)
 for rel,digest in source['old_bits'].items():assert sha((ROOT/rel).read_bytes())==digest,rel
 tracked=git('diff','--name-only').decode().splitlines();assert set(tracked)<= {'docs/GITHUB_REFERENCE_RESEARCH.md'},tracked
 assert not git('diff','--cached','--name-only').strip()
 remote=git('remote','get-url','origin').decode().strip();assert remote=='https://github.com/Philid14/anlogic-ph1p35-image-processing.git'
 refs=dict(line.split()[::-1] for line in git('ls-remote','origin','refs/heads/'+branch,'refs/tags/'+tag,'refs/tags/'+tag+'^{}').decode().splitlines())
 tagobj=git('rev-parse',tag).decode().strip();archive=git('rev-parse',tag+'^{}').decode().strip()
 assert refs['refs/heads/'+branch]==head
 assert refs['refs/tags/'+tag]==tagobj and refs['refs/tags/'+tag+'^{}']==archive
 receipt=dict(version=d['version'],time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),remote=remote,branch=branch,remote_head=head,source_commit=d['source_commit'],archive_commit=archive,tag=tag,tag_object=tagobj,bit_sha256=d['bit_sha256'],tagged_inputs_verified=len(source['files']),historical_bits_unchanged=len(source['old_bits']),push_status='SUCCESS',board_test='NOT_RUN',pr='See PR creation receipt; no merge authorization')
 out=ROOT/'docs/evidence/TRACK_REGION_FIX_V1/REMOTE_RECEIPT.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
