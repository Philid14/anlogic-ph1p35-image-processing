"""Read-only checks of the final document package; PASS is not hardware acceptance."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import zipfile
import xml.etree.ElementTree as E

P = Path(__file__).resolve().parent
REPO = P.parents[2]
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(ref, path):
    return subprocess.check_output(
        ['git', '-c', 'core.longpaths=true', 'cat-file', 'blob', ref + ':' + path],
        cwd=REPO)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-git', action='store_true')
    parser.add_argument('--video', type=Path, help='Optional local original F01 MP4')
    parser.add_argument('--output', type=Path, help='Write result outside this frozen package')
    args = parser.parse_args()
    checks = []

    def ck(name, ok, details):
        checks.append({'name': name, 'passed': bool(ok), 'details': details})

    release = json.loads((P / 'RELEASE_CHECKS.json').read_text(encoding='utf-8'))
    rows = release['files']
    names = {x['path'] for x in rows}
    actual = {p.relative_to(P).as_posix() for p in P.rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and p.name != 'RELEASE_CHECKS.json'}
    ck('package_file_set', actual == names, {'expected': len(names), 'actual': len(actual)})
    bad = [x['path'] for x in rows if not (P / x['path']).is_file()
           or sha((P / x['path']).read_bytes()) != x['sha256']]
    ck('package_hashes', not bad, {'mismatches': bad, 'self_manifest_excluded': True})
    doc = next(P.glob('*.docx'))
    with zipfile.ZipFile(doc) as z:
        ck('zip_crc', z.testzip() is None, 'Word package')
        parts = {n: z.read(n) for n in z.namelist()}
    for n, b in parts.items():
        if n.endswith('.xml'):
            E.fromstring(b)
    root = E.fromstring(parts['word/document.xml'])
    body = root.find(W + 'body')

    def txt(e):
        return ''.join(t.text or '' for t in e.iter(W + 't'))

    paras = [txt(e) for e in body if e.tag == W + 'p']
    ck('five_parts', sum(s.startswith(('第一部分', '第二部分', '第三部分', '第四部分', '第五部分'))
                         for s in paras) == 5, 'official order retained')
    ck('references', sum(bool(re.match(r'^\[\d+\]', s)) for s in paras) == 2, 'only original references1 and11, renumbered1 and2')
    ck('pictures', len(root.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/picture}pic')) == 34,
       '30 source placements plus four native Word crops / 18 groups')
    ck('tables', len(root.findall('./' + W + 'body/' + W + 'tbl')) == 23, '23 native tables including the relation figure')
    ck('native_equation', len(root.findall('.//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath')) == 1,
       'original OMML')
    prior = next((P.parent / 'FINAL_REPORT_V3').glob('*.docx'))
    allow = {'word/document.xml', 'word/_rels/document.xml.rels',
             'docProps/core.xml', '[Content_Types].xml'}
    with zipfile.ZipFile(prior) as z:
        changed = [n for n in z.namelist() if n not in allow and parts.get(n) != z.read(n)]
    ck('preserved_parts', not changed, {'unexpected_changes': changed})
    limits = {'摘要': 800, '1.1': 400, '1.2': 400, '1.3': 400, '1.4': 200,
              '1.5': 200, '1.6': 200, '4.1': 300, '4.2': 1000}
    slots = {}
    key = None
    for e in body:
        s = txt(e)
        if e.tag == W + 'p' and (s == '摘要' or re.match(r'^第[一二三四五]部分|^[1-4]\.\d', s)):
            key = s.split()[0]
            slots[key] = ''
        elif key:
            slots[key] += s
    counts = {k: len(re.sub(r'\s+', '', slots[k])) for k in limits}
    ck('length_limits', all(counts[k] <= v for k, v in limits.items()), counts)
    selected = json.loads((P / 'SELECTED_MEDIA.json').read_text(encoding='utf-8'))
    ck('new_figures', all(sha((P / x['figure']).read_bytes()) == x['figure_sha256']
                           for x in selected['new']), 'no new source figures; inherited originals')
    layout = json.loads((P / 'FIGURE_LAYOUT.json').read_text(encoding='utf-8'))
    ck('native_word_crops', len(root.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}srcRect')) == 4
       and all(sha((P/'figures'/x['source_figure']).read_bytes()) == x['source_sha256'] for x in layout['crops']),
       'four native placement crops; original bytes unchanged')
    media = json.loads((P / 'MEDIA_INVENTORY.json').read_text(encoding='utf-8'))
    ck('video_scope', media['decode_exit'] == 0 and media['sampled_frames'] == 342
       and media['exact_recording_bit_sha256'] is None, 'edited video; recording bit not inferred')
    alltext = txt(root)
    descriptions = '\n'.join(e.get('descr', '') for e in root.iter() if e.tag.endswith('}docPr'))
    banned = ['配套索引', '见配套', '历史索引', '详见仓库', '参见仓库', 'MEDIA_INDEX.md', 'SELECTED_MEDIA.json', 'SOURCE_EVIDENCE.json']
    bad_prose = [s for s in banned if s in alltext + descriptions]
    ck('standalone_prose', not bad_prose, bad_prose)
    external = [rel.get('Target') for n, b in parts.items() if n.endswith('.rels')
                for rel in E.fromstring(b) if rel.get('TargetMode') == 'External']
    ck('zero_external_relationships', not external, external)
    ck('zero_hyperlinks', not root.findall('.//' + W + 'hyperlink'), 'all citations are inline text')
    ck('no_machine_paths', not re.search(r'(?<![A-Za-z])[A-Za-z]:[\\/]', alltext + descriptions),
       'no absolute machine paths in text or alternative descriptions')
    refs = [s for s in paras if re.match(r'^\[\d+\]', s)]
    ck('approved_references', len(refs) == 2
       and refs[0].startswith('[1] 上海安路信息科技股份有限公司.')
       and refs[1].startswith('[2] 竞赛技术文档模板'), 'two supplied official sources')
    ck('in_text_citations', set(re.findall(r'\[(\d+)\]', alltext)) == {'1', '2'},
       'no dangling old bibliography numbers')
    ck('inline_evidence', all(s in alltext for s in ['3.3.6', '图16', '图17', '图18', 'N0000', '尚有5项']),
       'decision evidence and scope embedded in report')
    ck('video_SHA_in_body', media['sha256'] in re.sub(r'\s+', '', alltext), 'full F01 identity in report')
    rns = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
    ck('embedded_images', not any(e.get(rns + 'link') for e in root.iter() if e.tag.endswith('}blip')),
       'pictures embedded; no linked image files')
    if args.video:
        ck('original_F01', args.video.is_file() and sha(args.video.read_bytes()) == media['sha256'],
           'original video SHA-256')
    evidence = json.loads((P / 'SOURCE_EVIDENCE.json').read_text(encoding='utf-8'))
    if args.check_git:
        bad = [x['path'] for x in evidence['sources']
               if sha(git(x['commit'], x['path'])) != x['sha256']]
        ck('fixed_evidence_objects', not bad, bad)
        bad = []
        matched = 0
        unresolved = []
        for x in evidence['input_blob_audit']:
            b = git(evidence['main_commit'], x['path'])
            old = git(evidence['hardware_source_commit'], x['path'])
            if b != old or sha(b) != x['git_blob_sha256']:
                bad.append(x['path'])
            lf = b.replace(b'\r\n', b'\n')
            if any(sha(v) == x['expected_build_input'] for v in [b, lf, lf.replace(b'\n', b'\r\n')]):
                matched += 1
            else:
                unresolved.append(x['path'])
        ck('191_git_blobs', len(evidence['input_blob_audit']) == 191 and not bad, bad)
        ck('raw_hash_audit_scope', matched == 184 and set(unresolved) == set(
            evidence['build_manifest_match_summary']['unresolved_raw_hash_paths']),
           {'direct_or_EOL_matches': matched, 'raw_hash_unresolved': len(unresolved),
            'meaning': 'historical audit reproduced; additive mixed-EOL proof checked separately'})
        update = json.loads((P / 'INPUT_AUDIT_UPDATE.json').read_text(encoding='utf-8'))
        solved = []
        pending = []
        bad = []
        original = {x['path']: x for x in evidence['input_blob_audit']}
        for x in update['files']:
            b = git(evidence['main_commit'], x['path'])
            expected = original[x['path']]['expected_build_input']
            if sha(b) != x['git_blob_sha256'] or expected != x['expected_build_sha256']:
                bad.append(x['path'])
            if x['status'] != 'FORMAT_MATCH_VERIFIED':
                pending.append(x['path'])
                continue
            lf = b.replace(b'\r\n', b'\n')
            lines = lf.splitlines(keepends=True)
            if x['path'].endswith('measure_background.v'):
                assert len(lines) == 71
                chosen = {71}
            elif x['path'].endswith('camera_to_dsi_display.sdc'):
                chosen = set(range(3, 14))
            else:
                raise ValueError('Unrecognized format reconstruction')
            raw = b''.join(line[:-1] + b'\r\n' if i in chosen and line.endswith(b'\n') else line
                           for i, line in enumerate(lines, 1))
            proof = x['format_reconstruction']
            if not (sha(raw) == expected == proof['sha256']
                    and len(raw) == proof['bytes'] and raw.replace(b'\r\n', b'\n') == lf):
                bad.append(x['path'])
            solved.append(x['path'])
        ck('additive_input_audit', not bad and len(solved) == 2 and len(pending) == 5
           and set(solved + pending) == set(unresolved)
           and update['current_content_relation_supported'] == matched + len(solved) == 186
           and update['remaining'] == len(pending),
           {'format_matches': len(solved), 'remaining_original_bytes': len(pending), 'mismatches': bad,
            'meaning': 'no new build or full original byte equivalence claimed'})
        source_manifest = json.loads(git(evidence['main_commit'],
            'artifacts/bitstreams/FINAL_SUBMISSION_REBUILD_V1/build_evidence/SOURCE_MANIFEST.json'))
        al = source_manifest['al_path']
        ck('TD_project_blob', git(evidence['main_commit'], al) == git(evidence['hardware_source_commit'], al),
           'TD .al Git content unchanged')
        ck('final_bit', sha(git(evidence['main_commit'], evidence['bit_path'])) == evidence['bit_sha256'],
           evidence['hardware_version'])
    report = {'scope': 'DOCUMENT_AND_READ_ONLY_EVIDENCE',
              'result': 'PASS' if all(x['passed'] for x in checks) else 'FAIL',
              'checks': checks, 'docx_sha256': sha(doc.read_bytes()),
              'not_verified': ['five original build byte hashes',
                               'exact recording bit identity for edited video',
                               'physical accuracy, true latency and long-run stability',
                               'new RTL/TD/P&R/hardware tests']}
    if args.output:
        if P == args.output.resolve().parent or P in args.output.resolve().parents:
            parser.error('--output must be outside this frozen package')
        args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
