"""Describe a validated real capture without inventing edge/motion ground truth.

This evaluates the existing spatial models and existing offline proposals only.
No algorithm is installed in the FPGA path. Empty edge sets are not successes.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import temporal_roi_analysis as analysis
import edge_stability_model as spatial
import edge_denoise_model as denoise


def rgb_summary(images):
    delta = images[1:].astype(np.int32)-images[:-1].astype(np.int32)
    return dict(frame_channel_mean=images.mean((1, 2)).tolist(),
                channel_min=images.min((0, 1, 2)).tolist(),
                channel_max=images.max((0, 1, 2)).tolist(),
                transition_mae=np.abs(delta).mean((1, 2, 3)).tolist(),
                transition_signed_mean=delta.mean((1, 2, 3)).tolist(),
                channel_mae=np.abs(delta).mean((0, 1, 2)).tolist(),
                changed_channel_fraction=float((delta != 0).mean()),
                changed_rgb_pixel_fraction=float((delta != 0).any(3).mean()),
                mean_pixel_temporal_std_ddof0=float(images.std(0).mean()),
                max_abs_delta=int(np.abs(delta).max()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    pre, post, meta, header = analysis.load_validated_capture(args.capture)
    assert pre.shape == (8, 32, 128, 3), 'this report expects the published ROI geometry'
    roi = np.zeros((32, 64), bool)
    roi[7:-7, 7:-7] = True
    shift = lambda a, k: np.roll(a, (-k, -k), (0, 1))
    states = [spatial.stages(frame, True, 60) for frame in post]
    fields = dict(gray_pair=np.array([denoise.pairs(x) for x in post]),
        gaussian=np.array([shift(s['source'], 1) for s in states]),
        sobel_magnitude=np.array([shift(s['mag'], 2) for s in states]),
        nms_magnitude=np.array([shift(s['detail']['magnitude'], 3) for s in states]))
    field_stats = {}
    for name, values in fields.items():
        values = values[:, roi]
        field_stats[name] = dict(min=int(values.min()), max=int(values.max()),
            percentiles_50_90_95_99_100=np.percentile(values, [50, 90, 95, 99, 100]).tolist(),
            frame_max=values.max(1).tolist())
    historical = {}
    for threshold in (40, 60, 80):
        predictions = [spatial.outputs(frame, threshold) for frame in post]
        historical[threshold] = {}
        for name in predictions[0]:
            masks = np.array([x[name] for x in predictions])
            historical[threshold][name] = dict(
                frame_edge_samples=masks[:, roi].sum(1).tolist(),
                **analysis.metrics(masks, roi))
    fixed = np.array([analysis.apply_gain(x, meta[0, 1:3]) for x in pre])
    gains = meta[:, 1:3].astype(np.int64)
    flags = (meta[:, 7] >> 17) & 31
    stats_valid = (meta[:, 7] >> 16) & 1
    targets = np.clip((meta[:, 4:5].astype(np.uint64) << 16)//meta[:, [3, 5]],
                      0xc000, 0x30000)
    result = dict(input_kind='CRC-validated real camera pre/post AWB RGB888, not Bayer RAW',
        capture_sha256=hashlib.sha256(args.capture.read_bytes()).hexdigest(),
        shape=list(pre.shape), transitions=len(pre)-1, evaluation_internal_samples=int(roi.sum()),
        no_independent_labels=True, motion_response_verified=False,
        pre_rgb=rgb_summary(pre), post_rgb=rgb_summary(post), fields=field_stats,
        awb=dict(gains_q16=gains.tolist(), gains_multiplier=(gains/65536).tolist(),
                 multiplier_peak_to_peak=np.ptp(gains, axis=0).tolist(),
                 multiplier_peak_to_peak_unit='Q16 integer codes; divide by 65536',
                 max_adjacent_gain_delta_q16=np.abs(np.diff(gains, axis=0)).max(0).tolist(),
                 selected_sample_count=meta[:, 6].tolist(), stats_valid=stats_valid.tolist(),
                 stats_sequence=(meta[:, 7] & 65535).tolist(),
                 gain_matches_recorded_clamped_G_R_G_B_target=bool(np.array_equal(gains, targets)),
                 fixed_first_gain_changed_post_elements=int((fixed != post).sum()),
                 fixed_first_gain_max_post_delta=int(np.abs(fixed.astype(int)-post.astype(int)).max()),
                 fixed_first_gain_is_hardware_freeze=False),
        integrity=dict(capture_sofs=meta[:, 0].tolist(), roi_gain_changed=((flags >> 4)&1).tolist(),
            fifo_armed=((flags >> 2)&3).tolist(), fifo_sticky=(flags & 3).tolist(),
            input_beats=meta[:, 10].tolist(), lines=(meta[:, 11] >> 16).tolist(),
            last_line_beats=(meta[:, 11] & 65535).tolist(), bubble_line_error_words=meta[:, 12].tolist(),
            roi_beats=(meta[:, 13] >> 16).tolist(), phase_errors=(meta[:, 13]&65535).tolist(),
            packed_words=meta[:, 14].tolist(), pre_crc=[f'{x:08X}' for x in meta[:, 8]],
            actual_post_crc=[f'{x:08X}' for x in meta[:, 9]],
            unique_pre_crcs=len(set(meta[:, 8].tolist())), unique_post_crcs=len(set(meta[:, 9].tolist())),
            sof_intervals_mipi_cycles=((meta[1:, 15].astype(np.int64)-meta[:-1, 15]) % 2**32).tolist()),
        historical_spatial_models=historical,
        conclusion='transport valid; this low-contrast ROI has no edge samples at TH40/60/80; no temporal algorithm ranking')
    (args.output/'evaluation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    with (args.output/'frame_metadata.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['capture_sof', 'R_Q16', 'B_Q16', 'R_multiplier', 'B_multiplier',
                         'stats_seq', 'selected_samples', 'sum_R', 'sum_G', 'sum_B', 'pre_crc', 'post_crc'])
        for m in meta:
            writer.writerow([int(m[0]), int(m[1]), int(m[2]), m[1]/65536, m[2]/65536,
                int(m[7]&65535), int(m[6]), *map(int, m[3:6]), f'{m[8]:08X}', f'{m[9]:08X}'])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, axes = plt.subplots(4, 2, figsize=(12, 7), layout='constrained')
    for f, axis in enumerate(axes.ravel()):
        axis.imshow(post[f], interpolation='nearest', vmin=0, vmax=255)
        axis.add_patch(Rectangle((13.5, 6.5), 100, 18, fill=False, edgecolor='cyan', linewidth=.7))
        axis.set_title(f'SOF {meta[f, 0]} / actual AWB RGB888', fontsize=10)
        axis.axis('off')
    fig.suptitle('REAL decoded ROI: fixed 0..255 display, no brightness enhancement\nCyan: common valid interior (50 x 18 paired samples)')
    fig.savefig(args.output/'real_roi_contact.png', dpi=140)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), layout='constrained')
    axes[0, 0].plot(meta[1:, 0], np.abs(np.diff(pre.astype(int), axis=0)).mean((1, 2, 3)), 'o-', label='pre AWB')
    axes[0, 0].plot(meta[1:, 0], np.abs(np.diff(post.astype(int), axis=0)).mean((1, 2, 3)), 'o-', label='post AWB')
    axes[0, 0].set(title='Adjacent-frame RGB changes', ylabel='Mean absolute delta / 8-bit codes', ylim=(0, 3.5))
    axes[0, 0].legend()
    for channel, axis, label in [(0, axes[0, 1], 'R'), (1, axes[1, 0], 'B')]:
        axis.plot(meta[:, 0], gains[:, channel]/65536, 'o-')
        axis.set(title=f'Actual {label} AWB gain (small scale range)', ylabel='Multiplier')
        axis.ticklabel_format(style='plain', useOffset=False)
    axes[1, 1].hist(fields['sobel_magnitude'][:, roi].ravel(), bins=np.arange(0, 83, 2), label='Gaussian + Sobel')
    for value, name in [(20, 'low @ TH40'), (40, 'TH40'), (60, 'TH60'), (80, 'TH80')]:
        axes[1, 1].axvline(value, linestyle='--', linewidth=1, label=name)
    axes[1, 1].set(title='Valid-interior gradient distribution (8 frames)', xlabel='L1 magnitude', ylabel='Samples')
    axes[1, 1].legend(fontsize=8)
    fig.suptitle('Validated real data: input variation exists; no eligible contours in this ROI')
    fig.savefig(args.output/'input_awb_gradient.png', dpi=140)
    plt.close(fig)
    print(json.dumps({k: result[k] for k in ('shape', 'evaluation_internal_samples', 'conclusion')}, indent=2))


if __name__ == '__main__':
    main()
