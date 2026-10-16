#!/usr/bin/env python3
"""Standalone build entry point for the latency / OSD display deliverable.

Two levels, in the order the project demands (AGENTS.md section 11/12):

1. always: an elaboration check of the RTL with the local Icarus Verilog, so a
   missing include or a syntax error cannot reach the vendor tool silently;
2. optional: a Tang Dynasty single module synthesis run. It needs the local TD
   installation at .tools/td/app (see docs/setup/tangdynasty.md) and is skipped
   with a clear message when TD is absent - this script must not pretend a build
   happened.

Usage
    python scripts/build-latency.py                 # elaboration check only
    python scripts/build-latency.py --td            # also try the TD synthesis
    python scripts/build-latency.py --check-only    # elaboration check, no output

Results of an actual TD run are written to work/output/latency-osd/td/ and must
then be quoted from those files, never from this script's summary.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work/output/latency-osd/td"

SOURCES = [
    ROOT / "work/rtl/latency/latency_meter.v",
    ROOT / "work/rtl/osd/char_rom.v",
    ROOT / "work/rtl/osd/text_overlay.v",
    ROOT / "work/rtl/osd/latency_osd.v",
]
INCLUDES = [ROOT / "work/rtl/osd"]
TOP = "latency_osd"


def find_iverilog() -> Path | None:
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
    return None


def elaboration_check(iverilog: Path) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    exe = OUT / "elaborate.vvp"
    cmd = [str(iverilog), "-g2012", "-Wall", "-s", TOP, "-o", str(exe)]
    cmd += ["-I" + str(p) for p in INCLUDES]
    cmd += [str(p) for p in SOURCES]
    env = dict(os.environ)
    extra = [iverilog.parent]
    sibling_lib = iverilog.parent.parent / "lib"
    if sibling_lib.is_dir():
        extra.append(sibling_lib)     # OSS CAD Suite keeps shared libraries here
    env["PATH"] = os.pathsep.join(str(p) for p in extra) + os.pathsep + env.get("PATH", "")
    print(">>", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        print("ELABORATION FAILED (rc=%d)" % proc.returncode)
        return proc.returncode
    exe.unlink(missing_ok=True)
    print("ELABORATION OK (top=%s, %d sources)" % (TOP, len(SOURCES)))
    return 0


def td_synthesis() -> int:
    td = ROOT / ".tools/td/app"
    if not td.is_dir():
        print("TD not found at .tools/td/app: skipping the synthesis step.")
        print("Install / open Tang Dynasty as described in docs/setup/tangdynasty.md,")
        print("then add the four sources of SOURCES plus the include directory")
        print("work/rtl/osd to a project with top level %s." % TOP)
        print("Record LUT/register/ERAM usage and Setup/Hold WNS in")
        print("docs/experiments/2026-10-16-latency-display.md section 6.")
        return 0
    print("TD found at %s" % td)
    print("This project has no verified batch synthesis recipe for a standalone")
    print("module yet (the existing recipe, scripts/build_and_run_td.py, builds the")
    print("camera_to_dsi_display project). Opening TD manually is the documented")
    print("route; do not record numbers that were not produced by a real run.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--td", action="store_true", help="also attempt the TD synthesis")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    iverilog = find_iverilog()
    if iverilog is None:
        print("iverilog not found: set IVERILOG_BIN or install it under .tools/iverilog")
        return 1
    rc = elaboration_check(iverilog)
    if rc:
        return rc
    if args.td and not args.check_only:
        return td_synthesis()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
