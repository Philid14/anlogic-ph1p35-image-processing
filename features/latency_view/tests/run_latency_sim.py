#!/usr/bin/env python3
"""Scenario regression for features/latency_view/rtl/latency_meter.v.

Truth is computed from the event times the testbench actually drove
("EVT CAP"/"EVT DSP" lines), never from a model that copies the RTL. The
reported latency is accepted within a documented tolerance:
  same clock  : exact (0 cycles)
  cross clock : +/-1 display cycle (CDC phase), +/-1 tick

Usage:
    python tests/run_latency_sim.py              # all scenarios
    python tests/run_latency_sim.py --only s2_skip
    python tests/run_latency_sim.py --list
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

HERE = Path(__file__).resolve().parent
FEAT = HERE.parent
ROOT = FEAT.parents[1]
RTL = FEAT / "rtl"
OUT = FEAT / ".build"
IVER = None

DEST_PERIOD = 10.0                 # ns
TICK_PERIOD_CYCLES = 2.5           # TICK_BASE=2, remainder 50000/100000


def find_iverilog():
    cand = []
    env = os.environ.get("IVERILOG_BIN")
    if env:
        cand.append(Path(env))
    cand.append(ROOT / ".tools/iverilog/bin/iverilog.exe")
    which = shutil.which("iverilog")
    if which:
        cand.append(Path(which))
    for c in cand:
        if not c.is_file():
            continue
        # validate: a stale .tools copy without its DLLs fails to execute
        try:
            probe = subprocess.run([str(c), "-V"], capture_output=True, text=True, timeout=20)
        except OSError:
            continue
        if probe.returncode == 0:
            return c
        print("skip unusable iverilog: %s (rc=%d)" % (c, probe.returncode))
    raise SystemExit("iverilog not found (set IVERILOG_BIN)")


def tool_env(iver):
    env = dict(os.environ)
    extra = [iver.parent]
    lib = iver.parent.parent / "lib"
    if lib.is_dir():
        extra.append(lib)
    env["PATH"] = os.pathsep.join(str(p) for p in extra) + os.pathsep + env.get("PATH", "")
    return env


def vectors(events):
    lines = ["%d %s %d %d %d %d" % e for e in events]
    lines.append("0 0 0 0 0 0")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- scenarios
# event tuples: (kind, time_ns, a, b, c, d)
def cap(t, sid, fid, kind=0):
    return (1, t, sid, fid, kind, 0)


def lvl(t, sid, fid, hold, kind=0):
    return (5, t, sid, fid, kind, hold)


def dsp(t, sid, fid):
    return (2, t, sid, fid, 0, 0)


def ev(kind, t):
    return (kind, t, 0, 0, 0, 0)


SCENARIOS = [
    dict(name="s1_normal", same_clock=True,
         events=[cap(105, 1, 1), dsp(205, 1, 1), cap(505, 1, 2), dsp(655, 1, 2)],
         lat=[(115, 205, 1, 1), (515, 655, 1, 2)],
         alarm=0, stats=(1, 2), cnt=(2, 0, 0, 1), flags=(0, 0, 0),
         desc="normal pairing: 10 and 15 cycle latencies, exact"),

    dict(name="s2_skip", same_clock=True,
         events=[cap(105, 1, 1), cap(205, 1, 2), cap(305, 1, 3), dsp(405, 1, 3)],
         lat=[(315, 405, 1, 3)],
         alarm=0, stats=(1, 1), cnt=(3, 0, 0, 1), flags=(0, 0, 0),
         desc="review repro: A,B,C captured, only C displayed -> C latency, not A's"),

    dict(name="s3_abort_skip", same_clock=True,
         events=[cap(105, 1, 1), cap(205, 1, 2), cap(305, 1, 3),
                 cap(405, 1, 1, 1), cap(455, 1, 2, 1), dsp(505, 1, 3)],
         lat=[(315, 505, 1, 3)],
         alarm=0, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         desc="upstream abort of A and B: only C is matched and counted"),

    dict(name="s4_repeat", same_clock=True,
         events=[cap(105, 1, 1), dsp(205, 1, 1), dsp(405, 1, 1)],
         lat=[(115, 205, 1, 1)], age=[(115, 405)], age_key=(1, 1),
         alarm=0, stats=(1, 1), cnt=(1, 0, 1, 1), flags=(0, 0, 1),
         desc="repeat display reports image age, never re-enters latency stats"),

    dict(name="s5_unmatched", same_clock=True,
         events=[dsp(105, 1, 9), cap(305, 1, 1), dsp(405, 1, 1)],
         lat=[(315, 405, 1, 1)],
         alarm=1, stats=(1, 1), cnt=(1, 1, 0, 1), flags=(0, 0, 0),
         desc="display without capture sets alarm bit0 and invalidates stats, then recovers"),

    dict(name="s6_overflow_recovery", same_clock=True,
         events=[cap(105, 1, 1), cap(205, 1, 2), cap(305, 1, 3), cap(405, 1, 4),
                 cap(505, 1, 5), cap(605, 1, 6), cap(705, 1, 7), cap(805, 1, 8),
                 cap(905, 1, 9), ev(3, 1005), ev(4, 1105),
                 cap(1205, 1, 1), dsp(1305, 1, 1)],
         lat=[(1215, 1305, 1, 1)],
         alarm=0, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         desc="table overflow -> invalid; alarm_clr alone does not re-enable stats; resync does"),

    dict(name="s7_session_switch", same_clock=True,
         events=[cap(105, 1, 1), cap(305, 2, 1), dsp(405, 2, 1)],
         lat=[(315, 405, 2, 1)],
         alarm=8, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         desc="new session flushes the old one: no cross-session match, alarm bit3"),

    dict(name="s8_multi_pulse", same_clock=True,
         events=[lvl(105, 1, 1, 35), dsp(305, 1, 1)],
         lat=[(115, 305, 1, 1)],
         alarm=0, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         desc="a 3.5 cycle high level is exactly ONE event (b43284c counted 3)"),

    dict(name="s9_abort_then_display", same_clock=True,
         events=[cap(105, 1, 1), cap(205, 1, 1, 1), dsp(305, 1, 1)],
         lat=[], alarm=1, stats=(0, 0), cnt=(0, 1, 0, 0), flags=(0, 0, 0),
         desc="aborted frame is removed: its display is unmatched, no statistics"),

    dict(name="s10_resync", same_clock=True,
         events=[cap(105, 1, 1), ev(4, 205), dsp(305, 1, 1),
                 cap(405, 1, 2), dsp(505, 1, 2)],
         lat=[(415, 505, 1, 2)],
         alarm=1, stats=(1, 1), cnt=(1, 1, 0, 1), flags=(0, 0, 0),
         desc="resync flushes: the old frame is unmatched, the next clean pair is counted"),

    dict(name="s11_mid_frame", same_clock=True,
         events=[cap(15, 1, 1), dsp(115, 1, 1)],
         lat=[(25, 115, 1, 1)],
         alarm=0, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         desc="capture starts mid frame (no vs dependency), still matched"),

    dict(name="s12_cross_clock", same_clock=False, cap_half=12.0, tol=1,
         events=[cap(105, 1, 1), dsp(305, 1, 1)],
         lat=[(115, 305, 1, 1)],
         alarm=0, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         desc="24 ns capture clock vs 10 ns display clock, +/-1 cycle bound"),
]


def parse(text):
    out = {"cap": [], "dsp": [], "lat": [], "age": []}
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^EVT CAP ([0-9.]+) (\d+) (\d+) (\d+)", line)
        if m:
            out["cap"].append(dict(t=float(m.group(1)), sid=int(m.group(2)), fid=int(m.group(3)),
                                   kind=int(m.group(4))))
            continue
        m = re.match(r"^EVT DSP ([0-9.]+) (\d+) (\d+)", line)
        if m:
            out["dsp"].append(dict(t=float(m.group(1)), sid=int(m.group(2)), fid=int(m.group(3))))
            continue
        m = re.match(r"^LAT (\d+) (\d+) ([0-9.]+)", line)
        if m:
            out["lat"].append(dict(cycles=int(m.group(1)), ticks=int(m.group(2)), t=float(m.group(3))))
            continue
        m = re.match(r"^AGE (\d+) ([0-9.]+)", line)
        if m:
            out["age"].append(dict(cycles=int(m.group(1)), t=float(m.group(2))))
            continue
        for tag, key in (("ALARM", "alarm"), ("STATS", "stats"), ("CNT", "cnt"), ("FLAGS", "flags")):
            m = re.match(r"^%s ([0-9 ]+)$" % tag, line)
            if m:
                out[key] = [int(x) for x in m.group(1).split()]
        m = re.match(r"^TB_ERRORS=(\d+)", line)
        if m:
            out["tb_errors"] = int(m.group(1))
    return out


def nearest(records, t, sid, fid):
    best = None
    for r in records:
        if r["sid"] == sid and r["fid"] == fid:
            if best is None or abs(r["t"] - t) < abs(best["t"] - t):
                best = r
    return best


def run_case(case, iver, exe_dir):
    name = case["name"]
    vec = OUT / (name + ".vec")
    vec.write_text(vectors(case["events"]), encoding="utf-8", newline="\n")
    tb = ROOT / "features/latency_view/tests/tb_latency_meter.v"
    exe = exe_dir / (name + ".vvp")
    cmd = [str(iver), "-g2012", "-s", "tb_latency_meter", "-o", str(exe),
           "-Ptb_latency_meter.TB_SAME_CLOCK=%d" % (1 if case.get("same_clock", True) else 0),
           "-Ptb_latency_meter.TB_DEST_HALF=5.0",
           "-Ptb_latency_meter.TB_CAP_HALF=%s" % case.get("cap_half", 5.0),
           str(tb), str(RTL / "latency_meter.v"), str(RTL / "frame_event_bridge.v")]
    p = subprocess.run(cmd, capture_output=True, text=True, env=tool_env(iver))
    if p.returncode != 0:
        return None, ["compile failed rc=%d: %s" % (p.returncode, (p.stderr or p.stdout)[:400])]
    vvp = iver.parent / ("vvp.exe" if os.name == "nt" else "vvp")
    r = subprocess.run([str(vvp), str(exe), "+VECTORS=" + vec.as_posix()],
                       capture_output=True, text=True, env=tool_env(iver))
    text = r.stdout + r.stderr
    (OUT / (name + ".log")).write_text(text, encoding="utf-8", newline="\n")
    rec = parse(text)
    return rec, check(case, rec)


def check(case, rec):
    fails = []
    if rec.get("tb_errors") != 0:
        fails.append("testbench errors=%s" % rec.get("tb_errors"))
    tol = case.get("tol", 0)
    expect_lat = case.get("lat", [])
    if len(rec["lat"]) != len(expect_lat):
        fails.append("LAT pulses=%d expected=%d" % (len(rec["lat"]), len(expect_lat)))
    for i, (cap_t, dsp_t, sid, fid) in enumerate(expect_lat):
        c = nearest(rec["cap"], cap_t, sid, fid)
        d = nearest(rec["dsp"], dsp_t, sid, fid)
        if c is None or d is None:
            fails.append("pair %d: missing recorded event" % i)
            continue
        true_cycles = (d["t"] - c["t"]) / DEST_PERIOD
        if i >= len(rec["lat"]):
            continue
        got = rec["lat"][i]["cycles"]
        if abs(got - true_cycles) > tol:
            fails.append("LAT[%d] rtl=%d true=%.1f tol=%d" % (i, got, true_cycles, tol))
        exp_ticks = true_cycles / TICK_PERIOD_CYCLES
        if abs(rec["lat"][i]["ticks"] - exp_ticks) > (1 + tol):
            fails.append("ticks[%d] rtl=%d true=%.1f" % (i, rec["lat"][i]["ticks"], exp_ticks))
    for i, (cap_t, dsp_t) in enumerate(case.get("age", [])):
        if i >= len(rec["age"]):
            fails.append("missing AGE pulse %d" % i)
            continue
        sid, fid = case["age_key"]
        c = nearest(rec["cap"], cap_t, sid, fid)
        d = nearest(rec["dsp"], dsp_t, sid, fid)
        if c is None or d is None:
            fails.append("AGE %d: event not recorded" % i)
            continue
        true_age = (d["t"] - c["t"]) / DEST_PERIOD
        if abs(rec["age"][i]["cycles"] - true_age) > tol:
            fails.append("AGE[%d] rtl=%d true=%.1f" % (i, rec["age"][i]["cycles"], true_age))
    if rec.get("alarm") is None or rec["alarm"][0] != case["alarm"]:
        fails.append("alarm=%s expected=%d" % (rec.get("alarm"), case["alarm"]))
    st = case["stats"]
    if rec.get("stats") is None:
        fails.append("missing STATS")
    else:
        if rec["stats"][0] != st[0]:
            fails.append("stats_valid=%d expected=%d" % (rec["stats"][0], st[0]))
        if rec["stats"][1] != st[1]:
            fails.append("stat_count=%d expected=%d" % (rec["stats"][1], st[1]))
        if rec["stats"][2] != sum(x["cycles"] for x in rec["lat"]):
            fails.append("stat_sum=%d != sum(LAT)=%d" % (rec["stats"][2], sum(x["cycles"] for x in rec["lat"])))
    if rec.get("cnt") is None:
        fails.append("missing CNT")
    else:
        for i, label in enumerate(("entries", "unmatched", "repeat", "lat_seen")):
            if rec["cnt"][i] != case["cnt"][i]:
                fails.append("%s=%d expected=%d" % (label, rec["cnt"][i], case["cnt"][i]))
    if rec.get("flags") is None:
        fails.append("missing FLAGS")
    else:
        for i, label in enumerate(("too_fast", "gap_alarm", "age_seen")):
            if rec["flags"][i] != case["flags"][i]:
                fails.append("%s=%d expected=%d" % (label, rec["flags"][i], case["flags"][i]))
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    if a.list:
        for c in SCENARIOS:
            print("%-24s %s" % (c["name"], c["desc"]))
        return 0
    global IVER
    IVER = find_iverilog()
    OUT.mkdir(parents=True, exist_ok=True)
    cases = SCENARIOS
    if a.only:
        want = set(a.only)
        cases = [c for c in cases if c["name"] in want]
        if not cases:
            raise SystemExit("no such scenario: %s" % a.only)
    results, failed = [], 0
    print("iverilog: %s" % IVER)
    for case in cases:
        rec, fails = run_case(case, IVER, OUT)
        status = "PASS" if not fails else "FAIL"
        failed += 1 if fails else 0
        print("[%s] %-24s %s" % (status, case["name"], case["desc"]))
        for f in fails:
            print("       - %s" % f)
        if fails and rec is not None:
            for line in (OUT / (case["name"] + ".log")).read_text(encoding="utf-8").splitlines():
                print("       | %s" % line)
        results.append(dict(name=case["name"], status=status, failures=fails,
                            expected=dict(alarm=case["alarm"], stats=case["stats"], cnt=case["cnt"]),
                            actual=rec))
    (OUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\ncases: %d, failed: %d" % (len(results), failed))
    print("RESULT: %s" % ("PASS" if failed == 0 else "FAIL"))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
