#!/usr/bin/env python3
"""Loss-accounting test for frame_event_bridge.v (TARGET review 2026-10-21).

Checks:
  * 20 legal events with the destination paused, depth 16 -> delivered 16,
    lost 4 (the old design lost them silently);
  * two consecutive too-close events -> lost +2 (the old toggle could cancel
    an even number of errors).
"""
from __future__ import annotations

import os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FEAT = HERE.parent
ROOT = FEAT.parents[1]
OUT = FEAT / ".build"


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


def main():
    iver = find_iverilog()
    OUT.mkdir(parents=True, exist_ok=True)
    exe = OUT / "tb_frame_event_bridge.vvp"
    cmd = [str(iver), "-g2012", "-s", "tb_frame_event_bridge", "-o", str(exe),
           str(HERE / "tb_frame_event_bridge.v"), str(FEAT / "rtl/frame_event_bridge.v")]
    env = dict(os.environ)
    extra = [iver.parent]
    lib = iver.parent.parent / "lib"
    if lib.is_dir():
        extra.append(lib)
    env["PATH"] = os.pathsep.join(str(p) for p in extra) + os.pathsep + env.get("PATH", "")
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if p.returncode:
        print(p.stdout + p.stderr)
        return 1
    vvp = iver.parent / ("vvp.exe" if os.name == "nt" else "vvp")
    r = subprocess.run([str(vvp), str(exe)], capture_output=True, text=True, env=env)
    text = r.stdout + r.stderr
    (OUT / "tb_frame_event_bridge.log").write_text(text, encoding="utf-8", newline="\n")
    m = re.search(r"FINAL lost=(\d+) delivered=(\d+)", text)
    fails = []
    if not m:
        fails.append("no FINAL line")
    else:
        lost, delivered = int(m.group(1)), int(m.group(2))
        if lost != 6:
            fails.append("lost=%d expected 6 (4 full + 2 too-close)" % lost)
        if delivered != 17:
            fails.append("delivered=%d expected 17" % delivered)
    for line in text.strip().splitlines():
        print("  " + line)
    for f in fails:
        print("FAIL: %s" % f)
    print("RESULT: %s" % ("PASS" if not fails else "FAIL"))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
