"""Independent synthetic ablation of candidate TARGET research directions.

This is a CPU set-based oracle, not RTL or a throughput/resource measurement.
It uses binary strong/weak masks to isolate localization from color conversion.
Warm cases supply a fixed previous box to both association-aware candidates;
cold ambiguous cases are reported separately, never hidden in an overall mean.
No external source code or packages are used.
"""

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

W, H, MIN_COUNT = 160, 120, 64
OFFSETS = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]


def rect(x, y, w, h):
    return {(xx, yy) for yy in range(y, y + h) for xx in range(x, x + w)}


def bbox(mask):
    if not mask:
        return None
    return (min(x for x, y in mask), min(y for x, y in mask),
            max(x for x, y in mask), max(y for x, y in mask))


def area(box):
    return 0 if box is None else (box[2] - box[0] + 1) * (box[3] - box[1] + 1)


def center(box):
    return ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2)


def iou(a, b):
    if a is None or b is None:
        return float(a == b)
    overlap = max(0, min(a[2], b[2]) - max(a[0], b[0]) + 1) * \
        max(0, min(a[3], b[3]) - max(a[1], b[1]) + 1)
    return overlap / (area(a) + area(b) - overlap)


def dilate(mask):
    return {(x + dx, y + dy) for x, y in mask for dx, dy in OFFSETS
            if 0 <= x + dx < W and 0 <= y + dy < H}


def erode(mask):
    # Out-of-image pixels are zero, explicitly including image borders.
    return {(x, y) for x, y in mask if all((x + dx, y + dy) in mask for dx, dy in OFFSETS)}


def support(mask, minimum=3):
    return {(x, y) for x, y in mask
            if sum((x + dx, y + dy) in mask for dx, dy in OFFSETS) >= minimum}


def majority(mask):
    return {(x, y) for x, y in dilate(mask)
            if sum((x + dx, y + dy) in mask for dx, dy in OFFSETS) >= 5}


def horizontal_runs(mask):
    out = set()
    for x, y in sorted(mask, key=lambda p: (p[1], p[0])):
        if (x - 1, y) in mask:
            continue
        end = x
        while (end + 1, y) in mask:
            end += 1
        if end - x + 1 >= 3:
            out.update((xx, y) for xx in range(x, end + 1))
    return out


def components(mask):
    unseen, out = set(mask), []
    while unseen:
        first = min(unseen)
        unseen.remove(first)
        group, stack = {first}, [first]
        while stack:
            x, y = stack.pop()
            for dx, dy in OFFSETS:
                p = x + dx, y + dy
                if p in unseen:
                    unseen.remove(p)
                    group.add(p)
                    stack.append(p)
        out.append(group)
    return out


def largest(groups):
    groups = [g for g in groups if len(g) >= MIN_COUNT]
    return max(groups, key=lambda g: (len(g), tuple(-x for x in bbox(g)))) if groups else set()


def associated(groups, strong, prior):
    groups = [g for g in groups if len(g) >= MIN_COUNT]
    seeded = [g for g in groups if g & strong]
    if prior is None:
        return largest(seeded)
    px, py = center(prior)

    def distance(g):
        gx, gy = center(bbox(g))
        return abs(gx - px) + abs(gy - py)

    def plausible(g):
        return distance(g) <= 48 and area(prior) <= 4 * area(bbox(g)) \
            and area(bbox(g)) <= 4 * area(prior)

    high = [g for g in seeded if plausible(g)]
    low = [g for g in groups if plausible(g)]
    candidates = high or low  # weak-only continuation needs a supplied prior
    return min(candidates, key=lambda g: (distance(g), -len(g), bbox(g))) if candidates else set()


