"""Check diagnosis on known static/moved edges and real nonempty/empty datasets."""
import argparse
import json
from pathlib import Path
import numpy as np
import temporal_capture_evaluation as evaluation
import temporal_stage_diagnosis as diagnosis


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old_evaluation', type=Path)
    parser.add_argument('new_evaluation', type=Path)
    args = parser.parse_args()
    old, new = [json.loads(p.read_text(encoding='utf-8')) for p in (args.old_evaluation, args.new_evaluation)]
    assert evaluation.edge_presence(old['historical_spatial_models'])['quality_nonempty_thresholds'] == []
    assert evaluation.edge_presence(new['historical_spatial_models'])['quality_nonempty_thresholds'] == [40, 60]
    x = np.indices((32, 128))[1]
    static = np.repeat(np.where(x < 64, 32, 200).astype(np.uint8)[:, :, None], 3, 2)
    frames = np.repeat(static[None], 8, 0)
    result, _ = diagnosis.diagnose(frames, 60)
    assert min(result['four_hop_samples']) > 0
    assert sum(result['nms_strong_flip_partition'].values()) == 0
    assert sum(d['output_changed'] for d in result['finite_four_hop_dependency']) == 0
    assert result['symmetric_nearest_distance_bins_0_1_2_3_4_gt4'][0] > 0
    assert not any(result['symmetric_nearest_distance_bins_0_1_2_3_4_gt4'][1:])
    frames[1::2] = np.roll(static, 2, axis=1)
    moved, _ = diagnosis.diagnose(frames, 60)
    assert sum(moved['nms_strong_flip_partition'].values()) > 0
    assert moved['four_hop_changed_samples_near_other_frame_within_2px'] > 0
    assert moved['four_hop_changed_samples_without_nearby_2px_match'] == 0
    assert diagnosis.components(np.eye(3, dtype=bool)) == dict(count=1, largest=3, sizes=[3])
    assert diagnosis.components(np.zeros((3, 3), bool)) == dict(count=0, largest=0, sizes=[])
    print('PASS: real empty/nonempty descriptions; fixed-edge zero flips; 2px displacement proxy; 8-connectivity')


if __name__ == '__main__':
    main()
