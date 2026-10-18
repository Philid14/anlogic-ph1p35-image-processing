"""Revalidate an actual capture, then reject a deliberately damaged post array.

Empty edge sets have no edge-conditioned flicker/location score. This tests PC
analysis gates only; it does not claim a hardware optimization or new capture.
"""
import argparse
import json
from pathlib import Path
import tempfile

import numpy as np
import temporal_roi_analysis as analysis


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    pre, post, meta, header = analysis.load_validated_capture(args.capture)
    temporary = Path(__file__).resolve().parents[1]/'tmp'
    temporary.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='temporal_analysis_gates_', dir=temporary))
    damaged = post.copy()
    damaged[0, 0, 0, 0] ^= np.uint8(1)
    np.savez_compressed(work/'damaged.npz', pre=pre, post=damaged,
                        meta=meta, global_header=header)
    try:
        analysis.load_validated_capture(work/'damaged.npz')
    except ValueError as error:
        assert str(error) == 'post array differs from CRC-validated AWB reconstruction'
    else:
        raise AssertionError('damaged post-AWB array accepted')
    roi = np.ones((8, 8), bool)
    empty = np.zeros((3, 8, 8), bool)
    score = analysis.metrics(empty, roi)
    assert score['flip_per_union'] is None
    assert score['mean_nearest_position_distance_original_pixels'] is None
    assert score['unmatched_beyond_4px_fraction'] is None
    assert score['flip_per_roi'] == 0 and score['mean_edge_samples'] == 0
    stable = empty.copy()
    stable[:, 4, 4] = True
    score = analysis.metrics(stable, roi)
    assert score['flip_per_union'] == 0
    assert score['mean_nearest_position_distance_original_pixels'] == 0
    assert score['mean_edge_samples'] == 1
    print(json.dumps(dict(valid_capture_revalidated=True, damaged_post_rejected=True,
                          empty_edges_not_reported_stable=True,
                          stable_nonempty_edge_reference_passed=True), indent=2))


if __name__ == '__main__':
    main()
