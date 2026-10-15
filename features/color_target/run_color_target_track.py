"""color_target_track 的独立自检：生成逐帧激励 -> 仿真 -> 与参考模型逐帧比对。

用法：
    python features/color_target/run_color_target_track.py
    python features/color_target/run_color_target_track.py --sim modelsim
"""

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RTL = HERE / "rtl"
TB = HERE / "tb"
MSIM = Path(r"D:\altera\14.1\modelsim_ase\win32aloem")
TB_NAME = "tb_color_target_track"
MOD_NAME = "color_target_track"


def load_model():
    spec = importlib.util.spec_from_file_location(
        "ref_ct_tr", HERE / "model" / "ref_color_target_track.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def B(**kw):
    """一帧的默认结果；用关键字覆盖。"""
    d = dict(strobe=1, rvalid=1, present=1, count=100,
             xmin=100, xmax=199, ymin=50, ymax=99, cx=149, cy=74,
             session=1, frame=1)
    d.update(kw)
    return d


def build_cases():
    cases = []

    cases.append(("never_present", [B(present=0) for _ in range(5)], {}))

    cases.append(("acquire_at_threshold",
                  [B(frame=1), B(frame=2), B(frame=3), B(frame=4)], {}))

    cases.append(("acq_interrupted",
                  [B(frame=1), B(frame=2), B(present=0, frame=3), B(frame=4)], {}))

    cases.append(("track_hold_reacquire",
                  [B(frame=1), B(frame=2), B(frame=3),
                   B(present=0, frame=4), B(frame=5)], {}))

    cases.append(("hold_then_lost",
                  [B(frame=1), B(frame=2), B(frame=3)]
                  + [B(present=0, frame=4 + i) for i in range(15)],
                  {"lost_frames": 15}))

    cases.append(("abort_frames_ignored",
                  [B(frame=1), B(frame=2), B(frame=3)]
                  + [B(rvalid=0, present=0, frame=4 + i) for i in range(3)]
                  + [B(frame=7)],
                  {}))

    cases.append(("session_change_resets",
                  [B(frame=1), B(frame=2), B(frame=3), B(session=2, frame=1)], {}))

    # HOLD 期间必须保持"上一次被接受"的那一帧，不能被丢失帧清零
    cases.append(("bundle_held_during_hold",
                  [B(frame=1, count=100, xmin=10, xmax=19, ymin=10, ymax=19, cx=14, cy=14),
                   B(frame=2, count=200, xmin=20, xmax=29, ymin=20, ymax=29, cx=24, cy=24),
                   B(frame=3, count=300, xmin=30, xmax=39, ymin=30, ymax=39, cx=34, cy=34),
                   B(present=0, count=0, xmin=0, xmax=0, ymin=0, ymax=0, cx=0, cy=0,
                     frame=4)], {}))

    # 跳变门限：确认后突然跳到远处应按未检出处理
    cases.append(("jump_rejected",
                  [B(frame=1, cx=100, cy=100), B(frame=2, cx=100, cy=100),
                   B(frame=3, cx=100, cy=100),
                   B(frame=4, cx=500, cy=100)], {"max_jump": 50}))

    # 与上一例同样输入但门限关闭：应被接受
    cases.append(("jump_allowed_when_disabled",
                  [B(frame=1, cx=100, cy=100), B(frame=2, cx=100, cy=100),
                   B(frame=3, cx=100, cy=100),
                   B(frame=4, cx=500, cy=100)], {"max_jump": 0}))

    # 无 strobe 的拍不得改变任何状态
    cases.append(("no_strobe_no_change",
                  [B(frame=1), B(frame=2), B(frame=3),
                   B(strobe=0, present=0, frame=4), B(strobe=0, present=0, frame=5),
                   B(frame=6)], {}))

    return cases


def write_stim(path, beats):
    with open(path, "w", encoding="ascii") as f:
        for b in beats:
            f.write("%d %d %d %0d %0d %0d %0d %0d %0d %0d %d %d\n" % (
                b["strobe"], b["rvalid"], b["present"], b["count"],
                b["xmin"], b["xmax"], b["ymin"], b["ymax"], b["cx"], b["cy"],
                b["session"], b["frame"]))


def compile_iverilog(tmp, params):
    iv = shutil.which("iverilog") or "C:/iverilog/bin/iverilog.exe"
    if not Path(iv).exists():
        return None
    cmd = [iv, "-g2005", "-Wall", "-s", TB_NAME]
    for k, v in params.items():
        cmd.append(f"-P{TB_NAME}.{k}={v}")
    cmd += ["-o", str(tmp / "tr.vvp"), str(TB / "tb_color_target_track.v"),
            str(RTL / "color_target_track.v")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return "iverilog" if r.returncode == 0 else f"[iverilog 编译失败]\n{r.stdout}\n{r.stderr}"


def compile_modelsim(tmp, params):
    if not MSIM.exists():
        return None
    exe = lambda n: str(MSIM / n)
    env = dict(os.environ)
    env["PATH"] = f"{MSIM};{env.get('PATH','')}"
    subprocess.run([exe("vlib.exe"), "work"], cwd=tmp, capture_output=True, text=True, env=env)
    r = subprocess.run([exe("vlog.exe"), "-quiet", "-work", "work",
                        str(RTL / "color_target_track.v"),
                        str(TB / "tb_color_target_track.v")],
                       cwd=tmp, capture_output=True, text=True, env=env)
    return "modelsim" if r.returncode == 0 else f"[vlog 失败]\n{r.stdout}\n{r.stderr}"


def run_sim(sim, tmp, params, stim, outp):
    if sim == "iverilog":
        vvp = shutil.which("vvp") or "C:/iverilog/bin/vvp.exe"
        r = subprocess.run([vvp, str(tmp / "tr.vvp"), f"+STIM={stim.as_posix()}",
                            f"+OUT={outp.as_posix()}"], cwd=tmp,
                           capture_output=True, text=True)
    else:
        exe = lambda n: str(MSIM / n)
        env = dict(os.environ)
        env["PATH"] = f"{MSIM};{env.get('PATH','')}"
        cmd = [exe("vsim.exe"), "-c", "-quiet"]
        for k, v in params.items():
            cmd.append(f"-g{k}={v}")
        cmd += [f"work.{TB_NAME}", f"+STIM={stim.as_posix()}", f"+OUT={outp.as_posix()}",
                "-do", "run -all; quit -f"]
        r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, env=env)
    return r.stdout + r.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", default="auto", choices=["auto", "iverilog", "modelsim"])
    args = ap.parse_args()

    model = load_model()
    total = passed = 0
    for name, beats, over in build_cases():
        p = dict(model.TRACK_DEFAULTS, **over)
        want_recs = model.sim_track([dict(b) for b in beats], p)
        want = [[r["state"], r["show"], r["count"], r["xmin"], r["xmax"], r["ymin"],
                 r["ymax"], r["cx"], r["cy"], r["session"], r["frame"], r["change"]]
                for r in want_recs]

        total += 1
        params = dict(XW=11, YW=10, ACQ_FRAMES=p["acq_frames"],
                      LOST_FRAMES=p["lost_frames"], MAX_JUMP=p["max_jump"])
        with tempfile.TemporaryDirectory(prefix="cttr-") as td:
            tmp = Path(td)
            stim, outp = tmp / "stim.txt", tmp / "dut.txt"
            write_stim(stim, beats)
            sim = args.sim
            if sim == "auto":
                sim = compile_iverilog(tmp, params) or compile_modelsim(tmp, params)
            else:
                sim = compile_iverilog(tmp, params) if sim == "iverilog" \
                      else compile_modelsim(tmp, params)
            if sim not in ("iverilog", "modelsim"):
                print(sim)
                return 2
            out = run_sim(sim, tmp, params, stim, outp)
            if "FAIL" in out or f"PASS {MOD_NAME}" not in out:
                print(f"FAIL  {name}  [仿真台]\n      " + out.strip().replace("\n", "\n      "))
                continue

            got = []
            if outp.exists():
                for line in outp.read_text().splitlines():
                    if line.strip():
                        got.append([int(v) for v in line.split()])
            if got != want:
                bad = [(i, got[i], want[i]) for i in range(min(len(got), len(want)))
                       if got[i] != want[i]]
                print(f"FAIL  {name}  [与模型不符]  {len(bad)}/{len(want)} 帧不同")
                for i, g, w in bad[:5]:
                    print(f"      帧{i}: got={g} want={w}")
                continue
            passed += 1
            print(f"PASS  {name}  (frames={len(want)})")

    print(f"\n{passed}/{total} 用例通过  [sim={args.sim}]")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
