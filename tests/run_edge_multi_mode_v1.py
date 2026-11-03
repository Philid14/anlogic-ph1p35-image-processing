"""EDGE_MULTI_MODE_V1 simulation: pixel math, keys/CDC, stream and packing.

The physical MIPI/PHY, DDR controller and HDMI transmitter remain outside
this simulation. Exact 96-bit stream and 128-bit packer comparisons cover the
production ISP integration boundary.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import tempfile

import numpy as np
import run_edge_control_v1 as control
import run_edge_temporal_v1 as temporal

ROOT = control.ROOT
HDL = control.HDL
OUT = ROOT / "tmp/edge_multi_mode_v1"
RESET_CONFIG = (3 << 16) | (80 << 8) | 130


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_bytes(commit, rel):
    return subprocess.check_output(["git", "show", f"{commit}:{rel}"], cwd=ROOT)


def compatibility_hashes():
    # These paths define sensor/ISP, the frozen Edge algorithm, DDR/HDMI,
    # Logo/CNT, pins and timing. They must remain byte-identical to V1.
    unchanged = [
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/awb.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/video_in.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/video_out.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/data_96bit_to_128bit.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/osd_char_lib.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/hdmi_mixer.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/anlogic_logo_rom.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/edge_detect_96.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/gaussian_pair_3x3.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/nms_gradient_pair_3x3.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/edge_link_pair_3x3.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/edge_center_pair_delay.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/edge_temporal_hold.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/fifo_event_counter.v",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/constraints_source/pin.adc",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.sdc",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/ip_source/PLL/PLL.xml",
        "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/ph1p35_ddr/ddr2/ddr2.xml",
    ]
    tag = "edge-temporal-v1-candidate"
    for rel in unchanged:
        current = (ROOT / rel).read_bytes().replace(b"\r\n", b"\n")
        baseline = tracked_bytes(tag, rel).replace(b"\r\n", b"\n")
        assert current == baseline, rel
    print(f"PASS compatibility hashes: {len(unchanged)} V1 algorithm/ISP/DDR/HDMI/pin/sdc paths unchanged", flush=True)
    return {rel: sha(ROOT / rel) for rel in unchanged}


def luma(rgb):
    r, g, b = (int(x) for x in rgb)
    return (77 * r + 150 * g + 29 * b + 128) >> 8


def rgb_vectors(path):
    rng = np.random.default_rng(20261018)
    special = [
        (0, 0, 0), (255, 255, 255), (1, 1, 1), (127, 127, 127),
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
        (0, 255, 255), (255, 0, 255), (10, 20, 30), (250, 240, 230),
    ]
    beats = []
    for threshold in (10, 29, 77, 130, 150, 250):
        for i in range(0, len(special), 4):
            pixels = (special + special)[i:i + 4]
            beats.append((pixels, threshold))
    # Every neutral code, including binary equality at that threshold.
    for value in range(256):
        pixels = [(value, value, value)] * 4
        beats.append((pixels, value if value >= 10 else 10))
    for _ in range(2048):
        pixels = [tuple(int(x) for x in p) for p in rng.integers(0, 256, (4, 3))]
        threshold = int(10 + 10 * rng.integers(0, 25))
        beats.append((pixels, threshold))
    with path.open("w", encoding="ascii") as f:
        for pixels, threshold in beats:
            rgb = int.from_bytes(bytes(c for p in pixels for c in p), "big")
            gray_pixels = []
            binary_pixels = []
            for p in pixels:
                y = luma(p)
                gray_pixels.append((y, y, y))
                binary_pixels.append((255, 255, 255) if y >= threshold else (0, 0, 0))
            gray = int.from_bytes(bytes(c for p in gray_pixels for c in p), "big")
            binary = int.from_bytes(bytes(c for p in binary_pixels for c in p), "big")
            f.write(f"{rgb:024x} {gray:024x} {binary:024x} {threshold}\n")
    return len(beats), len(beats) * 4


def mode_text(mode):
    return {
        0: "MODE: ORIGIN  ",
        1: "MODE: GRAY    ",
        2: "MODE: BINARY  ",
        3: "MODE: EDGE    ",
    }[mode]


def overlay_pixels(pixels, x, y, mode, edge_threshold, binary_threshold, font,
                   fifo_counts=0x1234ABCD):
    threshold_text = (f"THRESHOLD: {binary_threshold:03d}" if mode == 2 else
                      f"THRESHOLD: {edge_threshold:03d}" if mode == 3 else
                      "THRESHOLD:    ")
    fifo_text = f"B:{fifo_counts >> 16:04X} S:{fifo_counts & 0xffff:04X} "
    out = []
    for lane, rgb in enumerate(pixels):
        px = x + lane
        if 800 <= px < 1248 and ((16 <= y < 88) or (96 <= y < 128)):
            local_x = px - 800
            local_y = y - 16
            row = None
            text = " " * 14
            if local_y < 32:
                text = mode_text(mode)
                row = local_y // 2
            elif 40 <= local_y < 72:
                text = threshold_text
                row = (local_y - 40) // 2
            elif local_y >= 80:
                text = fifo_text
                row = (local_y - 80) // 2
            char_col, offset = divmod(local_x, 32)
            bits = font.get(ord(text[char_col]), {}).get(row, 0)
            rgb = (255, 255, 0) if bits & (1 << (15 - offset // 2)) else (16, 16, 16)
        out.append(rgb)
    return bytes(c for p in out for c in p)


def frame_rgb(width, height, frame_index, rng):
    yy, xx = np.indices((height, width))
    rgb = np.empty((height, width, 3), dtype=np.uint8)
    rgb[:, :, 0] = ((xx * 3 + yy * 5 + frame_index * 31) % 256)
    rgb[:, :, 1] = ((xx * 7 + yy * 2 + frame_index * 47) % 256)
    rgb[:, :, 2] = ((xx + yy * 11 + frame_index * 19) % 256)
    # Add hard edges, neutral patches and saturated primaries.
    rgb[height // 4:height // 2, width // 5:width // 2] = (255, 255, 255)
    rgb[height // 2:3 * height // 4, width // 3:2 * width // 3] = (0, 0, 0)
    rgb[height // 5:height // 3, 2 * width // 3:4 * width // 5] = (255, 32, 16)
    rgb[2 * height // 3:4 * height // 5, width // 6:width // 3] = (16, 255, 32)
    noise = rng.integers(-2, 3, rgb.shape, dtype=np.int16)
    return np.clip(rgb.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def expected_edge(rgb, threshold, previous_raw, previous_threshold):
    raw, support = temporal.causal_fields(rgb, threshold)
    active = raw.copy()
    if previous_raw is not None and previous_threshold == threshold:
        active |= previous_raw & support
    return active, raw


def pack_model(valid, data):
    count = 0
    previous = 0
    words = []
    mask64 = (1 << 64) - 1
    mask32 = (1 << 32) - 1
    for is_valid, current in zip(valid, data):
        if not is_valid:
            count = 0
            continue
        if count == 1:
            words.append(((previous << 32) | (current >> 64)) & ((1 << 128) - 1))
        elif count == 2:
            words.append(((previous & mask64) << 64) | (current >> 32))
        elif count == 3:
            words.append(((previous & mask32) << 96) | current)
        previous = current
        count = (count + 1) & 3
    return words


def stream_vectors(directory, width, height, full=False):
    rng = np.random.default_rng(818)
    if full:
        frames = [
            (2, 60, 130, False),
            (3, 60, 130, True),
        ]
    else:
        frames = [
            (3, 80, 130, True),
            (0, 80, 130, False),
            (1, 60, 130, True),
            (2, 60, 130, False),
            (3, 60, 150, True),
            (2, 50, 130, False),
            (1, 50, 130, True),
            (0, 50, 130, False),
            (3, 50, 130, True),
        ]
    font = control.glyph_table()
    stimulus = directory / "stim.txt"
    packed = directory / "pack.txt"
    valid_sequence = []
    data_sequence = []
    previous_raw = None
    previous_threshold = None
    requested = RESET_CONFIG
    beats = 0

    with stimulus.open("w", encoding="ascii") as sf:
        def cycle(is_valid=0, user=0, last=0, request=None, data=0, expected=b"\0" * 12):
            nonlocal requested
            if request is not None:
                requested = request
            sf.write(f"{is_valid} {user} {last} {requested:05x} {data:024x} {expected.hex()}\n")
            valid_sequence.append(is_valid)
            data_sequence.append(int.from_bytes(expected, "big") if is_valid else 0)

        for frame_index, (mode, edge_threshold, binary_threshold, early) in enumerate(frames):
            rgb = frame_rgb(width, height, frame_index, rng)
            active, raw = expected_edge(rgb, edge_threshold, previous_raw, previous_threshold)
            edge_rgb = np.repeat(active.astype(np.uint8) * 255, 2, axis=1)
            cfg = (mode << 16) | (edge_threshold << 8) | binary_threshold
            requested = cfg
            if early:
                cycle(user=1)
                for _ in range(12):
                    cycle()
            for y in range(height):
                for x in range(0, width, 4):
                    user = 1 if (not early and y == 0 and x == 0) else 0
                    if mode == 0:
                        pixels = [tuple(int(c) for c in rgb[y, x + lane]) for lane in range(4)]
                    elif mode == 1:
                        pixels = []
                        for lane in range(4):
                            value = luma(rgb[y, x + lane])
                            pixels.append((value, value, value))
                    elif mode == 2:
                        pixels = []
                        for lane in range(4):
                            value = luma(rgb[y, x + lane])
                            pixels.append((255, 255, 255) if value >= binary_threshold else (0, 0, 0))
                    else:
                        pixels = [(int(edge_rgb[y, x + lane]),) * 3 for lane in range(4)]
                    expected = overlay_pixels(
                        pixels, x, y, mode, edge_threshold, binary_threshold, font)
                    group = x // 4
                    last = int(x == width - 4)
                    data = int.from_bytes(bytes(c for p in rgb[y, x:x + 4] for c in p), "big")
                    cycle(1, user, last, requested, data, expected)
                    beats += 1
                    if x > 0 and group % 19 == 7:
                        requested = (int(rng.integers(0, 4)) << 16) | \
                                    (10 + 10 * int(rng.integers(0, 25))) << 8 | \
                                    (10 + 10 * int(rng.integers(0, 25)))
                    if not full and group % 23 == 9:
                        cycle()
                for _ in range(1 + (y % 3 if not full else 1)):
                    cycle()
            previous_raw = raw
            previous_threshold = edge_threshold
        for _ in range(40):
            cycle()

    words = pack_model(valid_sequence, data_sequence)
    with packed.open("w", encoding="ascii") as pf:
        for word in words:
            pf.write(f"{word:032x}\n")
    return stimulus, packed, len(words), beats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    hashes = compatibility_hashes()

    rgb_path = OUT / "rgb_vectors.txt"
    rgb_beats, rgb_pixels = rgb_vectors(rgb_path)
    control.simulate(
        OUT, "tb_edge_multi_mode_rgb",
        [ROOT / "tests/tb_edge_multi_mode_rgb.v", HDL / "isp/rgb_effects_96.v"],
        plus=[f"+STIM={rgb_path.as_posix()}"],
    )
    print(f"PASS RGB model: {rgb_beats} beats / {rgb_pixels} pixels", flush=True)

    key_sources = [
        ROOT / "tests/tb_edge_multi_mode_keys.v",
        HDL / "edge_key_control.v",
        HDL / "edge_config_cdc.v",
    ]
    control.simulate(OUT, "tb_edge_multi_mode_keys", key_sources)
    control.simulate(OUT, "tb_edge_multi_mode_mailbox", key_sources)

    cases = [(64, 32, False)]
    if args.full:
        cases.append((1280, 720, True))
    results = []
    for width, height, full in cases:
        with tempfile.TemporaryDirectory(prefix="edge-multi-stream-") as temporary:
            directory = Path(temporary)
            stimulus, packed, words, beats = stream_vectors(directory, width, height, full)
            sources = [
                ROOT / "tests/tb_edge_multi_mode_stream.v",
                HDL / "isp/edge_control_stream.v",
                HDL / "isp/rgb_effects_96.v",
                HDL / "isp/edge_detect_96.v",
                HDL / "isp/gaussian_pair_3x3.v",
                HDL / "isp/nms_gradient_pair_3x3.v",
                HDL / "isp/edge_link_pair_3x3.v",
                HDL / "isp/edge_center_pair_delay.v",
                HDL / "isp/edge_temporal_hold.v",
                HDL / "edge_status_osd.v",
                HDL / "osd_char_lib.v",
                HDL / "data_96bit_to_128bit.v",
                HDL / "isp/isp_top.v",
                HDL / "isp/data128_96/data128_96.v",
                ROOT / "tests/isp_boundary_stubs.v",
            ]
            log = control.simulate(
                OUT, "tb_edge_multi_mode_stream", sources,
                [f"-Ptb_edge_multi_mode_stream.WIDTH={width}",
                 f"-Ptb_edge_multi_mode_stream.HEIGHT={height}"],
                [f"+STIM={stimulus.as_posix()}", f"+PACK={packed.as_posix()}",
                 f"+WORDS={words}"],
            )
            assert f"valid_beats={beats} " in log
            results.append(dict(width=width, height=height, full=full,
                                beats=beats, packed_words=words))
            print(f"PASS multi-mode stream {width}x{height}: {beats} beats, {words} words", flush=True)

    result = dict(compatibility_hashes=hashes, rgb_beats=rgb_beats,
                  rgb_pixels=rgb_pixels, streams=results)
    (OUT / "rtl_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS EDGE_MULTI_MODE_V1 RTL regression; physical board/IP validation pending", flush=True)


if __name__ == "__main__":
    main()
