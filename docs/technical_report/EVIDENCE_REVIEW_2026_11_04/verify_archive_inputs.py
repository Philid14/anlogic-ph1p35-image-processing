"""Read-only comparison of an extracted original P35 package and fixed build input hashes."""
from pathlib import Path
import argparse,hashlib,json
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--root',type=Path,required=True,help='Original extracted P35 directory; check before opening TD')
 p.add_argument('--output',type=Path)
 a=p.parse_args();base=Path(__file__).resolve().parent
 m=json.loads((base/'BUILD_INPUT_EXPECTATIONS.json').read_text(encoding='utf-8'))
 root=a.root.resolve()
 if not root.is_dir():p.error('Original extracted source root does not exist')
 rows=[]
 expected=dict(m['files'])
 if m.get('al_path') and m.get('al_sha256'):expected[m['al_path']]=m['al_sha256']
 for relative,want in expected.items():
  f=(root/relative).resolve()
  if root not in f.parents:raise ValueError('Manifest path leaves supplied root')
  got=hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
  rows.append({'path':relative,'expected':want,'actual':got,'status':'MATCH' if got==want else 'MISSING' if got is None else 'DIFFERENT'})
 result={'scope':'ORIGINAL_BUILD_BYTE_CHECK_ONLY','root':str(root),'source_commit':m['source_commit'],
  'total':len(rows),'matched':sum(r['status']=='MATCH' for r in rows),'files':rows,
  'result':'PASS' if all(r['status']=='MATCH' for r in rows) else 'NEEDS_REVIEW',
  'not_tested':['RTL semantic equivalence','TD/P&R','bit identity of board footage','physical hardware performance']}
 if a.output:
  target=a.output.resolve()
  if target==root or root in target.parents:p.error('Write result outside original source directory')
  target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False,indent=2))
 return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