def tile_groups(mask, size=16, minimum=4):
    cells = defaultdict(set)
    for x, y in mask:
        cells[(x // size, y // size)].add((x, y))
    eligible = {p for p, values in cells.items() if len(values) >= minimum}
    return [set().union(*(cells[p] for p in group)) for group in components(eligible)]


def routes(strong, weak, prior):
    strict_groups = components(strong)
    weak_groups = components(weak)
    high_match = associated(strict_groups, strong, prior)
    return {
        "raw": strong,
        "horizontal_run3": horizontal_runs(strong),
        "support3": support(strong),
        "opening3": dilate(erode(strong)),
        "majority5": majority(strong),
        "largest_component8": largest(strict_groups),
        "seeded_component8": associated(weak_groups, strong, prior),
        "two_stage_component8": high_match or associated(weak_groups, strong, prior),
        "seeded_tile8": associated(tile_groups(weak, size=8), strong, prior),
        "seeded_tile16": associated(tile_groups(weak), strong, prior),
    }


def isolated(rng, forbidden, count=40):
    out = set()
    blocked = dilate(forbidden)
    while len(out) < count:
        point = rng.randrange(W), rng.randrange(H)
        if point not in blocked:
            out.add(point)
            blocked.update(dilate({point}))
    return out


def cases(seed):
    rng = random.Random(seed)
    target = rect(60, 40, 32, 32)
    singles = isolated(rng, target)
    clusters2 = set().union(*(rect(x, y, 2, 2) for x, y in
                             [(8, 8), (140, 8), (10, 100), (140, 100), (120, 60), (24, 65)]))
    clusters3 = set().union(*(rect(x, y, 3, 3) for x, y in
                             [(8, 8), (140, 8), (10, 100), (140, 100),
                              (120, 60), (24, 65), (30, 15), (115, 95)]))
    values = [
        ("clean", "single", target, target, target, None),
        ("isolated40", "single", target | singles, target | singles, target, None),
        ("clusters2", "single", target | clusters2, target | clusters2, target, None),
        ("clusters3", "single", target | clusters3, target | clusters3, target, None),
    ]
    pepper = {p for p in sorted(target) if rng.random() >= 0.20}
    values.append(("pepper20", "single", pepper, pepper, target, None))
    for name, mask in [
        ("thin_vertical", rect(70, 20, 1, 80)),
        ("thin_horizontal", rect(20, 60, 100, 1)),
        ("thin_diagonal", {(20 + k, 20 + k) for k in range(80)}),
        ("small8", rect(61, 43, 8, 8)),
        ("border", rect(0, 0, 32, 32)),
        ("split_target", rect(50, 40, 16, 16) | rect(90, 40, 16, 16)),
    ]:
        values.append((name, "single", mask, mask, mask, None))
    seeds = rect(72, 52, 3, 3)
    prior = bbox(rect(56, 40, 32, 32))
    values.extend([
        ("weak_with_seed", "weak", seeds | singles, target | singles, target, None),
        ("weak_no_seed_warm", "warm", singles, target | singles, target, prior),
        ("larger_distractor_warm", "warm", target | rect(5, 5, 42, 42),
         target | rect(5, 5, 42, 42), target, prior),
        ("larger_distractor_cold", "ambiguous", target | rect(5, 5, 42, 42),
         target | rect(5, 5, 42, 42), target, None),
        ("weak_bridge", "adversarial", target | rect(120, 40, 32, 32),
         target | rect(120, 40, 32, 32) | rect(92, 55, 28, 1), target, prior),
        ("empty", "empty", set(), set(), set(), None),
        ("noise_only_clusters", "empty", clusters3, clusters3, set(), None),
    ])
    # Mirror the bridge probe: a deterministic leftmost tie must not be
    # mistaken for successful target association.
    bridge = next(v for v in values if v[0] == "weak_bridge")
    flip = lambda mask: {(W - 1 - x, y) for x, y in mask}
    values.append(("weak_bridge_mirror", "adversarial", flip(bridge[2]),
                   flip(bridge[3]), flip(bridge[4]), bbox(flip(rect(56, 40, 32, 32)))))
    seedless = ("weak_bridge_seedless_target", "adversarial", rect(120, 40, 32, 32),
                bridge[3], target, prior)
    values.append(seedless)
    values.append(("weak_bridge_seedless_mirror", "adversarial", flip(seedless[2]),
                   flip(seedless[3]), flip(target), bbox(flip(rect(56, 40, 32, 32)))))
    fast_target = rect(105, 80, 32, 32)
    values.append(("fast_weak_jump", "warm", set(), fast_target, fast_target, prior))
    for name, suite, strong, weak, gt, old_box in values:
        assert strong <= weak
        yield dict(name=name, suite=suite, strong=strong, weak=weak, gt=gt, prior=old_box)


def self_check():
    assert bbox(rect(4, 7, 8, 8)) == (4, 7, 11, 14)
    assert len(dilate(erode(rect(4, 4, 3, 3)))) == 9
    assert not erode(rect(4, 4, 2, 2))
    line = rect(20, 20, 1, 4)
    assert not horizontal_runs(line)
    assert support(line) == {(20, 21), (20, 22)}
    assert len(components({(1, 1), (2, 2)})) == 1
    assert iou((0, 0, 3, 3), (2, 0, 5, 3)) == 1 / 3
    assert len(tile_groups(rect(1, 1, 2, 2) | rect(10, 10, 2, 2))) == 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    self_check()
    records = []
    for seed in (11, 23, 47, 89):
        for case in cases(seed):
            gt, prior = case["gt"], case["prior"]
            expected = bbox(gt)
            fingerprint = {k: sorted(case[k]) for k in ("strong", "weak", "gt")}
            fingerprint["prior"] = prior
            digest = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
            for name, selected in routes(case["strong"], case["weak"], prior).items():
                selected = selected if len(selected) >= MIN_COUNT else set()
                actual = bbox(selected)
                err = (abs(center(actual)[0] - center(expected)[0]) +
                       abs(center(actual)[1] - center(expected)[1])) if actual and expected \
                    else 0 if actual == expected else W + H
                records.append(dict(seed=seed, case=case["name"], suite=case["suite"],
                                    method=name, iou=iou(actual, expected),
                                    center_l1=err, recall=len(selected & gt) / len(gt) if gt else 1.0,
                                    false_alarm=int(not gt and bool(actual)), present=int(bool(actual)),
                                    expected_present=int(bool(gt)), input_sha256=digest))
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "mask_route_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    summary = []
    for suite in ("single", "weak", "warm", "ambiguous", "adversarial", "empty"):
        for method in sorted({r["method"] for r in records}):
            subset = [r for r in records if r["suite"] == suite and r["method"] == method]
            errors = sorted(r["center_l1"] for r in subset)
            summary.append(dict(suite=suite, method=method, samples=len(subset),
                                mean_iou=sum(r["iou"] for r in subset) / len(subset),
                                min_iou=min(r["iou"] for r in subset),
                                success_iou90=sum(r["iou"] >= 0.9 for r in subset),
                                mean_recall=sum(r["recall"] for r in subset) / len(subset),
                                center_l1_p95=errors[math.ceil(0.95 * len(errors)) - 1],
                                false_alarms=sum(r["false_alarm"] for r in subset)))
    method_count = len({r["method"] for r in records})
    case_count = len(records) // method_count
    (args.out / "mask_route_summary.json").write_text(json.dumps(dict(
        kind="synthetic_cpu_oracle_not_rtl", baseline="172815e97587c19a63863c27c1c86bc8e85353bd",
        width=W, height=H, minimum_count=MIN_COUNT, seeds=[11, 23, 47, 89],
        case_count=case_count, method_count=method_count, evaluations=len(records),
        border="zero outside image", summary=summary), indent=2), encoding="utf-8")
    print(f"PASS independent self-checks; {case_count} synthetic cases x {method_count} methods = {len(records)} evaluations")
    for suite in ("single", "weak", "warm", "adversarial", "empty"):
        print(suite)
        for entry in [s for s in summary if s["suite"] == suite]:
            print(f"  {entry['method']:22s} meanIoU={entry['mean_iou']:.3f} "
                  f"IoU>=.9={entry['success_iou90']}/{entry['samples']} "
                  f"recall={entry['mean_recall']:.3f} false_alarms={entry['false_alarms']}")


if __name__ == "__main__":
    main()
