"""detect -> track -> overlay 三级链路端到端自检。

用合成像素帧驱动整条链路，逐拍比对 overlay 判定与 track 状态。
目的：在 MAIN 介入之前证明三个模块按协议时序接在一起是对的，并给 MAIN 一份可照抄的接线。

用法：
    python features/color_target/run_color_target_chain.py
    python features/color_target/run_color_target_chain.py --sim modelsim
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
TB_NAME = "tb_color_target_chain"
MOD_NAME = "color_target_chain"

DET = dict(target_class=0, hue_half_width_deg=30, c_min=24, v_min=32,
           min_count=4, xw=11, yw=10)
TRK = dict(acq_frames=3, lost_frames=15, max_jump=0)
OVL = dict(box_thick=3, box_rgb=0x00FF00, cross_arm=12, cross_thick=1,
           cross_rgb=0xFFFF00)

RED = (230, 30, 30)
WHITE = (200, 200, 200)


def load_model():
    spec = importlib.util.spec_from_file_location(
        "ref_ct_chain", HERE / "model" / "ref_color_target_chain.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def pack(px):
    v = 0
    for (r, g, b) in px:
        v = (v << 24) | (r << 16) | (g << 8) | b
    return v


def frame(width, height, painter, session, fid):
    beats, k = [], 0
    for y in range(height):
        for x in range(0, width, 4):
            px = [painter(min(x + i, width - 1), y) for i in range(4)]
            last_row = (x + 4 >= width)
            last = last_row and (y == height - 1)
            beats.append(dict(valid=1, sof=1 if k == 0 else 0,
                              eol=1 if last_row else 0, eof=1 if last else 0,
                              abort=0, x0=x, y=y, data96=pack(px),
                              session=session, frame=fid))
            k += 1
    return beats


def idle(n=2):
    return [dict(valid=0, sof=0, eol=0, eof=0, abort=0, x0=0, y=0,
                 data96=0, session=0, frame=0) for _ in range(n)]


def build_beats():
    """6 帧：无目标 -> 红块左 -> 红块中 -> 红块右 -> 无目标 -> 红块重现。"""
    W, H = 32, 8

    def blk(xa, xb):
        def p(x, y):
            return RED if (xa <= x <= xb and 2 <= y <= 5) else WHITE
        return p

    def none(x, y):
        return WHITE

    beats = []
    beats += frame(W, H, none, 1, 1) + idle()
    beats += frame(W, H, blk(4, 11), 1, 2) + idle()
    beats += frame(W, H, blk(12, 19), 1, 3) + idle()
    beats += frame(W, H, blk(20, 27), 1, 4) + idle()
    beats += frame(W, H, none, 1, 5) + idle()          # 目标消失 -> HOLD
    beats += frame(W, H, blk(8, 15), 1, 6) + idle()    # 目标重现 -> TRACK
    return beats


def write_stim(path, beats):
    with open(path, "w", encoding="ascii") as f:
        for b in beats:
            d = b["data96"]
            f.write("%d %d %d %d %d %d %d %08x %08x %08x %d %d\n" % (
                b["valid"], b["sof"], b["eol"], b["eof"], b["abort"],
                b["x0"], b["y"], (d >> 64) & 0xFFFFFFFF,
                (d >> 32) & 0xFFFFFFFF, d & 0xFFFFFFFF, b["session"], b["frame"]))


def compile_iverilog(tmp, params):
    iv = shutil.which("iverilog") or "C:/iverilog/bin/iverilog.exe"
    if not Path(iv).exists():
        return None
    cmd = [iv, "-g2005", "-Wall", "-s", TB_NAME]
    for k, v in params.items():
        cmd.append(f"-P{TB_NAME}.{k}={v}")
    cmd += ["-o", str(tmp / "ch.vvp"), str(TB / "tb_color_target_chain.v"),
            str(RTL / "color_classify.v"), str(RTL / "color_target_detect.v"),
            str(RTL / "color_target_track.v"), str(RTL / "color_target_overlay.v")]
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
                        str(RTL / "color_classify.v"), str(RTL / "color_target_detect.v"),
                        str(RTL / "color_target_track.v"), str(RTL / "color_target_overlay.v"),
                        str(TB / "tb_color_target_chain.v")],
                       cwd=tmp, capture_output=True, text=True, env=env)
    return "modelsim" if r.returncode == 0 else f"[vlog 失败]\n{r.stdout}\n{r.stderr}"


def run_sim(sim, tmp, params, stim, outp):
    if sim == "iverilog":
        vvp = shutil.which("vvp") or "C:/iverilog/bin/vvp.exe"
        r = subprocess.run([vvp, str(tmp / "ch.vvp"), f"+STIM={stim.as_posix()}",
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
    beats = build_beats()
    want_recs = model.sim_chain(beats, dict(detect=DET, track=TRK, overlay=OVL))
    want = [[r["state"], r["show"], 1 if r["ov"] else 0, (r["ov"] or 0)] for r in want_recs]

    params = dict(TARGET_CLASS=DET["target_class"], HUE_HALF_WIDTH_DEG=DET["hue_half_width_deg"],
                  C_MIN=DET["c_min"], V_MIN=DET["v_min"], MIN_COUNT=DET["min_count"],
                  XW=DET["xw"], YW=DET["yw"],
                  ACQ_FRAMES=TRK["acq_frames"], LOST_FRAMES=TRK["lost_frames"],
                  MAX_JUMP=TRK["max_jump"],
                  BOX_THICK=OVL["box_thick"], CROSS_ARM=OVL["cross_arm"])

    with tempfile.TemporaryDirectory(prefix="ctchain-") as td:
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
            print("[仿真台]\n" + out.strip()[-2500:])
            return 1

        got = []
        if outp.exists():
            for line in outp.read_text().splitlines():
                if line.strip():
                    st, sh, ov, rgb = line.split()
                    got.append([int(st), int(sh), int(ov),
                                int(rgb, 16) if int(ov) else 0])

        if got != want:
            bad = [(i, got[i], want[i]) for i in range(min(len(got), len(want)))
                   if got[i] != want[i]]
            print(f"FAIL  {len(bad)}/{len(want)} 拍不同")
            for i, g, w in bad[:8]:
                b = beats[i]
                print(f"      拍{i} (x0={b['x0']} y={b['y']} eof={b['eof']}): "
                      f"got={g} want={w}")
            return 1

        # 顺带汇报关键节点，便于人工核对链路行为
        print(f"PASS  chain  beats={len(want)}  [sim={args.sim}]")
        prev = None
        for i, r in enumerate(want_recs):
            if r["state"] != prev:
                print(f"      拍{i:4d}: track_state={r['state']} show={r['show']}")
                prev = r["state"]
        return 0


if __name__ == "__main__":
    sys.exit(main())
