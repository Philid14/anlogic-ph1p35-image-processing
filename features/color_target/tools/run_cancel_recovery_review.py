"""Run a read-only warm-stream CSI-stop review against a pinned MAIN snapshot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--snapshot-manifest', type=Path, required=True)
    ap.add_argument('--msim', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    src, out, msim = a.source.resolve(), a.out.resolve(), a.msim.resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(a.snapshot_manifest.read_text(encoding='utf-8'))
    expected = {r['path']: r['sha256'] for r in manifest['files']}
    if manifest['commit'] != '5cbb1de3814a842067ee1ffd41df3d75bbf0de26':
        raise ValueError('Review is pinned to MAIN 5cbb1de; reassess harness on revision change')
    original = src / 'tests/tb_target_frame_system_active_epoch.sv'
    probe = HERE.parent / 'tb/tb_cancel_recovery_probe.svh'
    harness = original.read_text(encoding='utf-8').split('    integer issued_total=0,')[0]
    old = 'gray=(f+1)*12;'
    if harness.count(old) != 1:
        raise ValueError('Pinned scene marker changed')
    # Spatial grayscale reveals an offset error hidden by uniform backgrounds.
    harness = harness.replace(old, 'gray=16+((f*31+(px%239)+(py%233))%144);')
    tb = out / 'tb_cancel_recovery.sv'
    tb.write_text(harness + probe.read_text(encoding='utf-8'), encoding='utf-8')
    h = src / 'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
    ip = h.parent / 'ip_source'
    files = [tb, *[h / 'target' / n for n in (
        'target_frame_system.v', 'frame_bundle_cdc.v', 'frame_timebase.v',
        'target_observer_adapter.v', 'frame_transaction_ledger.v')],
        *sorted((src / 'features/color_target/rtl').glob('*.v')),
        *[h / n for n in ('video_in.v', 'video_out.v', 'mc_to_user_interface.v',
            'data_96bit_to_128bit.v', 'isp/fifo_event_counter.v', 'vtc/uivtc.v')]]
    for folder in ('w128_d512_fifo', 'w155_d512_fifo'):
        files += sorted((ip / folder).glob('*.v'))
    for p in files[1:] + [original]:
        if sha(p) != expected[p.relative_to(src).as_posix()]:
            raise ValueError(f'Snapshot hash mismatch: {p}')
    before = {str(p): sha(p) for p in files + [original, probe, Path(__file__).resolve()]}
    (out / 'SOURCE_MANIFEST.json').write_text(json.dumps(before, indent=2)+'\n')
    commands = [[str(msim/'vlib.exe'), 'work'],
        [str(msim/'vlog.exe'), '-sv', '-work', 'work', *map(str, files)],
        [str(msim/'vsim.exe'), '-c', '-quiet', '-lib', 'work', 'tb_target_frame_system',
         '+TRACE='+str(out/'events.txt'), '-do', 'onerror {quit -code 2}; run -all; quit -f -code 0']]
    stages = []
    env = dict(os.environ)
    env['PATH'] = str(msim)+os.pathsep+env.get('PATH', '')
    for i, command in enumerate(commands):
        start = time.monotonic()
        with (out/f'stage_{i}.txt').open('wb') as log:
            p = subprocess.run(command, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1500)
        text = (out/f'stage_{i}.txt').read_text(errors='replace')
        ok = p.returncode == 0 and '** Error:' not in text and '** Fatal:' not in text
        stages.append(dict(argv=command, exit_code=p.returncode, tool_ok=ok, elapsed_seconds=time.monotonic()-start))
        (out/'stages.json').write_text(json.dumps(stages, indent=2)+'\n')
        print('STAGE', i, 'tool_ok', ok, flush=True)
        if not ok:
            break
    final = (out/'stage_2.txt').read_text(errors='replace') if (out/'stage_2.txt').exists() else ''
    unchanged = all(sha(Path(p)) == v for p, v in before.items())
    passed = len(stages) == 3 and all(s['tool_ok'] for s in stages) and unchanged and final.count('PASS CANCEL_RECOVERY_TRACE') == 1 and 'FAIL' not in final
    report = dict(limited_invariants_passed=passed, assessment='REVIEW_REQUIRED',
        source_unchanged=unchanged, candidate_commit=manifest['commit'], stages=stages,
        scope='Actual digital MAIN/FIFOs with prior read lease; spatial synthetic pixels and bounded DDR. Not final HDMI pixel/PHY/P&R/board proof.')
    (out/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    print(final[-3500:], flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
