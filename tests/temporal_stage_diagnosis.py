"""Replay existing spatial stages on CRC-validated RGB. No new edge algorithm.

Boolean partitions isolate decision changes, not physical causal percentages.
All metrics exclude a seven-sample spatial halo; no temporal ground truth.
"""
import argparse
from collections import deque
import json
from pathlib import Path

import numpy as np
import temporal_roi_analysis as analysis
import edge_stability_model as spatial
import edge_quality_model as quality


def shift(a, k):
    return np.roll(a, (-k, -k), (0, 1))


def components(a):
    """8-connectivity on the clipped common interior, not full-frame topology."""
    unseen = set(map(tuple, np.argwhere(a)))
    sizes = []
    while unseen:
        todo = deque([unseen.pop()])
        size = 0
        while todo:
            y, x = todo.popleft()
            size += 1
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if (y+dy, x+dx) in unseen:
                        unseen.remove((y+dy, x+dx))
                        todo.append((y+dy, x+dx))
        sizes.append(size)
    return dict(count=len(sizes), largest=max(sizes, default=0), sizes=sorted(sizes, reverse=True))


def expanded(mask, steps=4):
    out = mask.copy()
    for _ in range(steps):
        out |= np.logical_or.reduce(quality.neighbors(out))
    return out


def diagnose(post, threshold):
    states = [spatial.stages(frame, True, threshold) for frame in post]
    roi = np.zeros(post.shape[1:3], bool)[:, ::2].copy()
    roi[7:-7, 7:-7] = True
    mags = np.array([shift(s['mag'], 2) for s in states])
    centers = np.array([shift(s['detail']['center'], 3) for s in states])
    keep = np.array([shift(s['detail']['keep'], 3) for s in states])
    nm = np.array([shift(s['detail']['magnitude'], 3) for s in states])
    strong, weak = nm >= threshold, nm >= threshold//2
    active = np.array([shift(s['labels'][-1][1], 7) for s in states])
    assert np.array_equal(mags[:, roi], centers[:, roi]), 'gradient/NMS center alignment'
    assert np.array_equal(strong[:, roi], ((mags >= threshold) & keep)[:, roi])
    for m, current in zip(nm, active):
        assert np.array_equal(quality.propagate(m, threshold, 4)[roi], current[roi])
    mag_cross = (mags[1:] >= threshold) ^ (mags[:-1] >= threshold)
    peak_cross = keep[1:] ^ keep[:-1]
    flips = strong[1:] ^ strong[:-1]
    partition = dict(
        magnitude_threshold_only=int((flips & mag_cross & ~peak_cross)[:, roi].sum()),
        nms_keep_only=int((flips & ~mag_cross & peak_cross)[:, roi].sum()),
        both=int((flips & mag_cross & peak_cross)[:, roi].sum()))
    assert sum(partition.values()) == int(flips[:, roi].sum())
    propagation = []
    for a, b, sa, sb, wa, wb in zip(active[:-1], active[1:], strong[:-1], strong[1:], weak[:-1], weak[1:]):
        changed = (a ^ b) & roi
        seeds_near = expanded(sa ^ sb)
        weak_near = expanded(wa ^ wb)
        assert not (changed & ~seeds_near & ~weak_near).any(), 'unexplained finite-hop change'
        propagation.append(dict(output_changed=int(changed.sum()),
            seed_change_near_only=int((changed & seeds_near & ~weak_near).sum()),
            weak_change_near_only=int((changed & ~seeds_near & weak_near).sum()),
            both_near=int((changed & seeds_near & weak_near).sum())))
    near, far, dist_hist = 0, 0, np.zeros(6, int)
    # Nearest-neighbor proxy, not tracking: the last bin is >4px, NOT 5px.
    for a, b in zip(active[:-1], active[1:]):
        for before, after in ((a, b), (b, a)):
            d = analysis.distance_to(before)
            changed = after & ~before & roi
            near += int((changed & (d <= 2)).sum())
            far += int((changed & (d > 2)).sum())
            dist_hist += np.bincount(d[after & roi], minlength=6)
    result = dict(threshold=threshold,
        strong_samples=strong[:, roi].sum(1).tolist(), weak_samples=weak[:, roi].sum(1).tolist(),
        four_hop_samples=active[:, roi].sum(1).tolist(),
        strong_components=[components(a[7:-7, 7:-7]) for a in strong],
        four_hop_components=[components(a[7:-7, 7:-7]) for a in active],
        nms_strong_flip_partition=partition,
        finite_four_hop_dependency=propagation,
        four_hop_changed_samples_near_other_frame_within_2px=near,
        four_hop_changed_samples_without_nearby_2px_match=far,
        symmetric_nearest_distance_bins_0_1_2_3_4_gt4=dist_hist.tolist(),
        physical_cause_percentages=None, true_contour_displacement=None,
        note='clipped ROI topology and nearest-neighbor proxies; no labels, optical flow or physical cause attribution')
    return result, (mags, strong, active)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pre, post, meta, header = analysis.load_validated_capture(args.capture)
    args.output.mkdir(parents=True, exist_ok=True)
    results, planes = {}, {}
    for th in (40, 60, 80):
        results[th], planes[th] = diagnose(post, th)
    (args.output/'stage_diagnosis.json').write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(8, 4, figsize=(14, 12), layout='constrained')
    mag, strong, active = planes[40]
    for f, row in enumerate(axes):
        row[0].imshow(post[f, 7:-7, 14:-14], interpolation='nearest')
        for ax, a, vmax, cmap in zip(row[1:], (mag[f], strong[f], active[f]), (80, 1, 1), ('magma', 'gray', 'gray')):
            ax.imshow(np.repeat(a[7:-7, 7:-7], 2, axis=1), interpolation='nearest', vmin=0, vmax=vmax, cmap=cmap)
        row[0].set_ylabel(f'SOF {meta[f, 0]}')
        for ax in row:
            ax.set_xticks([]); ax.set_yticks([])
    for ax, title in zip(axes[0], ('Actual RGB / common interior', 'Gaussian + Sobel / 0..80', 'NMS strong / TH40', 'Four spatial hops / TH40')):
        ax.set_title(title, fontsize=10)
    fig.suptitle('Decoded REAL RGB and existing-model replay; pixels enlarged, no brightness enhancement\n18 rows x 100 original pixels; no true-contour annotation')
    fig.savefig(args.output/'stage_contact.png', dpi=150); plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout='constrained')
    for ax, th in zip(axes, (40, 60, 80)):
        a = planes[th][2]
        count = (a[1:] ^ a[:-1]).sum(0)
        plot = ax.imshow(np.repeat(count[7:-7, 7:-7], 2, axis=1), vmin=0, vmax=7, cmap='magma', interpolation='nearest')
        ax.set_title(f'TH{th}: changed times / 7 transitions')
        ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(plot, ax=axes, shrink=.5, label='Same-coordinate binary changes')
    fig.suptitle('Four-hop output flicker map; empty TH80 is not measured contour stability')
    fig.savefig(args.output/'flicker_maps.png', dpi=150); plt.close(fig)
    print('PASS: CRC, center alignment, exact four-hop replay, transition partitions and dependency bounds')


if __name__ == '__main__':
    main()
