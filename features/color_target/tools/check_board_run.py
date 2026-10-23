"""Validate manually recorded board observations; never certify board acceptance.

Exit 0=no observed failure, 1=failure/review, 2=incomplete evidence, 3=invalid
record. Missing measurements and saturating counters cannot become a PASS.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

COUNTERS = ('fifo_startup', 'fifo_steady', 'dropped', 'cancelled', 'metadata_fault',
            'duplicate', 'reorder', 'wrong_session', 'identity_error', 'invalid',
            'guard_cancelled', 'stale', 'time_error', 'timeout')
OBSERVATIONS = ('video_live', 'logo_visible', 'no_visible_artifacts', 'annotation_atomic')


def load_record(text):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate JSON key: '+key)
            value[key] = item
        return value
    def reject(value):
        raise ValueError('Non-JSON number: '+value)
    return json.loads(text, object_pairs_hook=unique, parse_constant=reject)


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def parse_osd(identity_line, reason_line):
    """Explicit fixed candidate format; hexadecimal, no OCR guessing."""
    a = re.fullmatch(r'([S!])([0-9A-Fa-f]{8})\s+F([0-9A-Fa-f]{8})\s+G([0-9A-Fa-f]{8})\s+L([0-3])\s+D([0-9A-Fa-f]{4})\s+C([0-9A-Fa-f]{4})\s+Q([0-9A-Fa-f]{4})\s*', identity_line)
    b = re.fullmatch(r'D([0-9A-Fa-f]{4})\s+R([0-9A-Fa-f]{4})\s+W([0-9A-Fa-f]{4})\s+I([0-9A-Fa-f]{4})\s+V([0-9A-Fa-f]{4})\s+C([0-9A-Fa-f]{4})\s+S([0-9A-Fa-f]{4})\s+T([0-9A-Fa-f]{4})\s+O([0-9A-Fa-f]{4})\s*', reason_line)
    if not a or not b:
        raise ValueError('OSD text does not match STYLE_V2_TARGET_V1; do not guess missing characters')
    identity = dict(zip(('session', 'frame', 'generation', 'slot'), (int(x, 16) for x in a.groups()[1:5])))
    identity['online'] = a[1] == 'S'
    counters = dict(zip(COUNTERS[2:5], (int(x, 16) for x in a.groups()[5:])))
    counters.update(zip(COUNTERS[5:], (int(x, 16) for x in b.groups())))
    return identity, counters


def template():
    return {'schema': 'target-board-run-v1',
            'version': {'tag': 'style-v2-target-v1-candidate', 'source_commit': '7c7e5ee7d6c52260bcf557d9dabd4014f84e2687',
                        'bit_sha256': '2172e53406af5d67bd2a167c8935f6c9870cc0ac6e79382217f13024df7888ff'},
            'environment': {'camera_height_mm': None, 'field_of_view_mm': None,
                            'lighting': None, 'sensor_settings': None},
            'samples': [{'boot_id': 'cold-start-1', 't_s': 30, 'phase': 'steady',
                         'identity_line': None, 'reason_line': None,
                         'counters': {k: None for k in COUNTERS[:2]},
                         'observations': {k: None for k in OBSERVATIONS}, 'evidence': []}]}


def evaluate(data, base, bit=None):
    if not isinstance(data, dict):
        raise ValueError('Record must be an object')
    if data.get('schema') != 'target-board-run-v1':
        raise ValueError('Unsupported record schema')
    version = data.get('version', {})
    if not isinstance(version, dict):
        raise ValueError('version must be an object')
    for key, length in (('source_commit', 40), ('bit_sha256', 64)):
        if not isinstance(version.get(key), str) or not re.fullmatch('[0-9a-f]{'+str(length)+'}', version[key]):
            raise ValueError('Missing/invalid version.'+key)
    if not isinstance(version.get('tag'), str) or not version['tag'].strip():
        raise ValueError('Missing version.tag')
    samples = data.get('samples')
    if not isinstance(samples, list) or not samples:
        raise ValueError('At least one sample required')
    findings, intervals, evidence = [], [], []
    def note(level, message, sample=None):
        findings.append(dict(level=level, message=message, sample=sample))
    if bit is None:
        note('incomplete', 'Actual bit file hash not checked')
    elif file_sha(bit) != version['bit_sha256']:
        note('failure', 'Actual bit file SHA256 differs from declared version')
    env = data.get('environment', {})
    if not isinstance(env, dict):
        raise ValueError('environment must be an object')
    if any(env.get(k) in (None, '') for k in ('camera_height_mm', 'field_of_view_mm', 'lighting', 'sensor_settings')):
        note('incomplete', 'Environment/settings not fully recorded')
    normalized = []
    for i, row in enumerate(samples):
        if not isinstance(row, dict):
            raise ValueError(f'Sample {i}: must be an object')
        boot, t, phase = row.get('boot_id'), row.get('t_s'), row.get('phase')
        if not isinstance(boot, str) or not boot.strip():
            raise ValueError(f'Sample {i}: boot_id required')
        if type(t) not in (int, float) or not math.isfinite(t) or t < 0:
            raise ValueError(f'Sample {i}: finite nonnegative t_s required')
        if phase not in ('warmup', 'steady', 'fault', 'recovery'):
            raise ValueError(f'Sample {i}: invalid phase')
        counters = row.get('counters', {})
        if not isinstance(counters, dict) or set(counters)-set(COUNTERS):
            raise ValueError(f'Sample {i}: unknown/invalid counter name')
        counters = dict(counters)
        if row.get('identity_line') is not None or row.get('reason_line') is not None:
            if not isinstance(row.get('identity_line'), str) or not isinstance(row.get('reason_line'), str):
                raise ValueError(f'Sample {i}: both OSD lines required')
            identity, parsed = parse_osd(row['identity_line'], row['reason_line'])
            if not identity['online']:
                note('incomplete', 'OSD metadata transport offline', i)
            for name, value in parsed.items():
                if counters.get(name) not in (None, value):
                    raise ValueError(f'Sample {i}: conflicting OSD/counter transcription')
                counters[name] = value
        else:
            identity = None
            note('incomplete', 'OSD identity/reason lines not recorded', i)
        for key in COUNTERS:
            value = counters.get(key)
            if value is None:
                note('incomplete', 'Counter not measured: '+key, i)
            elif type(value) is not int or not 0 <= value <= 65535:
                raise ValueError(f'Sample {i}: {key} must be null or uint16 integer')
        obs = row.get('observations', {})
        if not isinstance(obs, dict) or set(obs)-set(OBSERVATIONS):
            raise ValueError(f'Sample {i}: unknown/invalid observation')
        for key in OBSERVATIONS:
            value = obs.get(key)
            if value is None:
                note('incomplete', 'Observation not measured: '+key, i)
            elif type(value) is not bool:
                raise ValueError(f'Sample {i}: {key} must be bool or null')
            elif not value:
                note('failure', 'Observed failed condition: '+key, i)
        paths = row.get('evidence', [])
        if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
            raise ValueError(f'Sample {i}: evidence must be a list of paths')
        if not paths:
            note('incomplete', 'No photo/video evidence linked', i)
        for name in paths:
            p = Path(name)
            p = p if p.is_absolute() else base/p
            if not p.is_file():
                note('incomplete', 'Evidence file missing: '+name, i)
            else:
                evidence.append(dict(sample=i, path=name, sha256=file_sha(p)))
        normalized.append(dict(boot_id=boot, t_s=t, phase=phase, counters=counters, identity=identity))
    comparable = 0
    for i, (a, b) in enumerate(zip(normalized, normalized[1:]), 1):
        if a['boot_id'] != b['boot_id']:
            intervals.append(dict(before=i-1, after=i, status='boot_changed_no_delta'))
            continue
        if b['t_s'] <= a['t_s']:
            raise ValueError(f'Sample {i}: time must increase within the same boot')
        comparable += 1
        deltas = {}
        for key in COUNTERS:
            x, y = a['counters'].get(key), b['counters'].get(key)
            if x is None or y is None:
                deltas[key] = dict(status='unmeasured')
            elif y < x:
                deltas[key] = dict(status='decreased_unknown_reset_or_transcription')
                note('incomplete', 'Counter decreased; no modulo/wrap delta inferred: '+key, i)
            elif x == 65535:
                deltas[key] = dict(status='saturated_unknown', lower_bound=0)
                note('incomplete', 'Saturated counter cannot prove zero events: '+key, i)
            else:
                delta = y-x
                deltas[key] = dict(status='lower_bound' if y == 65535 else 'exact', value=delta)
                if y == 65535:
                    note('incomplete', 'Counter reached saturation: '+key, i)
                if delta and key == 'fifo_steady':
                    note('failure', 'Post-warmup write/full frame counter increased', i)
                elif delta and key != 'fifo_startup':
                    note('review', 'Diagnostic increased; correlate with operation/policy: '+key, i)
        # Repeated/skipped display frame IDs alone are deliberately not alarms.
        intervals.append(dict(before=i-1, after=i, status='compared', counters=deltas))
    if not comparable:
        note('incomplete', 'No before/after interval within one boot')
    levels = {r['level'] for r in findings}
    assessment = ('OBSERVED_FAILURE' if 'failure' in levels else 'REVIEW_REQUIRED' if 'review' in levels
                  else 'INCOMPLETE' if 'incomplete' in levels else 'NO_OBSERVED_FAILURE')
    return dict(schema='target-board-analysis-v1', assessment=assessment,
                board_acceptance='NOT_CERTIFIED', version=version,
                provenance='Declared version plus optional actual file SHA; no Git/tag provenance certification',
                findings=findings, intervals=intervals, evidence=evidence)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('record', nargs='?', type=Path)
    ap.add_argument('--bit', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--template', type=Path)
    a = ap.parse_args()
    if a.template:
        with a.template.open('x', encoding='utf-8') as f:
            json.dump(template(), f, ensure_ascii=False, indent=2); f.write('\n')
        return 0
    if not a.record or not a.out:
        ap.error('record and --out are required')
    try:
        result = evaluate(load_record(a.record.read_text(encoding='utf-8-sig')), a.record.resolve().parent, a.bit)
        code = {'NO_OBSERVED_FAILURE': 0, 'OBSERVED_FAILURE': 1, 'REVIEW_REQUIRED': 1, 'INCOMPLETE': 2}[result['assessment']]
    except (ValueError, TypeError, KeyError, OSError) as e:
        result = dict(assessment='INVALID_RECORD', board_acceptance='NOT_CERTIFIED', error=str(e)); code = 3
    with a.out.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2); f.write('\n')
    print(json.dumps(dict(assessment=result['assessment'], board_acceptance='NOT_CERTIFIED'), ensure_ascii=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
