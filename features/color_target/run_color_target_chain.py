"""detect -> track -> overlay 三级链路端到端自检。

用合成像素帧驱动整条链路，逐拍比对 overlay 判定与 track 状态。
目的：在 MAIN 介入之前证明三个模块按协议时序接在一起是对的，并给 MAIN 一份可照抄的接线。

用法：
    python features/color_target/run_color_target_chain.py
    python features/color_target/run_color_target_chain.py --sim modelsim
"""

import argparse
import importlib.util
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RTL = HERE / "rtl"
TB = HERE / "tb"
def _simlib():
    """加载共用的仿真内核 tools/simlib.py —— 本目录的脚本不写死任何人的安装路径（协议 §5.1）。"""
    spec = importlib.util.spec_from_file_location("ct_simlib", HERE / "tools" / "simlib.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


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


def main():
    ap = argparse.ArgumentParser()
    simlib = _simlib()
    simlib.add_args(ap)
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
        ok, out, err = simlib.simulate(
            srcs=[RTL / "color_classify.v", RTL / "color_target_detect.v",
                  RTL / "color_target_track.v", RTL / "color_target_overlay.v",
                  TB / "tb_color_target_chain.v"],
            tb_top=TB_NAME, params=params,
            plusargs=dict(STIM=stim.as_posix(), OUT=outp.as_posix()),
            requested=args.sim, msim_root=getattr(args, "msim", None),
            workdir=tmp, name="ch")
        if not ok:
            print("[仿真]\n      " + err.strip().replace("\n", "\n      "))
            return 2
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
