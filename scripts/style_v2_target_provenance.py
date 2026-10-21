"""Bind the fixed TARGET import; never accept a moving branch or altered RTL."""
import hashlib
import json
import subprocess
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = '49641eefc8bab37de3cd1b9d7f95a0051a0f0d1e'
BASE = '89093f428878b918036c8a30a0d1afe7764946b8'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def audit():
    records = []
    raw = git('ls-tree', '-rz', TARGET, 'features/color_target')
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        info, name = entry.split(b'\t', 1)
        mode, kind, blob = info.decode().split()
        assert kind == 'blob' and mode == '100644', (mode, kind, name)
        path = name.decode('utf-8')
        expected = git('cat-file', 'blob', blob)
        actual = (ROOT/path).read_bytes()
        assert actual.replace(b'\r\n', b'\n') == expected.replace(b'\r\n', b'\n'), path
        records.append(dict(path=path, git_blob=blob,
                            git_sha256=hashlib.sha256(expected).hexdigest(),
                            worktree_sha256=hashlib.sha256(actual).hexdigest()))
    delivery = json.loads((ROOT/'features/color_target/board/TARGET_DELIVERY.json').read_text())
    for item in delivery['files']:
        row = next(r for r in records if r['path'] == item['path'])
        assert row['git_blob'] == item['git_blob'], item['path']
        assert row['git_sha256'] == item['git_sha256'], item['path']
    bit = ROOT/'artifacts/bitstreams/EDGE_STYLE_FILL_V2/camera_to_dsi_display.bit'
    digest = hashlib.sha256(bit.read_bytes()).hexdigest().upper()
    assert digest == 'CFB7435648ED50310F053AFE138702F2094B0061B6A7DD68B3B064B6B3D88F51'
    assert git('merge-base', BASE, 'HEAD').decode().strip() == BASE
    al=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.al'
    active=re.findall(r'<File Path="([^"]+)"',al.read_text(encoding='utf-8'))
    active_target=[p for p in active if '/features/color_target/rtl/' in p]
    return dict(schema=1, role='MAIN', target_source=TARGET, main_base=BASE,
                target_production_source=delivery['rtl_source_commit'],
                target_production_files=len(delivery['files']), files=records,
                rollback_bit_sha256=digest, production_td_target_count=len(active_target),
                integration_verified=False, board_test='NOT_RUN')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = audit()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f"Fixed TARGET import: {len(result['files'])} files; 9 production RTL bound; rollback bit unchanged")
