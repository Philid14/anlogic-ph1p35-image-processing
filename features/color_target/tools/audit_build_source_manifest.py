"""Read-only comparison of a source tree and a raw-byte build manifest.

Uniform or mixed CRLF/LF representations are accepted only if an EXACT SHA256
match is constructed. No whitespace stripping, encoding conversion, command
rewriting or source-file changes are performed. Never treats a missing file as
a match. Optional git-blob records bind downloaded bytes to pinned source.
"""
import argparse
import hashlib
import json
from pathlib import Path


def representations(raw, expected, search_limit=0):
    digest=lambda b:hashlib.sha256(b).hexdigest()
    lf=raw.replace(b'\r\n',b'\n')
    for name,data in [('raw',raw),('LF',lf),('CRLF',lf.replace(b'\n',b'\r\n'))]:
        if digest(data)==expected:
            return dict(kind=name,sha256=expected,bytes=len(data)),data
    parts=lf.split(b'\n');count=len(parts)-1
    if search_limit and 0<count<=search_limit and b'\0' not in lf:
        for mask in range(1<<count):
            data=b''.join(parts[i]+(b'\r\n' if mask&(1<<i) else b'\n')
                for i in range(count))+parts[-1]
            if digest(data)==expected:
                return dict(kind='MIXED_EOL_EXACT_SHA',sha256=expected,bytes=len(data),
                    crlf_lines=[i+1 for i in range(count) if mask&(1<<i)],
                    lf_lines=[i+1 for i in range(count) if not mask&(1<<i)]),data
    return None,None


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--download-records',type=Path)
    ap.add_argument('--byte-reference-root',type=Path,
        help='optional raw-byte witnesses; must exactly match manifest SHA and normalize to pinned Git bytes')
    ap.add_argument('--newline-search-limit',type=int,default=0)
    args=ap.parse_args()
    if not 0<=args.newline_search_limit<=20:ap.error('newline search must be 0..20')
    args.out.mkdir(parents=True,exist_ok=False)
    source_root=args.source_root.resolve()
    manifest=json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    downloads={}
    if args.download_records:
        downloads={x['path']:x for x in json.loads(args.download_records.read_text(encoding='utf-8-sig'))}
    rows=[]
    for name,expected in manifest['files'].items():
        path=(source_root/name).resolve();row=dict(path=name,expected_sha256=expected,passed=False)
        if not path.is_relative_to(source_root):
            row['reason']='path_escapes_source_root';rows.append(row);continue
        if not path.is_file():
            row['reason']='missing_file';rows.append(row);continue
        raw=path.read_bytes();row['raw_sha256']=hashlib.sha256(raw).hexdigest()
        if args.download_records:
            record=downloads.get(name)
            blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            if (record is None or record.get('commit')!=manifest['source_commit'] or
                blob!=record.get('blob_sha') or row['raw_sha256']!=record.get('sha256')):
                row['reason']='download_source_binding_mismatch';rows.append(row);continue
            row['git_blob_verified']=blob
        matched,data=representations(raw,expected,args.newline_search_limit)
        if matched is None and args.byte_reference_root:
            reference_root=args.byte_reference_root.resolve();reference=(reference_root/name).resolve()
            if reference.is_relative_to(reference_root) and reference.is_file():
                witness=reference.read_bytes()
                if (hashlib.sha256(witness).hexdigest()==expected and
                    witness.replace(b'\r\n',b'\n')==raw.replace(b'\r\n',b'\n')):
                    matched=dict(kind='EXACT_BYTE_REFERENCE_SAME_LF_CONTENT',sha256=expected,
                        bytes=len(witness),reference=str(reference))
                    data=witness
        if matched:
            row.update(passed=True,representation=matched)
            if matched['kind']=='MIXED_EOL_EXACT_SHA':
                dest=args.out/'exact-reconstructions'/name;dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(data);row['reconstruction']=str(dest.relative_to(args.out))
        else:row['reason']='no_exact_representation_match'
        rows.append(row)
    report=dict(schema=1,source_commit=manifest['source_commit'],source_root=str(source_root),
        manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        files=rows,total=len(rows),matched=sum(x['passed'] for x in rows),
        passed=bool(rows) and all(x['passed'] for x in rows),
        scope='Source-content binding only; no rebuilt bit, constraints coverage or board proof',
        source_mutated=False)
    (args.out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for row in rows:
        if not row['passed'] or row.get('representation',{}).get('kind')=='MIXED_EOL_EXACT_SHA':
            print(('PASS ' if row['passed'] else 'FAIL ')+row['path']+' '+str(row.get('representation',row.get('reason'))))
    print(f"BUILD_SOURCE_AUDIT_COMPLETE total={len(rows)} matched={report['matched']}")
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
