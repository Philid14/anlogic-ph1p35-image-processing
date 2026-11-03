"""Read-only, pinned LATENCY RTL review against TARGET integration requirements.

Extracts only two Git blobs to a NEW output directory. Never switches branches,
edits LATENCY, wires MAIN or certifies CDC physics. Exit 0 means the SELECTED gate
passes, 1 means valid evidence fails that gate, 2 means invalid evidence. Policy
and MAIN adapter probes are explicitly distinguished from component contracts.
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
    "single_error_toggle_visible",
]
KINDS = ["control", "control", "component_contract", "component_contract",
         "proposed_policy", "main_adapter_dependency", "main_adapter_dependency",
         "main_adapter_dependency", "control"]
# Independent literal gold for {setup flag, expected number}. The simulator
# cannot silently redefine the requirement by printing a different expected=.
CHECK_SPECS = [
    {"normal_complete_first_display": (True, 1), "normal_stats_valid": (False, 1),
     "repeat_not_new_observation": (False, 1), "repeat_reports_age": (False, 1), "normal_no_alarm": (False, 0)},
    {"prior_window_exists": (True, 1), "resync_count_zero": (False, 0), "resync_sum_zero": (False, 0),
     "resync_invalid_until_clean_pair": (False, 0), "new_window_one_pair": (False, 1), "new_window_valid": (False, 1)},
    {"offered_twenty_legal_gap_events": (True, 20), "source_input_gap_is_five_cycles": (True, 5),
     "delivered_payloads_arrive_in_order": (True, 0), "all_events_delivered_or_loss_visible": (False, 1)},
    {"exactly_two_source_drop_toggles": (True, 2), "two_drops_restore_toggle_to_initial_value": (True, 0),
     "one_accepted_event_survives": (True, 1), "two_dropped_events_are_visible": (False, 1)},
    {"pending_table_overflow_alarm": (True, 1), "overflow_makes_stats_invalid": (True, 0),
     "clear_alarm_does_not_itself_restore_stats": (True, 0), "overflow_cannot_recover_without_resync": (False, 0),
     "overflow_window_rejects_new_statistic": (False, 0)},
    {"new_session_pair_accepted": (True, 2), "retired_session_cannot_reopen_from_data": (False, 0)},
    {"one_event_delivered_before_destination_reset": (True, 1), "one_sided_reset_must_not_replay_retired_payload": (False, 1)},
    {"queued_old_events_have_arrived": (True, 1), "table_resync_alone_cannot_certify_epoch_barrier": (False, 0)},
    {"exactly_one_source_drop_toggle": (True, 1), "single_error_control_keeps_accepted_event": (True, 1),
     "single_pending_error_is_visible": (False, 1)},
]
EXPECTED_CHECKS = [set(row) for row in CHECK_SPECS]


def parse_case(output, number, tool_ok):
    marks = re.findall(r"^(?:#\s*)?LATENCY_REVIEW_COMPLETE id=(\d+) checks=(\d+) setup_failures=(\d+) requirement_failures=(\d+)$", output, re.M)
    check_rows = [dict(setup=bool(int(s)), name=n, expected=int(e), actual=int(a), passed=bool(int(p)))
                  for s, n, e, a, p in re.findall(r"^(?:#\s*)?CHECK setup=([01]) name=(\S+) expected=(\d+) actual=(\d+) pass=([01])$", output, re.M)]
    names = [x["name"] for x in check_rows]
    complete = (len(marks) == 1 and int(marks[0][0]) == number
                and int(marks[0][1]) == len(check_rows)
                and len(names) == len(set(names)) and set(names) == EXPECTED_CHECKS[number]
                and re.findall(r"^(?:#\s*)?CASE id=(\d+)$", output, re.M) == [str(number)])
    setup_failures = int(marks[0][2]) if complete else None
    failures = int(marks[0][3]) if complete else None
    consistent = (complete and all((x["setup"], x["expected"]) == CHECK_SPECS[number][x["name"]]
                                  and x["passed"] == (x["actual"] == x["expected"]) for x in check_rows)
                  and setup_failures == sum(not x["passed"] for x in check_rows if x["setup"])
                  and failures == sum(not x["passed"] for x in check_rows if not x["setup"]))
    valid = bool(tool_ok and consistent and setup_failures == 0)
    return dict(name=CASES[number], case_id=number, kind=KINDS[number], evidence_valid=valid,
                requirements_satisfied=valid and failures == 0, setup_failures=setup_failures,
                requirement_failures=failures, checks=check_rows)


def gate_results(jobs, source_unchanged, selected_gate):
    ids = [row["case_id"] for row in jobs]
    valid = (source_unchanged and len(ids) == len(set(ids)) == len(CASES)
             and set(ids) == set(range(len(CASES))) and all(row["evidence_valid"] for row in jobs)
             and all(row["kind"] == KINDS[row["case_id"]] for row in jobs))
    component = valid and all(row["requirements_satisfied"] for row in jobs
                              if row["kind"] in ("control", "component_contract"))
    all_requirements = valid and all(row["requirements_satisfied"] for row in jobs)
    return dict(evidence_valid=bool(valid), component_contract_satisfied=bool(component),
                requirements_satisfied=bool(all_requirements), selected_gate=selected_gate,
                selected_gate_satisfied=bool(component if selected_gate == "component" else all_requirements),
                integration_ready=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--revision", required=True, help="exact 40-character LATENCY commit")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--msim", required=True, type=Path)
    ap.add_argument("--gate", choices=("component", "integration"), default="integration",
                    help="component contracts or all proposed integration requirements; neither certifies MAIN")
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
        if not row["evidence_valid"]:
            status = "INVALID_EVIDENCE"
        elif row["requirements_satisfied"]:
            status = "PASS"
        else:
            status = {"component_contract": "COMPONENT_FAIL", "control": "CONTROL_FAIL",
                      "proposed_policy": "POLICY_UNDECIDED", "main_adapter_dependency": "ADAPTER_REQUIRED"}[row["kind"]]
        print(f"{status} {name}: failures={row['requirement_failures']}", flush=True)
    unchanged = before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in snap.iterdir()}
    gates = gate_results(jobs, unchanged, args.gate)
    report = dict(schema=2, created_utc=datetime.now(timezone.utc).isoformat(),
                  target_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  latency_revision=args.revision, latency_sources=manifest,
                  snapshot_sha256=before, source_unchanged=unchanged,
                  scope="Independent integration requirements; no MAIN adapter, physical CDC, P&R, bit or board proof",
                  fixture_clock_period_ns=dict(source=10, destination=14), jobs=jobs,
                  **gates)
    (args.out / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"LATENCY_HANDOFF_REVIEW_COMPLETE cases={len(jobs)} evidence_valid={gates['evidence_valid']} gate={args.gate} gate_satisfied={gates['selected_gate_satisfied']} requirements_satisfied={gates['requirements_satisfied']}")
    return 0 if gates['selected_gate_satisfied'] else 1 if gates['evidence_valid'] else 2


if __name__ == "__main__":
    try:
        result = main()
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        print(f"INVALID_EVIDENCE: {exc}", file=sys.stderr)
        result = 2
    raise SystemExit(result)
