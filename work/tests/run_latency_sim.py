#!/usr/bin/env python3
"""Compile and run the latency measurement / OSD display testbenches.

The RTL under test
    work/rtl/latency/latency_meter.v   time-stamp latency meter
    work/rtl/osd/char_rom.v            generated 95x8 character ROM
    work/rtl/osd/text_overlay.v        streaming text panel
    work/rtl/osd/latency_osd.v         meter + formatter + panel

The reference
    work/models/latency_osd_model.py   integer / bit exact golden model

The script builds the stimulus vectors from the model, runs Icarus Verilog and
fails (non-zero exit) if a testbench reports a mismatch, so it can be used as
the single regression entry point for this deliverable.

Usage
    python work/tests/run_latency_sim.py              # fast cases
    python work/tests/run_latency_sim.py --full       # add the 1280x720 overlay case
    python work/tests/run_latency_sim.py --only meter_same_clock

Environment
    IVERILOG_BIN   path to iverilog.exe, if it is not in .tools/iverilog/bin
                   or on PATH. The tool directory is prepended to PATH for the
                   child processes so the matching vvp/DLLs are always used.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "work/models"))

import latency_osd_model as model  # noqa: E402

RTL_DIR = ROOT / "work/rtl"
TB_DIR = ROOT / "work/tests"
OUT_DIR = ROOT / "work/output/latency-osd"

SOURCES = {
    "latency_meter": RTL_DIR / "latency/latency_meter.v",
    "char_rom": RTL_DIR / "osd/char_rom.v",
    "text_overlay": RTL_DIR / "osd/text_overlay.v",
    "latency_osd": RTL_DIR / "osd/latency_osd.v",
}
INCLUDES = [RTL_DIR / "osd"]

DEFAULT_TICK = (10, 50000, 100000)      # 10.5 cycles per tick, exercises the fraction
DEFAULT_DEPTH = 8


# ---------------------------------------------------------------------------
# tool discovery and execution
# ---------------------------------------------------------------------------

def find_iverilog() -> Path:
    candidates = []
    env = os.environ.get("IVERILOG_BIN")
    if env:
        candidates.append(Path(env))
    candidates.append(ROOT / ".tools/iverilog/bin/iverilog.exe")
    which = shutil.which("iverilog")
    if which:
        candidates.append(Path(which))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SystemExit("iverilog not found: set IVERILOG_BIN or install it under .tools/iverilog")


def tool_env(iverilog: Path) -> dict:
    """PATH with the simulator's own directories first.

    Toolchains such as OSS CAD Suite need their shared libraries on PATH, so
    the directory holding iverilog and its sibling ``lib`` directory (when
    present) are prepended for the child processes.
    """
    env = dict(os.environ)
    extra = [iverilog.parent]
    sibling_lib = iverilog.parent.parent / "lib"
    if sibling_lib.is_dir():
        extra.append(sibling_lib)
    env["PATH"] = os.pathsep.join(str(p) for p in extra) + os.pathsep + env.get("PATH", "")
    return env


def compile_tb(iverilog: Path, top: str, sources: list[Path], params: dict,
               out_vvp: Path, include: list[Path]) -> None:
    cmd = [str(iverilog), "-g2012", "-s", top, "-o", str(out_vvp)]
    for path in include:
        cmd.append("-I" + str(path))
    for key, value in params.items():
        cmd.append("-P%s.%s=%s" % (top, key, value))
    cmd += [str(p) for p in sources]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=tool_env(iverilog))
    if proc.returncode != 0:
        raise SystemExit("iverilog failed for %s (rc=%d)\n%s%s"
                         % (top, proc.returncode, proc.stdout, proc.stderr))


def run_vvp(iverilog: Path, exe: Path, plusargs: list[str]) -> str:
    vvp = iverilog.parent / ("vvp.exe" if os.name == "nt" else "vvp")
    cmd = [str(vvp), str(exe)] + plusargs
    proc = subprocess.run(cmd, capture_output=True, text=True, env=tool_env(iverilog))
    return proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# vector builders
# ---------------------------------------------------------------------------

def meter_vectors(same_clock: bool, dest_half: float, src_half: float, tick: tuple,
                  src_first: int, src_period: int, out_cycles: list[int],
                  depth: int = DEFAULT_DEPTH) -> tuple[str, dict]:
    base, rem, mod = tick
    last = max(out_cycles)
    # The vector list ends with two error checks at last + 10 and last + 12 and
    # the testbench consumes one more cycle while clearing the flags, so the
    # design is simulated up to cycle last + 13. Everything after that must be
    # excluded, otherwise the model would keep generating source events that the
    # testbench never applies.
    end_cycle = last + 13
    src_cycles = list(range(src_first, end_cycle + 1, src_period))
    results, ovf, unf, sim_info = model.simulate_meter(
        dest_half, src_half, src_cycles, out_cycles, base, rem, mod, depth,
        end_cycle=end_cycle)
    if same_clock:
        # cross check the closed form helper against the edge level model: with
        # a single clock the time stamp is exactly SYNC_CYCLES after the token
        for _, stamp in sim_info["pushes"]:
            token_cycle = stamp - model.SYNC_CYCLES
            expected, _ = model.measured_latency(token_cycle, token_cycle + model.SYNC_CYCLES,
                                                 base, rem, mod)
            assert expected == 0, (stamp, token_cycle)

    lines = []
    last_values = (0, 0, 0)
    for out_cycle in sorted(out_cycles):
        result = results[out_cycle]
        if result is None:
            expected = last_values
        else:
            expected = (result[0], result[1], 1)
            last_values = expected
        lines.append("1 %d %d %d %d" % (out_cycle, expected[0], expected[1], expected[2]))
    err_cycle = last + 10   # must match end_cycle above
    lines.append("2 %d %d %d 0" % (err_cycle, int(ovf), int(unf)))
    lines.append("2 %d 0 0 0" % (err_cycle + 2))
    lines.append("0 0 0 0 0")
    info = {
        "source_tokens": len(src_cycles),
        "pushes": sim_info["pushes"],
        "stamps": [stamp for _, stamp in sim_info["pushes"]],
        "expected_err_overflow": int(ovf),
        "expected_err_underflow": int(unf),
        "measurements": len(out_cycles),
    }
    return "\n".join(lines) + "\n", info


def blend_pixel(x: int, y: int, char_buf: str, cols: int, rows: int, x0: int, y0: int,
                scale_log2: int, fg: int, bg: int, bg_dim: bool, panel_en: bool) -> int:
    """Model of the text_overlay output for one pixel of the synthetic pattern."""
    rgb = ((x & 0xFF) << 16) | ((y & 0xFF) << 8) | ((x + y) & 0xFF)
    mask = model.overlay_mask(x, y, char_buf, x0, y0, scale_log2, cols, rows)
    if mask is None or not panel_en:
        return rgb
    if mask:
        return fg
    return model.dim_rgb(rgb) if bg_dim else bg


def overlay_expected(h: int, v: int, frames: int, char_buf: str, cols: int, rows: int,
                     x0: int, y0: int, scale_log2: int, fg: int, bg: int,
                     bg_dim: bool, panel_en: bool = True) -> tuple[int, list[int]]:
    hash_value = model.output_hash_init()
    row0 = None
    for _ in range(frames):
        for y in range(v):
            for x in range(h):
                pixel = blend_pixel(x, y, char_buf, cols, rows, x0, y0, scale_log2,
                                    fg, bg, bg_dim, panel_en)
                hash_value = model.output_hash_step(hash_value, pixel)
        if row0 is None:
            row0 = [blend_pixel(x, y0, char_buf, cols, rows, x0, y0, scale_log2,
                                fg, bg, bg_dim, panel_en)
                    for x in range(x0, x0 + cols * model.cell_size(scale_log2))]
    return hash_value, row0 or []


def overlay_vectors(chars: str, expected_hash: int) -> str:
    """Five integers per line, matching the testbench $fscanf format."""
    lines = ["1 " + " ".join(str(ord(c)) for c in chars)]
    lines.append("2 %d %d 0 0" % ((expected_hash >> 16) & 0xFFFF, expected_hash & 0xFFFF))
    lines.append("0 0 0 0 0")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# cases
# ---------------------------------------------------------------------------

def case_meter_same_clock() -> dict:
    tick = DEFAULT_TICK
    out_cycles = [45, 85, 125, 165]
    vectors, info = meter_vectors(True, 5.0, 5.0, tick, 1, 40, out_cycles)
    return {
        "name": "meter_same_clock",
        "top": "tb_latency_meter",
        "sources": [TB_DIR / "tb_latency_meter.v", SOURCES["latency_meter"]],
        "params": {
            "TB_TICK_BASE": tick[0], "TB_TICK_REMAINDER": tick[1], "TB_TICK_MOD": tick[2],
            "TB_SAME_CLOCK": 1, "TB_DEST_HALF": "5.0", "TB_SRC_HALF": "5.0",
            "TB_SRC_FIRST": 1, "TB_SRC_PERIOD": 40,
        },
        "vectors": vectors,
        "info": info,
        "description": "steady state, one pending time stamp, exact tick arithmetic",
    }


def case_meter_queue() -> dict:
    tick = DEFAULT_TICK
    out_cycles = [61, 71, 81]
    vectors, info = meter_vectors(True, 5.0, 5.0, tick, 1, 2, out_cycles)
    return {
        "name": "meter_queue",
        "top": "tb_latency_meter",
        "sources": [TB_DIR / "tb_latency_meter.v", SOURCES["latency_meter"]],
        "params": {
            "TB_TICK_BASE": tick[0], "TB_TICK_REMAINDER": tick[1], "TB_TICK_MOD": tick[2],
            "TB_SAME_CLOCK": 1, "TB_DEST_HALF": "5.0", "TB_SRC_HALF": "5.0",
            "TB_SRC_FIRST": 1, "TB_SRC_PERIOD": 2,
        },
        "vectors": vectors,
        "info": info,
        "description": "source burst: FIFO ordering, depth overflow, sticky flag",
    }


def case_meter_edges() -> dict:
    tick = (10, 0, 100000)     # exactly 10 cycles per tick
    out_cycles = [3, 30, 60]
    vectors, info = meter_vectors(True, 5.0, 5.0, tick, 1, 500, out_cycles)
    return {
        "name": "meter_edges",
        "top": "tb_latency_meter",
        "sources": [TB_DIR / "tb_latency_meter.v", SOURCES["latency_meter"]],
        "params": {
            "TB_TICK_BASE": tick[0], "TB_TICK_REMAINDER": tick[1], "TB_TICK_MOD": tick[2],
            "TB_SAME_CLOCK": 1, "TB_DEST_HALF": "5.0", "TB_SRC_HALF": "5.0",
            "TB_SRC_FIRST": 1, "TB_SRC_PERIOD": 500,
        },
        "vectors": vectors,
        "info": info,
        "description": "empty-queue pop, integer tick period, sticky underflow flag",
    }


def case_meter_cross_clock() -> dict:
    tick = DEFAULT_TICK
    out_cycles = [45, 60, 75, 90]
    vectors, info = meter_vectors(False, 5.0, 12.0, tick, 1, 8, out_cycles)
    return {
        "name": "meter_cross_clock",
        "top": "tb_latency_meter",
        "sources": [TB_DIR / "tb_latency_meter.v", SOURCES["latency_meter"]],
        "params": {
            "TB_TICK_BASE": tick[0], "TB_TICK_REMAINDER": tick[1], "TB_TICK_MOD": tick[2],
            "TB_SAME_CLOCK": 0, "TB_DEST_HALF": "5.0", "TB_SRC_HALF": "12.0",
            "TB_SRC_FIRST": 1, "TB_SRC_PERIOD": 8,
        },
        "vectors": vectors,
        "info": info,
        "description": "24 ns source clock against a 10 ns video clock (toggle CDC)",
    }


def overlay_case(name: str, h: int, v: int, ht: int, vt: int, frames: int,
                 chars: str, cols: int, rows: int, x0: int, y0: int, scale_log2: int,
                 addr_w: int) -> dict:
    char_buf = chars
    assert len(char_buf) >= cols * rows, "the panel needs cols*rows characters"
    expected_hash, row0 = overlay_expected(h, v, frames, char_buf, cols, rows, x0, y0,
                                           scale_log2, 0xFFFFFF, 0x000000, True)
    return {
        "name": name,
        "top": "tb_text_overlay",
        "sources": [TB_DIR / "tb_text_overlay.v", SOURCES["text_overlay"], SOURCES["char_rom"]],
        "params": {
            "TB_H": h, "TB_V": v, "TB_HT": ht, "TB_VT": vt, "TB_FRAMES": frames,
            "TB_COLS": cols, "TB_ROWS": rows, "TB_X0": x0, "TB_Y0": y0,
            "TB_SCALE_LOG2": scale_log2, "TB_ADDR_W": addr_w,
            "TB_PANEL_EN": 1, "TB_BG_DIM": 1,
        },
        "vectors": overlay_vectors(chars, expected_hash),
        "info": {"expected_hash": expected_hash, "expected_row0": row0,
                 "expected_pixels": h * v * frames},
        "description": "%dx%d raster, panel %dx%d at (%d,%d) scale 2^%d, %d frames"
                       % (h, v, cols, rows, x0, y0, scale_log2, frames),
    }


def osd_case(name: str, h: int, v: int, ht: int, vt: int, frames: int,
             back_frame: int, back_pipe: int, tick: tuple, x0: int, y0: int,
             scale_log2: int) -> dict:
    base, rem, mod = tick
    frame_cycles = ht * vt
    vsf = [1 + f * frame_cycles for f in range(1, frames + 1)]     # vs rising edges
    frame_stamps = [t - back_frame + model.SYNC_CYCLES for t in vsf]
    pipe_stamps = [t - back_pipe + model.SYNC_CYCLES for t in vsf]
    edges = model.tick_edges(base, rem, mod, (max(vsf) + base + 4))
    lat_frame_ticks = model.tick_count_at(edges, vsf[-1]) - model.tick_count_at(edges, frame_stamps[-1])
    lat_pipe_ticks = model.tick_count_at(edges, vsf[-1]) - model.tick_count_at(edges, pipe_stamps[-1])
    lat_frame_cycles = vsf[-1] - frame_stamps[-1]
    lat_pipe_cycles = vsf[-1] - pipe_stamps[-1]
    # the frame counter counts vs falling edges, so the last streamed frame is
    # numbered frames + 1; the sticky pairing error of the first frame is
    # cleared by err_clr, so the error nibble reads zero
    buffer = model.char_buffer(lat_frame_ticks, lat_pipe_ticks, frames + 1, 0, True, True)
    # the testbench hashes exactly one frame (the last streamed one), and that
    # frame already shows the final character buffer
    expected_hash, _ = overlay_expected(h, v, 1, buffer, model.OSD_COLS, model.OSD_ROWS,
                                        x0, y0, scale_log2, 0xFFFFFF, 0x000000, True)
    return {
        "name": name,
        "top": "tb_latency_osd",
        "cycle_tolerance": 1,   # see check_osd: stimulus phase, not a design property
        "sources": [TB_DIR / "tb_latency_osd.v", SOURCES["latency_osd"],
                    SOURCES["text_overlay"], SOURCES["char_rom"], SOURCES["latency_meter"]],
        "params": {
            "TB_H": h, "TB_V": v, "TB_HT": ht, "TB_VT": vt, "TB_FRAMES": frames,
            "TB_BACK_FRAME": back_frame, "TB_BACK_PIPE": back_pipe,
            "TB_X0": x0, "TB_Y0": y0, "TB_SCALE_LOG2": scale_log2,
            "TB_TICK_BASE": base, "TB_TICK_REMAINDER": rem, "TB_TICK_MOD": mod,
        },
        "vectors": "0 0 0 0 0\n",
        "info": {
            "expected_lat_frame_ticks": lat_frame_ticks,
            "expected_lat_frame_cycles": lat_frame_cycles,
            "expected_lat_pipe_ticks": lat_pipe_ticks,
            "expected_lat_pipe_cycles": lat_pipe_cycles,
            "expected_buffer": buffer,
            "expected_hash": expected_hash,
        },
        "description": "%dx%d frames=%d, frame lead %d cycles, pipe lead %d cycles"
                       % (h, v, frames, back_frame, back_pipe),
    }


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------

def check_meter(case: dict, output: str) -> list[str]:
    failures = []
    errors = re.search(r"TB_ERRORS=(\d+)", output)
    checks = re.search(r"TB_CHECKS=(\d+)", output)
    if not errors:
        failures.append("no TB_ERRORS reported")
    else:
        if int(errors.group(1)) != 0:
            failures.append("testbench reported %s errors" % errors.group(1))
        if int(checks.group(1)) < 3 * case["info"]["measurements"]:
            failures.append("too few comparisons: %s" % checks.group(1))
    return failures


def check_overlay(case: dict, output: str) -> list[str]:
    failures = []
    pixels = re.search(r"TB_CHECKED_PIXELS=(\d+)", output)
    if not pixels:
        failures.append("no pixel count reported")
    elif int(pixels.group(1)) != case["info"]["expected_pixels"]:
        failures.append("checked pixels %s, expected %d"
                        % (pixels.group(1), case["info"]["expected_pixels"]))
    delay = re.search(r"TB_DELAY_ERRORS=(\d+)", output)
    if not delay or int(delay.group(1)) != 0:
        failures.append("de_out is not de delayed by three cycles: %s"
                        % (delay.group(1) if delay else "missing"))
    got = [int(m.group(1)) for m in re.finditer(r"^PIX \d+ (\d+)$", output, re.M)]
    expected = case["info"]["expected_row0"]
    if len(got) != len(expected):
        failures.append("text row pixels %d, expected %d" % (len(got), len(expected)))
    else:
        for index, (a, b) in enumerate(zip(got, expected)):
            if a != b:
                failures.append("text pixel %d: rtl=%d model=%d" % (index, a, b))
                break
    match = re.search(r"TB_HASH=([0-9a-fA-F]+) EXPECTED=([0-9a-fA-F]+)", output)
    if not match:
        failures.append("no hash reported")
    elif int(match.group(1), 16) != int(match.group(2), 16):
        failures.append("hash rtl=%s expected=%s" % (match.group(1), match.group(2)))
    return failures


def check_osd(case: dict, output: str) -> list[str]:
    failures = []
    info = case["info"]
    # The tick field is the quantity that reaches the screen and is compared
    # exactly. The raw cycle field is compared with a one cycle tolerance: in
    # this integration testbench the source token is driven 1 ns after the
    # clock edge, so the edge that samples it sits one cycle either side of the
    # value the model assumes. tb_latency_meter asserts the cycle field exactly.
    tolerance = case.get("cycle_tolerance", 0)
    pairs = [
        ("lat_frame_ticks", r"^LATF (\d+) \d+$", info["expected_lat_frame_ticks"], 0),
        ("lat_frame_cycles", r"^LATF \d+ (\d+)$", info["expected_lat_frame_cycles"], tolerance),
        ("lat_pipe_ticks", r"^LATP (\d+) \d+$", info["expected_lat_pipe_ticks"], 0),
        ("lat_pipe_cycles", r"^LATP \d+ (\d+)$", info["expected_lat_pipe_cycles"], tolerance),
    ]
    for label, pattern, expected, slack in pairs:
        match = re.search(pattern, output, re.M)
        if not match:
            failures.append("missing %s" % label)
        elif abs(int(match.group(1)) - expected) > slack:
            failures.append("%s rtl=%s model=%d (tolerance %d)"
                            % (label, match.group(1), expected, slack))
    errors = re.search(r"^ERR (\d+)$", output, re.M)
    if not errors or int(errors.group(1)) != 0:
        failures.append("error nibble is not zero: %s" % (errors.group(1) if errors else "missing"))
    chars = [int(m.group(2)) for m in re.finditer(r"^CHAR (\d+) (\d+)$", output, re.M)]
    expected_buffer = info["expected_buffer"]
    if len(chars) != len(expected_buffer):
        failures.append("character dump length %d, expected %d" % (len(chars), len(expected_buffer)))
    else:
        for index, (got, exp) in enumerate(zip(chars, expected_buffer)):
            if got != ord(exp):
                failures.append("overlay RAM[%d]: rtl=%d (%r) model=%d (%r)"
                                % (index, got, chr(got), ord(exp), exp))
                break
    match = re.search(r"^HASH ([0-9a-fA-F]+)$", output, re.M)
    if not match:
        failures.append("no hash reported")
    elif int(match.group(1), 16) != info["expected_hash"]:
        failures.append("hash rtl=%s model=%08x" % (match.group(1), info["expected_hash"]))
    delay = re.search(r"^DELAY_ERRORS (\d+)$", output, re.M)
    if not delay or int(delay.group(1)) != 0:
        failures.append("de_out is not de delayed by three cycles")
    tb_errors = re.search(r"^TB_ERRORS (\d+)$", output, re.M)
    if not tb_errors or int(tb_errors.group(1)) != 0:
        failures.append("testbench reported errors")
    return failures


CHECKERS = {
    "tb_latency_meter": check_meter,
    "tb_text_overlay": check_overlay,
    "tb_latency_osd": check_osd,
}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def all_cases(include_full: bool) -> list[dict]:
    cases = [
        case_meter_same_clock(),
        case_meter_queue(),
        case_meter_edges(),
        case_meter_cross_clock(),
        overlay_case("overlay_small", 128, 64, 148, 74, 2, "1.24", 4, 1, 8, 8, 1, 3),
        osd_case("osd_small", 320, 64, 340, 74, 3, 2000, 200, DEFAULT_TICK, 8, 4, 1),
    ]
    if include_full:
        # full size raster regression: 1280x720 with the same four character
        # panel, so the hash covers one complete 720p frame
        cases.append(overlay_case("overlay_full_720p", 1280, 720, 1650, 750, 1,
                                  "LA1.", 4, 1, 24, 24, 1, 3))
    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="also run the 1280x720 case")
    parser.add_argument("--only", action="append", default=None, help="run one named case")
    parser.add_argument("--keep", action="store_true", help="keep the generated vectors and vvp files")
    args = parser.parse_args()

    iverilog = find_iverilog()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("iverilog: %s" % iverilog)

    cases = all_cases(args.full)
    if args.only:
        wanted = set(args.only)
        cases = [c for c in cases if c["name"] in wanted]
        missing = wanted - {c["name"] for c in cases}
        if missing:
            raise SystemExit("unknown case(s): %s" % ", ".join(sorted(missing)))

    results = []
    failed = 0
    for case in cases:
        top = case["top"]
        vec_path = OUT_DIR / (case["name"] + ".vec")
        vvp_path = OUT_DIR / (case["name"] + ".vvp")
        vec_path.write_text(case["vectors"], encoding="utf-8", newline="\n")
        compile_tb(iverilog, top, case["sources"], case["params"], vvp_path, INCLUDES)
        output = run_vvp(iverilog, vvp_path, ["+VECTORS=" + vec_path.as_posix()])
        (OUT_DIR / (case["name"] + ".log")).write_text(output, encoding="utf-8", newline="\n")
        failures = CHECKERS[top](case, output)

        status = "PASS" if not failures else "FAIL"
        if failures:
            failed += 1
        print("[%s] %-20s %s" % (status, case["name"], case["description"]))
        for line in failures:
            print("       - %s" % line)
        if failures:
            print("       --- testbench output ---")
            for line in output.strip().splitlines():
                print("       | %s" % line)
        results.append({
            "case": case["name"],
            "status": status,
            "description": case["description"],
            "failures": failures,
            "info": case["info"],
            "params": case["params"],
        })
        if not args.keep:
            vvp_path.unlink(missing_ok=True)
            vec_path.unlink(missing_ok=True)

    (OUT_DIR / "results.json").write_text(json.dumps(results, indent=2, default=str),
                                          encoding="utf-8", newline="\n")
    print("")
    print("cases: %d, failed: %d" % (len(results), failed))
    if failed:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
