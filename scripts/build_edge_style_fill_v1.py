"""Complete TD build for EDGE_STYLE_FILL_V1 from one clean source commit.

No clock, seed, pin, SDC, sensor or option changes. The script verifies every
TD input against the committed source before Synthesis, then reruns Physical
Design through final timing and bit generation.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse
import hashlib
import json
import os
import re
import subprocess

import prepare_td_runs

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project"
OUT = ROOT / "tmp/edge_style_fill_v1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-phy", action="store_true")
    args = parser.parse_args()
    assert not subprocess.check_output(
        ["git", "diff", "HEAD", "--name-only"], cwd=ROOT
    ).strip(), "commit tracked work first"
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    entries = re.findall(
        r'<File Path="([^"]+)"', (P / "camera_to_dsi_display.al").read_text(encoding="utf-8")
    )
    assert len(entries) == 66, len(entries)
    assert any(path.endswith("isp/rgb_effects_96.v") for path in entries)
    assert any(path.endswith("isp/style_fill_96.v") for path in entries)
    assert not any(
        "temporal_roi_capture" in path
        or "probe_" in path
        or "temporal_packet" in path
        for path in entries
    )
    manifest = {}
    for entry in entries:
        path = (P / entry).resolve()
        rel = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        saved = subprocess.check_output(["git", "show", commit + ":" + rel], cwd=ROOT)
        assert data.replace(b"\r\n", b"\n") == saved.replace(b"\r\n", b"\n"), rel
        manifest[rel] = hashlib.sha256(data).hexdigest()

    td = Path(os.environ.get("TD_HOME", "D:/TD"))
    exe = td / "bin/td_commands_prompt.exe"
    flow = td / "doc/scripts/DefaultFlow.tcl"
    snapshot = dict(
        source_commit=commit,
        time=datetime.now(timezone(timedelta(hours=8))).isoformat(),
        files=manifest,
        old_bits={
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (ROOT / "artifacts/bitstreams").glob("*/*.bit")
        },
        default_flow_sha256=hashlib.sha256(flow.read_bytes()).hexdigest(),
    )
    OUT.mkdir(exist_ok=True)
    if args.resume_phy:
        previous = json.loads((OUT / "prebuild.json").read_text())
        assert previous["files"] == snapshot["files"], "cannot reuse synthesis after input changes"
        assert "export_db camera_to_dsi_display_gate.db" in (
            OUT / "syn_1_stdout.txt"
        ).read_text(errors="replace")
        previous["resume_driver_commit"] = commit
        previous["synthesis_db_sha256"] = hashlib.sha256(
            (P / "camera_to_dsi_display_Runs/syn_1/camera_to_dsi_display_gate.db").read_bytes()
        ).hexdigest()
        (OUT / "prebuild.json").write_text(json.dumps(previous, indent=2) + "\n")
    else:
        (OUT / "prebuild.json").write_text(json.dumps(snapshot, indent=2) + "\n")

    prepare_td_runs.main()
    wrapper = OUT / "final_flow.tcl"
    wrapper.write_text(
        "source {" + flow.as_posix() + "}\n"
        "report_timing_summary -file final_timing.rpt -ep_num 10 -path_num 1\n"
        "report_timing_ignored -file ignored_timing.rpt\n"
        "exit\n"
    )
    runs = (
        (("phy_1", wrapper),)
        if args.resume_phy
        else (("syn_1", flow), ("phy_1", wrapper))
    )
    for run, script in runs:
        directory = P / "camera_to_dsi_display_Runs" / run
        stop = directory / ".stop.f"
        if stop.exists():
            stop.unlink()
        output = OUT / (run + "_stdout.txt")
        print("START", run, commit, flush=True)
        with output.open("wb") as log:
            result = subprocess.run(
                [exe.as_posix(), script.as_posix()],
                cwd=directory,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        text = output.read_text(errors="replace")
        assert result.returncode == 0 and not re.search(r"\bERROR\s*:", text), (
            run,
            result.returncode,
        )
        assert "Flow Statistics" in text, run
        if run == "syn_1":
            assert "export_db camera_to_dsi_display_gate.db" in text
            area = (directory / "camera_to_dsi_display_gate.area").read_text()
            rows = [line for line in area.splitlines() if "rgb_effects_96" in line]
            assert rows, "new RGB effects module missing from synthesis area"
            row = next(line for line in area.splitlines() if "|edge_temporal_hold " in line)
            cols = [value.strip() for value in row.split("|")[1:-1]]
            print("HISTORY RAM ROW", row, flush=True)
            print("RGB EFFECT ROW", rows[0], flush=True)
            assert int(cols[5]) >= 1 and int(cols[4]) < 2000, "history became registers"
        else:
            assert "BIT-1004 : Generate file camera_to_dsi_display.bit." in text
        print("COMPLETE", run, "exit", result.returncode, flush=True)
    print("COMPLETE TD; inspect final STA, resources and warnings before candidate", flush=True)


if __name__ == "__main__":
    main()
