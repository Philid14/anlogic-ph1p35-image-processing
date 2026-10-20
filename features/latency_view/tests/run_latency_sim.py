#!/usr/bin/env python3
"""Scenario regression for features/latency_view/rtl/latency_meter.v.

Protocol mapping: TEAM_PROTOCOL_V1 sections 2.3 (L1/L2), 4.1 and 4.4.
Truth is computed from the event times the testbench actually drove
("EVT CAP"/"EVT DSP"), never from a model that copies the RTL.

Usage:
    python tests/run_latency_sim.py [--only NAME] [--list]
"""
from __future__ import annotations

import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FEAT = HERE.parent
ROOT = FEAT.parents[1]
RTL = FEAT / "rtl"
OUT = FEAT / ".build"
DEST_PERIOD = 10.0
TICK_PERIOD_CYCLES = 2.5
IVER = None


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


def tool_env(iver):
    env = dict(os.environ)
    extra = [iver.parent]
    lib = iver.parent.parent / "lib"
    if lib.is_dir():
        extra.append(lib)
    env["PATH"] = os.pathsep.join(str(p) for p in extra) + os.pathsep + env.get("PATH", "")
    return env


def vectors(events):
    return "\n".join("%d %s %d %d %d %d" % e for e in events) + "\n0 0 0 0 0 0\n"


def start(t, sid, fid, kind=0):
    return (1, t, sid, fid, kind, 0)


def done(t, sid, fid):
    return (1, t, sid, fid, 2, 0)


def abort(t, sid, fid):
    return (1, t, sid, fid, 1, 0)


def lvl(t, sid, fid, hold):
    return (5, t, sid, fid, 0, hold)


def dsp(t, sid, fid):
    return (2, t, sid, fid, 0, 0)


def clr(t):
    return (3, t, 0, 0, 0, 0)


def resync(t):
    return (4, t, 0, 0, 0, 0)


def pair(sid, fid, t0, t1):
    """start at t0, done at t0+50, display at t1"""
    td = min(t0 + 100, t1 - 40)
    return [start(t0, sid, fid), done(td, sid, fid), dsp(t1, sid, fid)]


