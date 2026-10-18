"""Audit phone transport frame by frame, retaining only CRC-valid pages.

Uses the existing optical decoder and all original packet/capture gates.
Incomplete recordings produce an explicit audit, never an analyzable capture.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import temporal_transport as transport


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def finalize_capture(info, pages, output):
    """Check saved CRC-valid pages; video container frame count is advisory.

    A phone container may count an undisplayed frame. Missing optical pages or
    FPGA capture integrity failures, rather than that metadata, gate analysis.
    """
    info['video_frame_count_metadata_delta'] = info['frames_examined']-info['reported_frames']
    info['finalizer_sha256'] = sha256(Path(__file__))
    try:
        if info['conflicting_duplicates']:
            raise ValueError('conflicting CRC-valid duplicate pages')
        blobs = [p.read_bytes() for p in sorted(pages.glob('*.bin'))]
        words = transport.assemble(blobs)
        pre, post, meta, global_header = transport.unpack_capture(words)
        identities = {tuple(x) for x in info['page_identities']}
        identity = next(iter(identities))
        if identity != (len(words), int(global_header[15]), (len(words)+246)//247):
            raise ValueError('packet identity does not match reconstructed capture')
        np.savez_compressed(output / 'capture.npz', pre=pre, post=post,
                            meta=meta, global_header=global_header)
        info.update(status='complete_capture_validated', word_sha256=hashlib.sha256(
            transport.words_bytes(words)).hexdigest(), capture_frames=len(pre),
            roi_shape=list(pre.shape), capture_gate_error=None)
    except (ValueError, AssertionError) as error:
        info.update(status='incomplete_or_invalid_do_not_analyze',
                    capture_gate_error=str(error), capture_frames=None)
    (output / 'decode_audit.json').write_text(
        json.dumps(info, indent=2)+'\n', encoding='utf-8')
    return info


def main():
    import cv2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    pages = args.output / 'pages'
    pages.mkdir(exist_ok=True)
    # A fresh audit must not inherit a previous capture or a different video.
    if any(args.output.glob('capture.*')) or any(pages.iterdir()):
        raise ValueError('use a fresh output directory for a complete video audit')
    cap = cv2.VideoCapture(str(args.input))
    if not cap.isOpened():
        raise ValueError('cannot open video')
    cv2.setNumThreads(1)
    info = dict(input_name=args.input.name, input_bytes=args.input.stat().st_size,
                input_sha256=sha256(args.input), opencv=cv2.__version__,
                reported_frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                reported_fps=cap.get(cv2.CAP_PROP_FPS),
                reported_width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                reported_height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                decoder_sha256=sha256(Path(transport.__file__)),
                audit_sha256=sha256(Path(__file__)), stride=1)
    frame = 0
    valid_frames = 0
    identities = set()
    coverage = {}
    conflicts = []
    with (args.output / 'frame_ledger.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['video_frame_0based', 'video_pts_ms', 'crc_valid_pages'])
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            pts = float(cap.get(cv2.CAP_PROP_POS_MSEC))
            blobs = transport.decode_image(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            found = []
            for blob in blobs:
                ident, index, _ = transport.check_page(blob)
                identities.add(ident)
                name = f'{ident[1]:08x}_{index:04d}.bin'
                dest = pages / name
                if dest.exists() and dest.read_bytes() != blob:
                    conflicts.append(dict(frame=frame, name=name))
                elif not dest.exists():
                    dest.write_bytes(blob)
                    print(f'CRC-valid page {index}; frame {frame}; PTS {pts:.3f} ms', flush=True)
                record = coverage.setdefault(name, dict(index=index, identity=list(ident),
                    valid_observations=0, first_frame=frame, first_pts_ms=pts))
                record.update(last_frame=frame, last_pts_ms=pts)
                record['valid_observations'] += 1
                found.append(index)
            valid_frames += bool(blobs)
            writer.writerow([frame, f'{pts:.6f}', ';'.join(map(str, found))])
            frame += 1
            if frame % 300 == 0:
                print(f'Examined {frame} frames; {len(coverage)} unique pages', flush=True)
    cap.release()
    info.update(frames_examined=frame, crc_valid_video_frames=valid_frames,
                frames_without_crc_valid_page=frame-valid_frames,
                page_identities=[list(x) for x in sorted(identities)],
                unique_pages=len(coverage), conflicting_duplicates=conflicts,
                coverage=sorted(coverage.values(), key=lambda x: (x['identity'], x['index'])))
    missing = None
    if len(identities) == 1:
        identity = next(iter(identities))
        missing = sorted(set(range(identity[2])) - {x['index'] for x in coverage.values()})
    info['missing_pages_0based'] = missing
    finalize_capture(info, pages, args.output)
    print(json.dumps({k: v for k, v in info.items() if k != 'coverage'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
