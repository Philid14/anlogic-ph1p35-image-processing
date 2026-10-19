"""Run existing independent checks and retain evidence without claiming integration.

Exit 0 means the selected checks completed, including characterization of known
gaps. Read REPORT.md / summary.json: integration_ready remains false. Use a new
--out directory for each run. No RTL, thresholds or main project are modified.
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
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def execute(command, log, completion, timeout_sec):
    """Require successful process exit AND a terminal completion witness."""
    started = time.monotonic()
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    env["COLOR_TARGET_SIM_LOG_DIR"] = str(log.parent/(log.stem+"-tool-stages"))
    try:
        child = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=timeout_sec)
        raw, code, reason = child.stdout, child.returncode, None
    except subprocess.TimeoutExpired as exc:
        raw, code, reason = exc.stdout or b"", None, "timeout"
    except OSError as exc:
        raw, code, reason = str(exc).encode("utf-8"), None, "launch_error"
    log.write_bytes(raw)
    # Preserve raw bytes above; normalize only the parsing view on Windows.
    output = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
    if reason is None:
        if code != 0:
            reason = "nonzero_exit"
        elif re.search(r"^(?:#\s*)?(?:FAIL\b|Error:|\*\*\s+(?:Error|Fatal):)", output, re.M):
            reason = "failure_marker"
        elif not re.search(completion, output, re.M):
            reason = "missing_completion"
    return dict(command=command, exit_code=code, elapsed_seconds=round(time.monotonic()-started, 3),
                log=log.name, passed=reason is None, failure=reason)


def inspect_report(name, directory):
    report = json.loads((directory/"summary.json").read_text(encoding="utf-8"))
    if name in ("class_models", "class_rtl"):
        assert report["total"] == report["passed"] == 12, "incomplete A1 configurations"
        return {"parameter_configurations": 12}
    if name == "contract":
        assert report["total"] == report["passed"] == 36, "incomplete proposed traces"
        assert report["categories_covered"] == list(range(1, 11)), "missing fault category"
        return {"traces": 36, "scope": "PROPOSED MODEL ONLY"}
    if name == "track_audit":
        assert report["trace_matched"] is True, "TRACK characterization mismatch"
        assert isinstance(report["open_gaps"], dict), "missing open-gap accounting"
        return {"samples": len(report["observed"]), "open_gaps": report["open_gaps"],
                "scope": "CURRENT RTL CHARACTERIZATION, NOT REQUIREMENTS PASS"}
    if name == "rgb_replay":
        assert report["camera_material_used"] is False, "generated controls must be synthetic"
        rows = report["results"]
        assert len(rows) == 12, "expected six geometries in both modes"
        return {"runs": len(rows), "camera_material_used": False,
                "totals": {k: sum(row[k] for row in rows) for k in
                           ("input_cycles", "accepted_pixels", "result_events", "track_events",
                            "display_probes", "legacy_results_compared", "cancelled_frames")}}
    if name == "frame_transactions":
        assert report["passed"] and report["source_unchanged"]
        assert len(report["cases"]) == 33 and all(x["passed"] for x in report["cases"])
        return {"cases": 33, "scope": "TRANSACTION MODEL PROPOSAL ONLY"}
    if name == "guard":
        assert report["passed"] and report["source_unchanged"]
        assert len(report["jobs"]) == 9 and all(x["passed"] for x in report["jobs"])
        assert sum(x["details"]["checks"] for x in report["jobs"]) == 818
        return {"jobs": 9, "checks": 818, "scope": "INDEPENDENT GUARD RTL ONLY"}
    if name == "display_transactions":
        assert report["passed"] and report["source_unchanged"]
        rows = report["jobs"]
        assert len(rows) == 6 and [x["mutation"] for x in rows] == list(range(6))
        assert all(x["matched"] and x["tool_ok"] and x["complete"] and x["checks"] == 187 for x in rows)
        assert rows[0]["failures"] == 0 and all(x["failures"] > 0 for x in rows[1:])
        return {"checks": 187, "negative_controls": 5, "scope": "TEST-ONLY DISPLAY SCHEDULER; NO PHYSICAL CDC"}
    raise ValueError("unexpected report type: "+name)


def snapshot():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8").strip()
    files = list(HERE.glob("*.py"))
    for folder in ("rtl", "model", "tb", "tools"):
        files += [p for p in (HERE/folder).rglob("*") if p.suffix in (".py", ".v", ".tcl")]
    # Text pixel checks read the real main font without modifying it.
    files += list((ROOT/"in_out_example").rglob("osd_char_lib.v"))
    return dict(head=git("rev-parse", "HEAD"), branch=git("branch", "--show-current"),
                worktree=git("status", "--porcelain=v1", "--untracked-files=all"),
                python=sys.version, python_executable=sys.executable,
                source_sha256_lf={p.relative_to(ROOT).as_posix():
                    hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                    for p in sorted(set(files))})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", choices=("models", "quick", "full", "handoff"), default="quick")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sim", choices=("auto", "modelsim", "iverilog"), default="auto")
    ap.add_argument("--msim")
    ap.add_argument("--timeout-sec", type=float, default=1800, help="per-child timeout")
    args = ap.parse_args()
    if args.timeout_sec <= 0:
        ap.error("--timeout-sec must be positive")
    if args.profile == "handoff":
        args.msim = args.msim or os.environ.get("COLOR_TARGET_MSIM")
        if args.sim != "modelsim" or not args.msim:
            ap.error("handoff requires --sim modelsim and --msim (or COLOR_TARGET_MSIM); display test is ModelSim-only")
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    before = snapshot()
    simulator = ["--sim", args.sim] + (["--msim", args.msim] if args.msim else [])
    # name, script, flags, completion regex, structured report
    jobs = [
        ("class_models", "run_target_class_contract.py", ["--models-only"], r"^PASS models TARGET_CLASS=2147483647$", True),
        ("contract", "run_integration_contract.py", [], r"^36/36 traces;", True),
        ("data_contract", "run_replay_data_checks.py", [], r"^PASS replay data contract checks=17;", False),
    ]
    if args.profile != "models":
        jobs += [
            ("class_rtl", "run_target_class_contract.py", simulator, r"^12/12 parameter configurations;", True),
            ("track_audit", "run_track_admission_audit.py", simulator, r"^Trace matched: True Open gaps: [0-9]+$", True),
            ("text_updates", "run_color_target_text_updates.py", simulator, r"^PASS text updates: 7962 clocks, 0 violations$", False),
            ("legacy_chain", "run_color_target_chain.py", simulator, r"^PASS\s+chain\s+beats=396\b", False),
        ]
    if args.profile in ("full", "handoff"):
        jobs += [
            ("classifier", "run_color_classify.py", simulator, r"^40/40 参数组合通过，共 39079 像素", False),
            ("detector", "run_color_target.py", simulator+["--full"], r"^25/25 用例通过", False),
            ("geometry", "run_color_target_overlay.py", simulator, r"^10/10 用例通过；夹取等价性 5/5 通过", False),
            ("track_regression", "run_color_target_track.py", simulator, r"^21/21 用例通过", False),
            ("real_font", "run_color_target_text_overlay.py", simulator, r"^28/28 用例通过，共 307078 像素", False),
            ("rgb_replay", "run_color_target_replay.py", simulator+["--full"], r"^PASS RGB replay: results, identities, cancellation, track, box and text$", True),
        ]
    if args.profile == "handoff":
        jobs += [
            ("frame_transactions", "run_frame_transactions.py", [], r"^FRAME_TRANSACTIONS_COMPLETE cases=33 failed=0$", True),
            ("guard", "run_track_guard_contract.py", simulator, r"^GUARD_CONTRACT_COMPLETE jobs=9 passed=9 source_unchanged=True$", True),
            ("display_transactions", "run_display_transactions.py", ["--msim", args.msim], r"^DISPLAY_TRANSACTIONS_COMPLETE jobs=6 matched=6 source_unchanged=True$", True),
        ]
    checks = []
    for name, script, flags, completion, structured in jobs:
        command = [sys.executable, "-B", "-X", "utf8", "-u", str(HERE/script), *flags]
        if structured:
            command += ["--out", str(args.out/name)]
        print("RUN", name, flush=True)
        item = execute(command, args.out/(name+".log"), completion, args.timeout_sec)
        item.update(name=name, kind="CHARACTERIZATION" if name == "track_audit" else "CHECK")
        if structured and item["passed"]:
            try:
                item["details"] = inspect_report(name, args.out/name)
            except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
                item.update(passed=False, failure="structured_report: "+str(exc))
        checks.append(item)
        print("PASS" if item["passed"] else "FAIL", name, item["failure"] or "completed", flush=True)
    after = snapshot()
    unchanged = before == after
    passed = unchanged and all(c["passed"] for c in checks)
    gates = [
        dict(name="A2 standalone guard", status="PASS" if any(c["name"] == "guard" and c["passed"] for c in checks) else "NOT_CHECKED_THIS_RUN", evidence="integration/TRACK_GUARD_INTERFACE.md; not a display freshness proof"),
        dict(name="Unwrapped legacy TRACK identity / age", status="OPEN", evidence="integration/TRACK_ADMISSION_PROPOSAL.md"),
        dict(name="MAIN normalization / CDC / DDR / atomic display", status="OPEN", evidence="integration/MAIN_CONTRACT_DRAFT.md"),
        dict(name="Integrated TARGET P&R and bit", status="NOT_RUN", evidence="No TARGET in current main TD entry"),
        dict(name="Real camera policy / thresholds", status="PENDING_MATERIAL", evidence="User reserved decision until real camera material"),
        dict(name="Board acceptance", status="NOT_RUN", evidence="board/OBSERVATION_GUIDE.md"),
    ]
    report = dict(schema=1, created_utc=datetime.now(timezone.utc).isoformat(), profile=args.profile,
                  checks_status="PASS" if passed else "FAIL", integration_ready=False,
                  exit_semantics="0 = selected independent checks completed; open gates remain",
                  source=before, source_unchanged_during_run=unchanged, checks=checks, gates=gates)
    (args.out/"summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    lines = ["# TARGET verification run", "", f"Independent checks: **{report['checks_status']}**; integration ready: **NO**.",
             f"Profile: `{args.profile}`. HEAD: `{before['head']}`. Source stable: `{unchanged}`.",
             "A dirty worktree is identified below; source LF hashes are in summary.json.", "", "```text", before["worktree"] or "clean", "```", "",
             "| Check | Kind | Result | Exit | Log |", "|---|---|---|---:|---|"]
    for c in checks:
        lines.append(f"| {c['name']} | {c['kind']} | {'MATCHED / OPEN' if c['passed'] and c['kind']=='CHARACTERIZATION' else ('PASS' if c['passed'] else 'FAIL')} | {c['exit_code']} | [{c['log']}]({c['log']}) |")
        if c.get("failure"):
            lines.append(f"\nFailure {c['name']}: {c['failure']}\n")
    lines += ["", "## Unclosed engineering gates", ""]
    lines += [f"- {g['name']}: **{g['status']}** ({g['evidence']})." for g in gates]
    for c in checks:
        if c["name"] == "track_audit" and "details" in c:
            lines += ["", "## Current TRACK gaps", ""]
            lines += [f"- {k}: {v}" for k, v in c["details"]["open_gaps"].items()]
    lines += ["", "Full argv, source hashes, durations and structured results: [summary.json](summary.json).",
              "No physical CDC, integrated timing, camera accuracy or board result is established.", ""]
    (args.out/"REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("CHECKS", report["checks_status"], "INTEGRATION NOT READY; read", args.out/"REPORT.md", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
