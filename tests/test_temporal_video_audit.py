"""Exercise complete/incomplete phone-video gates with synthetic lossless video."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
import temporal_transport as transport
import temporal_video_audit as audit


def main():
    import cv2
    root = Path(__file__).resolve().parents[1]
    (root/'tmp').mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='temporal_video_audit_', dir=root/'tmp'))
    rng = np.random.default_rng(20261018)
    pre = rng.integers(0, 256, (8, 16, 32, 3), dtype=np.uint8)
    depth = pre.size//12
    values = [int.from_bytes(row, 'big') for row in pre.reshape(-1, 12)]
    raw = [(value >> (32*plane)) & 0xffffffff
           for plane in range(3) for value in values]
    meta = np.zeros((8, 16), np.uint32)
    meta[:, 0] = np.arange(600, 608)
    meta[:, 1:3] = 65536
    meta[:, 7] = (12 << 17) | (1 << 16)
    for frame in range(8):
        meta[frame, 8:10] = transport.crc(pre[frame].tobytes())
    meta[:, 10] = 230400
    meta[:, 11] = (720 << 16) | 320
    meta[:, 13] = 128 << 16
    meta[:, 14] = 172800
    global_header = np.array([0x54524f31, 0x10000, 600, (32 << 16) | 16,
        (576 << 16) | 344, 8, 128, 600, depth*3, depth*3, 128,
        depth*3+128, depth*3+144, 1280, 720, transport.crc(pre.tobytes())], np.uint32)
    words = np.array(raw+meta.ravel().tolist()+global_header.tolist(), np.uint32)
    pages = transport.encode(words, int(global_header[15]))
    results = {}
    for name, indices in [('complete', list(range(len(pages)))+[0]),
                          ('missing_page_2', [i for i in range(len(pages)) if i != 2])]:
        video = work/f'{name}.avi'
        writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*'FFV1'), 10, (1280, 720))
        assert writer.isOpened()
        for index in indices:
            writer.write(cv2.cvtColor(transport.render(pages[index]), cv2.COLOR_RGB2BGR))
        writer.release()
        previous = sys.argv
        sys.argv = ['temporal_video_audit.py', str(video), '--output', str(work/name)]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                audit.main()
        finally:
            sys.argv = previous
        report = json.loads((work/name/'decode_audit.json').read_text())
        assert report['frames_examined'] == len(indices)
        if name == 'complete':
            assert report['status'] == 'complete_capture_validated'
            data = np.load(work/name/'capture.npz')
            for key, expected in [('pre', pre), ('post', pre), ('meta', meta),
                                  ('global_header', global_header)]:
                assert np.array_equal(data[key], expected), key
            assert report['coverage'][0]['valid_observations'] == 2
        else:
            assert report['status'] == 'incomplete_or_invalid_do_not_analyze'
            assert report['missing_pages_0based'] == [2]
            assert not (work/name/'capture.npz').exists()
        results[name] = report['status']
    print(json.dumps(dict(synthetic_only=True, pages=len(pages), results=results), indent=2))


if __name__ == '__main__':
    main()
