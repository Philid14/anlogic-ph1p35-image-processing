"""Read-only, standard-library checks. PASS applies to evidence packaging only."""
from pathlib import Path
import argparse, hashlib, json, subprocess, zipfile, xml.etree.ElementTree as E

P=Path(__file__).resolve().parent
REPO=P.parents[2]
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(ref,path):return subprocess.check_output(['git','-c','core.longpaths=true','cat-file','blob',ref+':'+path],cwd=REPO)
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check-git',action='store_true');ap.add_argument('--qq-dir',type=Path);ap.add_argument('--original-dir',type=Path);ap.add_argument('--output',type=Path);args=ap.parse_args()
 checks=[]
 def ck(k,b,v):checks.append({'name':k,'passed':bool(b),'details':v})
 f=next(P.glob('*.docx'))
 with zipfile.ZipFile(f) as z:
  ck('zip',z.testzip() is None,'ZIP CRC');parts={n:z.read(n) for n in z.namelist()}
  for n,b in parts.items():
   if n.endswith('.xml'):E.fromstring(b)
 manifest=json.loads((P/'RELEASE_CHECKS.json').read_text(encoding='utf-8'))
 ck('file_manifest',all((P/x['path']).is_file() and sha((P/x['path']).read_bytes())==x['sha256'] for x in manifest['files']),'files excluding self-hashed RELEASE_CHECKS.json')
 root=E.fromstring(parts['word/document.xml']);body=root.find(W+'body')
 def txt(e):return ''.join(t.text or '' for t in e.iter(W+'t'))
 paras=[txt(e) for e in body if e.tag==W+'p']
 ck('five_parts',sum(x.startswith(('第一部分','第二部分','第三部分','第四部分','第五部分')) for x in paras)==5,'official structure')
 ck('references',sum(x.startswith('[') and x.split(']')[0][1:].isdigit() for x in paras)==20,'20 entries')
 ck('images',len(root.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/picture}pic'))==30,'30 inherited/new pictures')
 ck('equation',len(root.findall('.//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath'))==1,'native equation')
 ck('template_parts',sha(parts['word/header1.xml'])==sha(zipfile.ZipFile(next((P.parent/'REAL_MEDIA_REVIEW_V6').glob('*.docx'))).read('word/header1.xml')),'official header preserved')
 selected=json.loads((P/'SELECTED_MEDIA.json').read_text(encoding='utf-8'))
 ck('new_figures',all(sha((P/x['figure']).read_bytes())==x['figure_sha256'] for x in selected['new']),'source times and crop separately recorded')
 ev=json.loads((P/'SOURCE_EVIDENCE.json').read_text(encoding='utf-8'))
 if args.check_git:
  failed=[]
  for x in ev['sources']:
   if sha(git(x['commit'],x['path']))!=x['sha256']:failed.append(x['path'])
  ck('fixed_sources',not failed,failed)
  rows=ev['independently_rehashed_formal_inputs'];bad=[];matches=0
  for x in rows:
   b=git(ev['delivery_commit'],x['path']);built=git(ev['actual_TD_source'],x['path'])
   if sha(b)!=x['git_blob_sha256'] or b!=built:bad.append(x['path'])
   variants=[b,b.replace(b'\r\n',b'\n'),b.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')]
   matches+=any(sha(v)==x['expected_build_input'] for v in variants)
  ck('95_git_input_blobs',len(rows)==95 and not bad,{'different':bad})
  ck('manifest_match_boundary',matches==90 and len(ev['build_input_hash_limit']['raw_build_hash_unresolved'])==5,{'direct_or_EOL_matches':matches,'raw_hash_unresolved':5})
  ck('archived_bit',sha(git(ev['delivery_commit'],ev['bit_path']))==ev['bit_sha256'],'bit bytes from fixed Git object')
 media=json.loads((P/'MEDIA_INVENTORY.json').read_text(encoding='utf-8'))
 for kind,directory in [('QQ',args.qq_dir),('ORIGINAL',args.original_dir)]:
  if directory:
   rows=[x for x in media['items'] if x['source_kind']==kind]
   ck('original_files_'+kind,all((directory/x['file']).is_file() and sha((directory/x['file']).read_bytes())==x['sha256'] for x in rows),len(rows))
 report={'scope':'DOCUMENT_EVIDENCE_ONLY','result':'PASS' if all(x['passed'] for x in checks) else 'FAIL','checks':checks,'not_verified':['hardware latency/accuracy/stability','full original TD byte closure for five files','new RTL or P&R'],'docx_sha256':sha(f.read_bytes())}
 if args.output:args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