SCENARIOS = [
    dict(name="s1_normal", tol=0,
         events=pair(1, 1, 105, 205) + pair(1, 2, 505, 655),
         lat=[(115, 205, 1, 1), (515, 655, 1, 2)],
         alarm=0, stats=(1, 2), cnt=(2, 0, 0, 1), flags=(0, 0, 0),
         counts=(2, 2, 0, 2),
         desc="normal pairing, 10 and 15 cycles, exact"),

    dict(name="s2_skip", tol=0,
         events=([start(105, 1, 1), done(155, 1, 1), start(205, 1, 2), done(255, 1, 2),
                  start(305, 1, 3), done(355, 1, 3), dsp(405, 1, 3)]),
         lat=[(315, 405, 1, 3)],
         alarm=0, stats=(1, 1), cnt=(3, 0, 0, 1), flags=(0, 0, 0),
         counts=(3, 3, 0, 1),
         desc="review repro: A,B,C captured, only C displayed -> C latency"),

    dict(name="s3_abort_skip", tol=0,
         events=[start(105, 1, 1), abort(155, 1, 1), start(205, 1, 2), abort(255, 1, 2),
                 start(305, 1, 3), done(355, 1, 3), dsp(405, 1, 3)],
         lat=[(315, 405, 1, 3)],
         alarm=0, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         counts=(3, 1, 2, 1), lost=(0, 0),
         desc="upstream abort of A and B: only C is matched"),

    dict(name="s4_repeat", tol=0,
         events=pair(1, 1, 105, 205) + [dsp(405, 1, 1)],
         lat=[(115, 205, 1, 1)], age=[(115, 405)], age_key=(1, 1),
         alarm=0, stats=(1, 1), cnt=(1, 0, 1, 1), flags=(0, 0, 1),
         counts=(1, 1, 0, 2),
         desc="repeat display reports image age, never re-enters latency stats"),

    dict(name="s5_unmatched", tol=0,
         events=[dsp(105, 1, 9)] + pair(1, 1, 305, 405),
         lat=[(315, 405, 1, 1)],
         alarm=1, stats=(1, 1), cnt=(1, 1, 0, 1), flags=(0, 0, 0),
         counts=(1, 1, 0, 2),
         desc="display without capture sets alarm bit0, then recovers"),

    dict(name="s6_overflow_recovery", tol=0,
         events=[start(105, 1, 1), start(205, 1, 2), start(305, 1, 3), start(405, 1, 4),
                 start(505, 1, 5), start(605, 1, 6), start(705, 1, 7), start(805, 1, 8),
                 start(905, 1, 9), clr(1005), dsp(1105, 1, 1), resync(1205),
                 start(1305, 1, 1), done(1355, 1, 1), dsp(1405, 1, 1)],
         lat=[(1315, 1405, 1, 1)],
         alarm=1, stats=(1, 1), cnt=(1, 1, 0, 1), flags=(0, 0, 0),
         counts=(10, 1, 0, 2),
         desc="overflow -> invalid; alarm_clr does not restore; resync + clean pair does"),

    dict(name="s7_session_switch", tol=0,
         events=[start(105, 1, 1), done(155, 1, 1), start(305, 2, 1), done(355, 2, 1),
                 dsp(405, 2, 1)],
         lat=[(315, 405, 2, 1)],
         alarm=8, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         counts=(2, 2, 0, 1),
         desc="new session flushes the old one, no cross session match"),

    dict(name="s8_multi_pulse", tol=0,
         events=[lvl(105, 1, 1, 35), done(205, 1, 1), dsp(305, 1, 1)],
         lat=[(115, 305, 1, 1)],
         alarm=0, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         counts=(1, 1, 0, 1),
         desc="a 3.5 cycle high level is exactly ONE start event"),

    dict(name="s9_abort_then_display", tol=0,
         events=[start(105, 1, 1), abort(205, 1, 1), dsp(305, 1, 1)],
         lat=[], alarm=1, stats=(0, 0), cnt=(0, 1, 0, 0), flags=(0, 0, 0),
         counts=(1, 0, 1, 1),
         desc="aborted frame removed: its display is unmatched"),

    dict(name="s10_resync", tol=0,
         events=[start(105, 1, 1), done(155, 1, 1), resync(205), dsp(305, 1, 1)] + pair(1, 2, 405, 505),
         lat=[(415, 505, 1, 2)],
         alarm=1, stats=(1, 1), cnt=(1, 1, 0, 1), flags=(0, 0, 0),
         counts=(2, 2, 0, 2),
         desc="resync flushes, old frame unmatched, next clean pair counted"),

    dict(name="s11_mid_frame", tol=0,
         events=pair(1, 1, 15, 205),
         lat=[(25, 205, 1, 1)],
         alarm=0, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         counts=(1, 1, 0, 1),
         desc="capture starts mid frame, still matched"),

    dict(name="s12_cross_clock", tol=1, cap_half=12.0,
         events=[start(105, 1, 1), done(205, 1, 1), dsp(405, 1, 1)],
         lat=[(115, 405, 1, 1)],
         alarm=0, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         counts=(1, 1, 0, 1),
         desc="24 ns capture clock vs 10 ns display clock, +/-1 cycle"),

    dict(name="s13_incomplete", tol=0,
         events=[start(105, 1, 1), dsp(205, 1, 1)],
         lat=[], alarm=1, stats=(0, 0), cnt=(1, 1, 0, 0), flags=(0, 0, 0),
         counts=(1, 0, 0, 1),
         desc="display before frame complete: no statistic, alarm bit0"),

    dict(name="s14_done_after_display", tol=0,
         events=[start(105, 1, 1), dsp(205, 1, 1), done(305, 1, 1)],
         lat=[], alarm=1, stats=(0, 0), cnt=(1, 1, 0, 0), flags=(0, 0, 0),
         counts=(1, 1, 0, 1), lost=(0, 0),
         desc="frame completed only after being displayed: unmatched"),

    dict(name="s15_fps_window", tol=0, fps_window=35,
         events=[start(105, 1, 1), done(155, 1, 1), start(205, 1, 2), done(255, 1, 2),
                 start(305, 1, 3), done(355, 1, 3), start(405, 1, 4), done(455, 1, 4),
                 start(505, 1, 5), done(555, 1, 5),
                 dsp(605, 1, 1), dsp(705, 1, 2), dsp(805, 1, 3)],
         lat=[(115, 605, 1, 1), (215, 705, 1, 2), (315, 805, 1, 3)],
         alarm=0, stats=(1, 3), cnt=(5, 0, 0, 1), flags=(0, 0, 0),
         counts=(5, 5, 0, 3), fps=(5, 3, 1),
         desc="L1: capture and display counts per window, no divider"),

    dict(name="s16_abort_unknown", tol=0,
         events=[abort(105, 1, 9)],
         lat=[], alarm=8, stats=(0, 0), cnt=(0, 0, 0, 0), flags=(0, 0, 0),
         counts=(0, 0, 1, 0), lost=(0, 1),
         desc="abort for a frame that was never captured sets alarm bit3"),

    dict(name="s17_recapture", tol=0,
         events=[start(105, 1, 1), start(205, 1, 1), done(255, 1, 1), dsp(355, 1, 1)],
         lat=[(215, 355, 1, 1)],
         alarm=2, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         counts=(2, 1, 0, 1),
         desc="same key captured twice: record replaced, alarm bit1"),

    dict(name="s20_resync_stats_reset", tol=0, sum_check=False,
         events=[start(105, 1, 1), done(155, 1, 1), dsp(205, 1, 1),
                 dsp(305, 1, 9), resync(405),
                 start(505, 1, 1), done(555, 1, 1), dsp(605, 1, 1)],
         lat=[(115, 205, 1, 1), (515, 605, 1, 1)],
         alarm=1, stats=(1, 1), cnt=(1, 1, 0, 1), flags=(0, 0, 0),
         counts=(2, 2, 0, 3), stats_sum=10,
         desc="resync restarts the statistic window (count/sum cleared)"),

    dict(name="s19_too_fast_alarm_clr", tol=0, min_gap_src=3,
         events=[start(105, 1, 1), start(112, 1, 2), done(205, 1, 1),
                 clr(405), start(505, 1, 2), done(605, 1, 2), dsp(655, 1, 2)],
         lat=[(515, 655, 1, 2)],
         alarm=0, stats=(1, 1), cnt=(2, 0, 0, 1), flags=(0, 0, 0),
         counts=(2, 2, 0, 1),
         desc="too-close start is dropped and alarm bit2 can be cleared by alarm_clr"),

    dict(name="s18_fid_wrap", tol=0,
         events=[start(105, 1, 10), done(155, 1, 10), start(305, 1, 1), done(355, 1, 1),
                 dsp(405, 1, 1)],
         lat=[(315, 405, 1, 1)],
         alarm=8, stats=(1, 1), cnt=(1, 0, 0, 1), flags=(0, 0, 0),
         counts=(2, 2, 0, 1),
         desc="frame id wrap without a new session: flush + alarm bit3"),
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
        for tag, key in (("ALARM", "alarm"), ("STATS", "stats"), ("CNT", "cnt"), ("FLAGS", "flags"),
                         ("COUNTS", "counts"), ("FPS", "fps"), ("LOST", "lost")):
            m = re.match(r"^%s ([0-9 ]+)$" % tag, line)
            if m:
                out[key] = [int(x) for x in m.group(1).split()]
        m = re.match(r"^TB_ERRORS=(\d+)", line)
        if m:
            out["tb_errors"] = int(m.group(1))
    return out


def nearest(records, t, sid, fid, kind=None):
    best = None
    for r in records:
        if r["sid"] != sid or r["fid"] != fid:
            continue
        if kind is not None and r.get("kind") != kind:
            continue
        if best is None or abs(r["t"] - t) < abs(best["t"] - t):
            best = r
    return best


def check(case, rec):
    fails = []
    if rec.get("tb_errors") != 0:
        fails.append("testbench errors=%s" % rec.get("tb_errors"))
    tol = case.get("tol", 0)
    if len(rec["lat"]) != len(case.get("lat", [])):
        fails.append("LAT pulses=%d expected=%d" % (len(rec["lat"]), len(case.get("lat", []))))
    for i, (cap_t, dsp_t, sid, fid) in enumerate(case.get("lat", [])):
        c = nearest(rec["cap"], cap_t, sid, fid, kind=0)
        d = nearest(rec["dsp"], dsp_t, sid, fid)
        if c is None or d is None:
            fails.append("pair %d: missing recorded event" % i)
            continue
        true_cycles = (d["t"] - c["t"]) / DEST_PERIOD
        if i < len(rec["lat"]):
            if abs(rec["lat"][i]["cycles"] - true_cycles) > tol:
                fails.append("LAT[%d] rtl=%d true=%.1f" % (i, rec["lat"][i]["cycles"], true_cycles))
            if abs(rec["lat"][i]["ticks"] - true_cycles / TICK_PERIOD_CYCLES) > 1 + tol:
                fails.append("ticks[%d] rtl=%d true=%.1f" % (i, rec["lat"][i]["ticks"], true_cycles / TICK_PERIOD_CYCLES))
    for i, (cap_t, dsp_t) in enumerate(case.get("age", [])):
        sid, fid = case.get("age_key", (0, 0))
        c = nearest(rec["cap"], cap_t, sid, fid, kind=0)
        d = nearest(rec["dsp"], dsp_t, sid, fid)
        if c is None or d is None:
            fails.append("AGE %d: missing event" % i)
        elif i < len(rec["age"]) and abs(rec["age"][i]["cycles"] - (d["t"] - c["t"]) / DEST_PERIOD) > tol:
            fails.append("AGE[%d] rtl=%d true=%.1f" % (i, rec["age"][i]["cycles"], (d["t"] - c["t"]) / DEST_PERIOD))
    if rec.get("alarm") is None or rec["alarm"][0] != case["alarm"]:
        fails.append("alarm=%s expected=%d" % (rec.get("alarm"), case["alarm"]))
    for key, labels, expected in (("stats", ("valid", "count"), case["stats"]),
                                  ("cnt", ("entries", "unmatched", "repeat", "lat_seen"), case["cnt"]),
                                  ("flags", ("too_fast", "gap", "age_seen"), case["flags"]),
                                  ("counts", ("cap", "done", "abort", "dsp"), case.get("counts", ())),
                                  ("fps", ("cap_fps", "dsp_fps", "valid"), case.get("fps", ())),
                                  ("lost", ("done_lost", "abort_lost"), case.get("lost", ()))):
        if not expected:
            continue
        got = rec.get(key)
        if got is None:
            fails.append("missing %s" % key.upper())
            continue
        for i, label in enumerate(labels):
            if got[i] != expected[i]:
                fails.append("%s.%s=%d expected=%d" % (key, label, got[i], expected[i]))
    if rec.get("stats") and case.get("stats_sum") is not None:
        if rec["stats"][2] != case["stats_sum"]:
            fails.append("stat_sum=%d expected=%d" % (rec["stats"][2], case["stats_sum"]))
    elif rec.get("stats") and case.get("lat") and case.get("sum_check", True):
        if abs(rec["stats"][2] - sum(x["cycles"] for x in rec["lat"])) > 0:
            fails.append("stat_sum=%d != sum(LAT)" % rec["stats"][2])
    return fails


def run_case(case, iver):
    name = case["name"]
    vec = OUT / (name + ".vec")
    vec.write_text(vectors(case["events"]), encoding="utf-8", newline="\n")
    exe = OUT / (name + ".vvp")
    cmd = [str(iver), "-g2012", "-s", "tb_latency_meter", "-o", str(exe),
           "-Ptb_latency_meter.TB_SAME_CLOCK=%d" % (1 if case.get("same_clock", True) else 0),
           "-Ptb_latency_meter.TB_DEST_HALF=5.0",
           "-Ptb_latency_meter.TB_CAP_HALF=%s" % case.get("cap_half", 5.0),
           "-Ptb_latency_meter.TB_FPS_WINDOW=%d" % case.get("fps_window", 100000),
           "-Ptb_latency_meter.TB_MIN_GAP_SRC=%d" % case.get("min_gap_src", 2),
           str(HERE / "tb_latency_meter.v"), str(RTL / "latency_meter.v"),
           str(RTL / "frame_event_bridge.v")]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for c in SCENARIOS:
            print("%-26s %s" % (c["name"], c["desc"]))
        return 0
    global IVER
    IVER = find_iverilog()
    OUT.mkdir(parents=True, exist_ok=True)
    cases = SCENARIOS
    if a.only:
        want = set(a.only)
        cases = [c for c in cases if c["name"] in want]
        if not cases:
            raise SystemExit("no such scenario")
    results, failed = [], 0
    print("iverilog: %s" % IVER)
    for case in cases:
        rec, fails = run_case(case, IVER)
        status = "PASS" if not fails else "FAIL"
        failed += 1 if fails else 0
        print("[%s] %-26s %s" % (status, case["name"], case["desc"]))
        for f in fails:
            print("       - %s" % f)
        if fails:
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
