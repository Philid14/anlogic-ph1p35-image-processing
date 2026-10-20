#!/usr/bin/env python3
"""Panel content test for latency_osd.v (formatting + layout).

The testbench prints the meter values it produced and dumps the 80 character
panel. This script rebuilds the expected panel with model/latency_model.py and
compares all characters, so the OSD and the software model cannot drift.
"""
from __future__ import annotations

import os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FEAT = HERE.parent
ROOT = FEAT.parents[1]
sys.path.insert(0, str(FEAT / "model"))
import latency_model as model  # noqa: E402


def find_iverilog():
    cand = []
    if os.environ.get("IVERILOG_BIN"):
        cand.append(Path(os.environ["IVERILOG_BIN"]))
    cand.append(ROOT / ".tools/iverilog/bin/iverilog.exe")
    if shutil.which("iverilog"):
        cand.append(Path(shutil.which("iverilog")))
    for c in cand:
        if not c.is_file():
            continue
        try:
            if subprocess.run([str(c), "-V"], capture_output=True, timeout=20).returncode == 0:
                return c
        except OSError:
            continue
    raise SystemExit("iverilog not found (set IVERILOG_BIN)")


def run_mode(iver, fault, full=False):
    out = FEAT / ".build"
    out.mkdir(parents=True, exist_ok=True)
    tag = ("full" if full else "small") + "_%d" % fault
    exe = out / ("tb_latency_osd_%s.vvp" % tag)
    srcs = [HERE / "tb_latency_osd.v", FEAT / "rtl/latency_osd.v", FEAT / "rtl/latency_meter.v",
            FEAT / "rtl/frame_event_bridge.v", FEAT / "rtl/text_overlay.v", FEAT / "rtl/char_rom.v"]
    cmd = [str(iver), "-g2012", "-I", str(FEAT / "rtl"), "-s", "tb_latency_osd", "-o", str(exe),
           "-Ptb_latency_osd.TB_FAULT=%d" % fault]
    if full:
        cmd += ["-Ptb_latency_osd.H=1280", "-Ptb_latency_osd.V=720",
                "-Ptb_latency_osd.HT=1650", "-Ptb_latency_osd.VT=750",
                "-Ptb_latency_osd.FRAMES=1"]
    cmd += [str(s) for s in srcs]
    env = dict(os.environ)
    extra = [iver.parent]
    lib = iver.parent.parent / "lib"
    if lib.is_dir():
        extra.append(lib)
    env["PATH"] = os.pathsep.join(str(p) for p in extra) + os.pathsep + env.get("PATH", "")
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if p.returncode:
        print(p.stdout + p.stderr)
        return 1, None
    vvp = iver.parent / ("vvp.exe" if os.name == "nt" else "vvp")
    r = subprocess.run([str(vvp), str(exe)], capture_output=True, text=True, env=env)
    text = r.stdout + r.stderr
    (out / ("tb_latency_osd_%s.log" % tag)).write_text(text, encoding="utf-8", newline="\n")

    m = re.search(r"DBG lat_ticks=(\d+) avg_ticks=(\d+) age_ticks=(\d+) cap=(\d+) dsp=(\d+) alarm=(\d+) "
                  r"stats=(\d+) lat_seen=(\d+) age_seen=(\d+) fps_valid=(\d+) cnt=(\d+) sum_ticks=(\d+)", text)
    if not m:
        print(text)
        print("RESULT: FAIL (no DBG line)")
        return 1, None
    (lat_ticks, avg_ticks, age_ticks, cap, dsp, alarm, stats, lat_seen, age_seen,
     fps_valid, stat_cnt, sum_ticks) = map(int, m.groups())
    fb = re.search(r"FRAME_BCD ([0-9a-fA-F]+)", text)
    frame_bcd = int(fb.group(1), 16) if fb else 0
    frame = sum(((frame_bcd >> (4 * i)) & 0xF) * (10 ** i) for i in range(8))
    chars = [int(v) for v in re.findall(r"^CHAR \d+ (\d+)$", text, re.M)]

    # the panel shows LAT only while the association is trustworthy
    expected = model.char_buffer(lat_ticks, avg_ticks, age_ticks, cap, dsp, frame, stat_cnt, alarm,
                                 lat_valid=bool(lat_seen and stats),
                                 avg_valid=bool(stats and stat_cnt > 0),
                                 age_valid=bool(age_seen), fps_valid=bool(fps_valid))
    fails = []
    if len(chars) != 128:
        fails.append("character dump length %d, expected 128" % len(chars))
    else:
        for i, (got, exp) in enumerate(zip(chars, expected)):
            if got != ord(exp):
                fails.append("panel[%d] rtl=%d(%r) model=%d(%r)" % (i, got, chr(got), ord(exp), exp))
                break
    # the RTL serial divider must match integer division of the recorded sum
    if stat_cnt > 0:
        expected_avg = sum_ticks // stat_cnt
        if avg_ticks != expected_avg:
            fails.append("avg_ticks=%d expected sum/count=%d" % (avg_ticks, expected_avg))
    elif avg_ticks != 0:
        fails.append("avg_ticks=%d expected 0 for empty window" % avg_ticks)

    # fault mode must invalidate the statistics, normal mode must be valid
    expected_stats = 0 if fault else 1
    if stats != expected_stats:
        fails.append("stats_valid=%d expected %d" % (stats, expected_stats))

    print("[%s fault=%d] lat=%d avg=%d age=%d cap=%d dsp=%d frame=%d cnt=%d alarm=%d stats=%d sum_ticks=%d" %
          (tag, fault, lat_ticks, avg_ticks, age_ticks, cap, dsp, frame, stat_cnt, alarm, stats, sum_ticks))
    for row in range(8):
        print("  |%s|" % expected[row * 16:(row + 1) * 16])
    for f in fails:
        print("  FAIL: %s" % f)
    return (0 if not fails else 1), fails


def main():
    iver = find_iverilog()
    rc = 0
    for fault in (0, 1):
        code, fails = run_mode(iver, fault)
        rc = rc or code
    if "--full" in sys.argv:
        code, fails = run_mode(iver, 0, full=True)
        rc = rc or code
    print("RESULT: %s" % ("PASS" if rc == 0 else "FAIL"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
