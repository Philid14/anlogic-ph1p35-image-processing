"""Read-only, pinned LATENCY RTL review against TARGET integration requirements.

Extracts only two Git blobs to a NEW output directory. Never switches branches,
edits LATENCY, wires MAIN or certifies CDC physics. Exit 0 means all requirements
pass, 1 means completed functional requirement failures, 2 means invalid evidence.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from run_track_guard_contract import stage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASES = [
    "normal_and_repeat", "resync_statistics_window", "bridge_full_loss",
    "even_error_toggle_alias", "overflow_requires_resync",
    "retired_session_replay", "destination_only_reset", "resync_inflight",
]
EXPECTED_CHECKS = [
    {"normal_complete_first_display", "normal_stats_valid", "repeat_not_new_observation", "repeat_reports_age", "normal_no_alarm"},
    {"prior_window_exists", "resync_count_zero", "resync_sum_zero", "resync_invalid_until_clean_pair", "new_window_one_pair", "new_window_valid"},
    {"offered_twenty_legal_gap_events", "no_source_gap_violation", "first_sixteen_arrive_in_order", "fifo_capacity_observed", "all_events_delivered_or_loss_visible"},
    {"exactly_two_source_drop_toggles", "two_drops_restore_toggle_to_initial_value", "one_accepted_event_survives", "two_dropped_events_are_visible"},
    {"pending_table_overflow_alarm", "overflow_makes_stats_invalid", "clear_alarm_does_not_itself_restore_stats", "overflow_cannot_recover_without_resync", "overflow_window_rejects_new_statistic"},
    {"new_session_pair_accepted", "retired_session_cannot_reopen_from_data"},
    {"one_event_delivered_before_destination_reset", "one_sided_reset_must_not_replay_retired_payload"},
    {"queued_old_events_have_arrived", "table_resync_alone_cannot_certify_epoch_barrier"},
]


def parse_case(output, number, tool_ok):
    marks = re.findall(r"^(?:#\s*)?LATENCY_REVIEW_COMPLETE id=(\d+) checks=(\d+) setup_failures=(\d+) requirement_failures=(\d+)$", output, re.M)
    check_rows = [dict(setup=bool(int(s)), name=n, expected=int(e), actual=int(a), passed=bool(int(p)))
                  for s, n, e, a, p in re.findall(r"^(?:#\s*)?CHECK setup=(\d) name=(\S+) expected=(\d+) actual=(\d+) pass=(\d)$", output, re.M)]
    names = [x["name"] for x in check_rows]
    complete = (len(marks) == 1 and int(marks[0][0]) == number
                and int(marks[0][1]) == len(check_rows)
                and len(names) == len(set(names)) and set(names) == EXPECTED_CHECKS[number]
                and re.findall(r"^(?:#\s*)?CASE id=(\d+)$", output, re.M) == [str(number)])
    setup_failures = int(marks[0][2]) if complete else None
    failures = int(marks[0][3]) if complete else None
    consistent = (complete and all(x["passed"] == (x["actual"] == x["expected"]) for x in check_rows)
                  and setup_failures == sum(not x["passed"] for x in check_rows if x["setup"])
                  and failures == sum(not x["passed"] for x in check_rows if not x["setup"]))
    valid = bool(tool_ok and consistent and setup_failures == 0)
    return dict(name=CASES[number], case_id=number, evidence_valid=valid,
                requirements_satisfied=valid and failures == 0, setup_failures=setup_failures,
                requirement_failures=failures, checks=check_rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--revision", required=True, help="exact 40-character LATENCY commit")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--msim", required=True, type=Path)
    args = ap.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        ap.error("--revision must be an exact lower-case 40-character commit")
    resolved = subprocess.check_output(["git", "rev-parse", "--verify", args.revision + "^{commit}"], cwd=ROOT, text=True).strip()
    if resolved != args.revision:
        raise RuntimeError("--revision must identify a commit, not a tag/tree/blob")
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    snap = args.out / "source-snapshot"
    snap.mkdir()
    sources, manifest = [], []
    for name in ("frame_event_bridge.v", "latency_meter.v"):
        path = "features/latency_view/rtl/" + name
        raw = subprocess.check_output(["git", "show", args.revision + ":" + path], cwd=ROOT)
        blob = subprocess.check_output(["git", "rev-parse", args.revision + ":" + path], cwd=ROOT, text=True).strip()
        computed = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if blob != computed:
            raise RuntimeError("Git blob bytes do not match " + path)
        target = snap / name
        target.write_bytes(raw)
        sources.append(target)
        manifest.append(dict(path=path, git_blob=blob, sha256=hashlib.sha256(raw).hexdigest()))
    tb = HERE / "tb/tb_latency_handoff_review.v"
    (snap / tb.name).write_bytes(tb.read_bytes())
    (snap / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (snap / "run_track_guard_contract.py").write_bytes((HERE / "run_track_guard_contract.py").read_bytes())
    sources.append(snap / tb.name)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in snap.iterdir()}
    env = dict(os.environ)
    env["PATH"] = str(args.msim) + os.pathsep + env.get("PATH", "")
    jobs = []
    for number, name in enumerate(CASES):
        work = args.out / name
        work.mkdir()
        stages, output, tool_ok = [], "", True
        commands = [
            ("vlib", [args.msim / "vlib.exe", "work"]),
            ("vlog", [args.msim / "vlog.exe", "-work", "work", *sources]),
            ("vsim", [args.msim / "vsim.exe", "-c", "-onfinish", "stop",
                      "work.tb_latency_handoff_review", f"-GCASE_ID={number}", "-do",
                      "onerror {quit -code 2}; run -all; quit -f -code 0"]),
        ]
        for label, command in commands:
            result, output = stage(command, work, work / (label + ".log"), 60, env)
            stages.append(result)
            if not result["passed"]:
                tool_ok = False
                break
        row = parse_case(output, number, tool_ok)
        row["stages"] = stages
        jobs.append(row)
        status = "PASS" if row["requirements_satisfied"] else "REQUIREMENT_FAIL" if row["evidence_valid"] else "INVALID_EVIDENCE"
        print(f"{status} {name}: failures={row['requirement_failures']}", flush=True)
    unchanged = before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in snap.iterdir()}
    evidence_valid = unchanged and all(x["evidence_valid"] for x in jobs)
    passed = evidence_valid and all(x["requirements_satisfied"] for x in jobs)
    report = dict(schema=1, created_utc=datetime.now(timezone.utc).isoformat(),
                  target_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  latency_revision=args.revision, latency_sources=manifest,
                  snapshot_sha256=before, source_unchanged=unchanged,
                  scope="Independent integration requirements; no MAIN adapter, physical CDC, P&R, bit or board proof",
                  fixture_clock_period_ns=dict(source=10, destination=14), jobs=jobs,
                  evidence_valid=evidence_valid, requirements_satisfied=passed, integration_ready=False)
    (args.out / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"LATENCY_HANDOFF_REVIEW_COMPLETE cases={len(jobs)} evidence_valid={evidence_valid} requirements_satisfied={passed}")
    return 0 if passed else 1 if evidence_valid else 2


if __name__ == "__main__":
    try:
        result = main()
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        print(f"INVALID_EVIDENCE: {exc}", file=sys.stderr)
        result = 2
    raise SystemExit(result)
