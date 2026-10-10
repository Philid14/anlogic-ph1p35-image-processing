"""Independent spatial reference -> RTL/real DDR packer comparison.

Requires Icarus Verilog. Temporary vectors and executables stay outside the
repository. No writes to the teammate/reference project are performed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import random
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HDL = ROOT / "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source"


def check_frozen():
    manifest = json.loads((ROOT / "tests/edge_v1_frozen_manifest.json").read_text(encoding="utf-8"))
    for kind in ("frozen_main", "read_only_reference"):
        for name, digest in manifest[kind].items():
            actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            if actual != digest:
                raise AssertionError(f"Unexpected modification: {name}")
        print(f"PASS {kind}: {len(manifest[kind])} file hashes unchanged")


def scene(width, height, pattern, seed):
    rng = random.Random(seed)
    image = []
    for y in range(height):
        row = []
        for x in range(width):
            if pattern == "uniform":
                p = (177, 177, 177)
            elif pattern == "vertical":
                p = (255, 255, 255) if x >= width // 2 else (0, 0, 0)
            elif pattern == "horizontal":
                p = (255, 255, 255) if y >= height // 2 else (0, 0, 0)
            elif pattern == "diagonal":
                p = (255, 255, 255) if x * height >= y * width else (0, 0, 0)
            elif pattern == "channels":
                values = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]
                p = values[(x // 7 + y // 3) % 4]
            elif pattern == "threshold":
                # Small gradients exercise equality and both sides of TH=80.
                value = (10 * (x // 2) + y) % 64
                p = (value, value, value)
            else:
                p = tuple(rng.randrange(256) for _ in range(3))
            row.append(p)
        image.append(row)
    return image


def spatial_edges(image, threshold):
    # Construct a 640-sample image independently of pipeline/RTL state.
    samples = []
    for row in image:
        gray = [r // 4 + g // 2 + b // 4 for r, g, b in row]
        samples.append([(gray[x] + gray[x + 1]) // 2 for x in range(0, len(row), 2)])
    result = []
    kx = ((-1, 0, 1), (-2, 0, 2), (-1, 0, 1))
    ky = ((1, 2, 1), (0, 0, 0), (-1, -2, -1))
    for y in range(len(samples)):
        output = []
        for group in range(len(samples[0]) // 2):
            edges = []
            for lane in range(2):
                center_x = 2 * group + lane - 1
                if y < 2 or group == 0:
                    edge = 0
                else:
                    neighborhood = [samples[y - 2 + dy][center_x - 1:center_x + 2] for dy in range(3)]
                    gx = sum(neighborhood[dy][dx] * kx[dy][dx] for dy in range(3) for dx in range(3))
                    gy = sum(neighborhood[dy][dx] * ky[dy][dx] for dy in range(3) for dx in range(3))
                    edge = 255 if abs(gx) + abs(gy) >= threshold else 0
                edges.extend([edge, edge])
            output.extend(edges)
        result.append(output)
    return result


def write_vectors(directory, width, height, threshold, bubbles=False, full=False):
    stimulus = directory / "stim.txt"
    packed = directory / "pack.txt"
    expected_words = 0
    valid_beats = 0
    patterns = ["vertical", "diagonal"] if full else ["uniform", "vertical", "horizontal", "diagonal", "channels", "threshold", "random"]
    with stimulus.open("w", encoding="ascii") as sf, packed.open("w", encoding="ascii") as pf:
        def cycle(v=0, u=0, l=0, rgb=0, expected=0):
            sf.write(f"{v} {u} {l} {rgb:024x} {expected:024x}\n")
        for frame, pattern in enumerate(patterns):
            image = scene(width, height, pattern, frame)
            output = spatial_edges(image, threshold)
            early = frame % 2 == 0
            if early:
                cycle(u=1)
                for _ in range(60):
                    cycle()
            for y in range(height):
                row_bytes = bytearray()
                for x in range(0, width, 4):
                    rgb = int.from_bytes(bytes(c for p in image[y][x:x + 4] for c in p), "big")
                    out = bytes(c for e in output[y][x:x + 4] for c in (e, e, e))
                    cycle(1, int(not early and y == 0 and x == 0), int(x == width - 4), rgb, int.from_bytes(out, "big"))
                    row_bytes.extend(out)
                    valid_beats += 1
                    if bubbles and x % 28 == 0:
                        cycle()
                for off in range(0, len(row_bytes), 16):
                    pf.write(row_bytes[off:off + 16].hex() + "\n")
                    expected_words += 1
                for _ in range(3 + y % 7):
                    cycle()
            for _ in range(12):
                cycle()
        # An incomplete frame then early SOF: must recover without row-count
        # wrap assumptions, or stale line history contributing to first rows.
        if not full:
            cycle(u=1)
            for _ in range(60):
                cycle()
            for _ in range(4):
                cycle(1, rgb=0xFF00FF0000FF00FF00FFFFFF, expected=0)
                valid_beats += 1
            if not bubbles:
                for _ in range(3):
                    pf.write("0" * 32 + "\n")
                    expected_words += 1
            for _ in range(8):
                cycle()
            cycle(u=1)
            for _ in range(60):
                cycle()
            # New uniform full frame proves both memory rows initialize again.
            for y in range(height):
                for x in range(0, width, 4):
                    ex = 0 if y < 2 or x == 0 or threshold > 0 else (1 << 96) - 1
                    cycle(1, 0, int(x == width - 4), 0xA0A0A0A0A0A0A0A0A0A0A0A0, ex)
                    valid_beats += 1
                if not bubbles:
                    for x in range(0, width, 16):
                        row = [0 if y < 2 or p < 4 or threshold > 0 else 255 for p in range(x, x + 16)]
                        out = bytes(c for e in row for c in (e, e, e))
                        for off in range(0, 48, 16):
                            pf.write(out[off:off + 16].hex() + "\n")
                            expected_words += 1
                for _ in range(4):
                    cycle()
    return stimulus, packed, expected_words, valid_beats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Also verify two complete 1280x720 frames")
    args = parser.parse_args()
    check_frozen()
    iv = shutil.which("iverilog") or "C:/iverilog/bin/iverilog.exe"
    vvp = shutil.which("vvp") or "C:/iverilog/bin/vvp.exe"
    cases = [(64, 16, 80, False, False), (64, 16, 0, False, False),
             (64, 16, 81, False, False), (64, 16, 2025, False, False),
             (1280, 16, 80, False, False), (64, 16, 80, True, False)]
    if args.full:
        cases.append((1280, 720, 80, False, True))
    for width, height, threshold, bubbles, full in cases:
        with tempfile.TemporaryDirectory(prefix="edge-v1-") as temp:
            directory = Path(temp)
            stimulus, packed, words, beats = write_vectors(directory, width, height, threshold, bubbles, full)
            exe = directory / "sim.vvp"
            command = [iv, "-g2005", "-Wall", "-s", "tb_edge_v1",
                       f"-Ptb_edge_v1.WIDTH={width}", f"-Ptb_edge_v1.HEIGHT={height}",
                       f"-Ptb_edge_v1.THRESHOLD={threshold}", f"-Ptb_edge_v1.CHECK_PACK={int(not bubbles)}",
                       "-o", str(exe), str(ROOT / "tests/tb_edge_v1.v"),
                       str(HDL / "isp/edge_detect_96.v"), str(HDL / "data_96bit_to_128bit.v"),
                       str(HDL / "isp/isp_top.v"), str(HDL / "isp/data128_96/data128_96.v"),
                       str(ROOT / "tests/isp_boundary_stubs.v")]
            subprocess.run(command, check=True, capture_output=True, text=True)
            run = subprocess.run([vvp, str(exe), f"+STIM={stimulus.as_posix()}",
                                  f"+PACK={packed.as_posix()}", f"+WORDS={words}"],
                                 check=True, capture_output=True, text=True)
            if "FAIL" in run.stdout or "PASS edge_v1" not in run.stdout:
                raise AssertionError(run.stdout + run.stderr)
            if f"valid_beats={beats} " not in run.stdout:
                raise AssertionError(f"Lost beats: expected {beats}, got {run.stdout}")
            print(run.stdout.strip())
    check_frozen()
    print("PASS all edge_v1 RTL/model/packer checks")


if __name__ == "__main__":
    main()
