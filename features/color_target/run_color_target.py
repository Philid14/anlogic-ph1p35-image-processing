"""color_target_detect 的独立自检：生成激励 -> 仿真 -> 与参考模型逐行比对。

只验证**模块本身**在模拟输入下的行为。不接主线、不生成 bit、不代表整机或上板通过
（协议 §5.2：主线接口未接入时只能称"独立模块完成 / 模拟事件验证通过"）。

用法：
    python features/color_target/run_color_target.py            # 自动选仿真器
    python features/color_target/run_color_target.py --sim modelsim
    python features/color_target/run_color_target.py --full     # 追加一个真实尺寸帧
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

DEFAULTS = dict(target_class=0, hue_half_width_deg=30, c_min=24, v_min=32,
                min_count=4, xw=11, yw=10)

RED = (230, 30, 30)
WHITE = (200, 200, 200)
ORANGE = (250, 150, 40)      # hue 偏出 ±30 度窗口
PINK = (200, 170, 170)       # 彩度低
DARKRED = (60, 12, 12)       # 亮度低


def load_model():
    spec = importlib.util.spec_from_file_location("ref_ct", HERE / "model" / "ref_color_target.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def pack(pixels):
    """4 个 (r,g,b) -> 96 位，lane0 在高位。"""
    v = 0
    for (r, g, b) in pixels:
        v = (v << 24) | (r << 16) | (g << 8) | b
    return v


def make_frame(width, height, painter, session, frame, *, abort=False,
               emit_eof=True, first_beat_hook=None):
    """把一帧铺成 beat 序列。painter(x, y) -> (r,g,b)。"""
    beats, k = [], 0
    total_rows = height
    for y in range(total_rows):
        for x in range(0, width, 4):
            px = [painter(min(x + i, width - 1), y) for i in range(4)]
            last_of_row = (x + 4 >= width)
            last_of_frame = last_of_row and (y == total_rows - 1)
            b = dict(valid=1, sof=1 if k == 0 else 0, eol=1 if last_of_row else 0,
                     eof=(1 if (last_of_frame and emit_eof) else 0),
                     abort=1 if (abort and k == 0) else 0,
                     x0=x, y=y, data96=pack(px), session=session, frame=frame)
            if k == 0 and first_beat_hook:
                first_beat_hook(b)
            beats.append(b)
            k += 1
    return beats


def idle(n=3):
    return [dict(valid=0, sof=0, eol=0, eof=0, abort=0, x0=0, y=0,
                 data96=0, session=0, frame=0) for _ in range(n)]


def build_cases(p):
    """返回 [(名称, beats, 该用例的参数覆盖)]。"""
    cases = []

    cases.append(("flat_white_no_target",
                  make_frame(8, 2, lambda x, y: WHITE, 1, 10), {}))

    cases.append(("single_beat_all_red",
                  make_frame(4, 1, lambda x, y: RED, 1, 11), {}))

    # 阈值边界：4 个像素里只有 3 个命中 -> 计数 3 < MIN_COUNT(4)
    def three_of_four(x, y):
        return RED if x < 3 else WHITE
    cases.append(("count_below_min",
                  make_frame(4, 1, three_of_four, 1, 12), {}))

    # 目标块：x 8..23、y 2..5 -> 16*4=64 个像素；框 8..23 / 2..5，中心 (15,3)
    def rect(x, y):
        return RED if (8 <= x <= 23 and 2 <= y <= 5) else WHITE
    cases.append(("red_rect_bbox",
                  make_frame(32, 8, rect, 1, 13), {}))

    # 贴左上角，检验 x=0 / y=0 边界
    def corner(x, y):
        return RED if (x <= 3 and y <= 1) else WHITE
    cases.append(("corner_origin",
                  make_frame(16, 4, corner, 1, 14), {}))

    # 最右列：1280 宽下 xmax 应为 1279（XW=11 的上限）
    def last_cols(x, y):
        return RED if x >= 1276 else WHITE
    cases.append(("xmax_at_1279",
                  make_frame(1280, 2, last_cols, 1, 15), {}))

    # 中间帧被中止
    cases.append(("aborted_frame",
                  make_frame(32, 8, rect, 1, 16, abort=True), {}))

    # 截断帧（不发 eof）后接一帧正常帧：只应发布后者的结果
    trunc = make_frame(16, 4, rect, 1, 17, emit_eof=False)
    ok = make_frame(16, 4, rect, 1, 18)
    cases.append(("truncated_then_ok", trunc + idle(2) + ok, {}))

    # 颜色边界：橙 / 低彩 / 暗红都不应计入
    cases.append(("orange_out_of_hue",
                  make_frame(8, 2, lambda x, y: ORANGE, 1, 19), {}))
    cases.append(("low_chroma",
                  make_frame(8, 2, lambda x, y: PINK, 1, 20), {}))
    cases.append(("dark_red",
                  make_frame(8, 2, lambda x, y: DARKRED, 1, 21), {}))

    # 参数化验证：同一块绿/蓝目标，只有在对应 TARGET_CLASS 下才应命中
    def green_block(x, y):
        return (30, 220, 40) if (4 <= x <= 11 and y <= 1) else WHITE
    cases.append(("green_as_class1",
                  make_frame(16, 2, green_block, 1, 22), {"target_class": 1}))
    cases.append(("green_not_counted_as_red",
                  make_frame(16, 2, green_block, 1, 22), {"target_class": 0}))

    def blue_block(x, y):
        return (30, 40, 220) if (4 <= x <= 11 and y <= 1) else WHITE
    cases.append(("blue_as_class2",
                  make_frame(16, 2, blue_block, 1, 23), {"target_class": 2}))

    # 跨帧身份：两帧不同 session/frame，结果必须各自对应
    f1 = make_frame(8, 2, rect, 7, 100)
    f2 = make_frame(8, 2, rect, 7, 101)
    cases.append(("frame_id_propagation", f1 + idle(2) + f2, {}))

    return cases


def extra_full_frame(p):
    """真实尺寸帧：1280x720，中央一块 200x100 的红块。"""
    def painter(x, y):
        return RED if (540 <= x <= 739 and 310 <= y <= 409) else WHITE
    return [("full_1280x720", make_frame(1280, 720, painter, 3, 9), {})]


def write_stim(path, beats):
    with open(path, "w", encoding="ascii") as f:
        for b in beats:
            d = b["data96"]
            f.write("%d %d %d %d %d %d %d %08x %08x %08x %d %d\n" % (
                b["valid"], b["sof"], b["eol"], b["eof"], b["abort"],
                b["x0"], b["y"], (d >> 64) & 0xFFFFFFFF,
                (d >> 32) & 0xFFFFFFFF, d & 0xFFFFFFFF, b["session"], b["frame"]))


def sim_iverilog(tmp, params):
    iv = shutil.which("iverilog") or "C:/iverilog/bin/iverilog.exe"
    vvp = shutil.which("vvp") or "C:/iverilog/bin/vvp.exe"
    if not Path(iv).exists():
        return None
    cmd = [iv, "-g2005", "-Wall", "-s", "tb_color_target"]
    for k, v in params.items():
        cmd.append(f"-Ptb_color_target.{k}={v}")
    cmd += ["-o", str(tmp / "ct.vvp"), str(TB / "tb_color_target.v"),
            str(RTL / "color_target_detect.v"), str(RTL / "color_classify.v")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return f"[iverilog 编译失败]\n{r.stdout}\n{r.stderr}"
    return "iverilog"


def sim_modelsim(tmp, params):
    if not MSIM.exists():
        return None
    exe = lambda n: str(MSIM / n)
    env = dict(os.environ)
    env["PATH"] = f"{MSIM};{env.get('PATH','')}"
    def sh(c):
        return subprocess.run(c, cwd=tmp, capture_output=True, text=True, env=env)
    sh([exe("vlib.exe"), "work"])
    r = sh([exe("vlog.exe"), "-quiet", "-work", "work",
            str(RTL / "color_classify.v"), str(RTL / "color_target_detect.v"),
            str(TB / "tb_color_target.v")])
    if r.returncode != 0:
        return f"[vlog 失败]\n{r.stdout}\n{r.stderr}"
    return "modelsim"


def run_sim(sim, tmp, params, stim, outp):
    if sim == "iverilog":
        vvp = shutil.which("vvp") or "C:/iverilog/bin/vvp.exe"
        cmd = [vvp, str(tmp / "ct.vvp"), f"+STIM={stim.as_posix()}", f"+OUT={outp.as_posix()}"]
    else:
        exe = lambda n: str(MSIM / n)
        env = dict(os.environ)
        env["PATH"] = f"{MSIM};{env.get('PATH','')}"
        cmd = [exe("vsim.exe"), "-c", "-quiet"]
        for k, v in params.items():
            cmd.append(f"-g{k}={v}")
        cmd += ["work.tb_color_target", f"+STIM={stim.as_posix()}",
                f"+OUT={outp.as_posix()}", "-do", "run -all; quit -f"]
        r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, env=env)
        return r.stdout + r.stderr
    r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
    return r.stdout + r.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", default="auto", choices=["auto", "iverilog", "modelsim"])
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    model = load_model()
    cases = build_cases(DEFAULTS)
    if args.full:
        cases += extra_full_frame(DEFAULTS)

    total = passed = 0
    for name, beats, over in cases:
        p = dict(DEFAULTS, **over)
        total += 1
        # 参考模型期望（用同一份 beat 序列）
        mbeats = [dict(b) for b in beats]
        expect = model.run(mbeats, p)

        with tempfile.TemporaryDirectory(prefix="ct-") as td:
            tmp = Path(td)
            stim = tmp / "stim.txt"
            outp = tmp / "dut.txt"
            write_stim(stim, beats)
            params = dict(TARGET_CLASS=p["target_class"],
                          HUE_HALF_WIDTH_DEG=p["hue_half_width_deg"],
                          C_MIN=p["c_min"], V_MIN=p["v_min"],
                          MIN_COUNT=p["min_count"], XW=p["xw"], YW=p["yw"])
            sim = args.sim
            if sim == "auto":
                sim = sim_iverilog(tmp, params) or sim_modelsim(tmp, params)
                if sim not in ("iverilog", "modelsim"):
                    print(sim)
                    return 2
            else:
                setup = sim_iverilog(tmp, params) if sim == "iverilog" else sim_modelsim(tmp, params)
                if setup not in ("iverilog", "modelsim"):
                    print(setup)

            out = run_sim(sim, tmp, params, stim, outp)
            if "FAIL" in out or "PASS color_target" not in out:
                print(f"FAIL  {name}  [仿真台断言]\n      " + out.strip().replace("\n", "\n      "))
                continue

            got = []
            if outp.exists():
                for line in outp.read_text().splitlines():
                    if line.strip():
                        got.append([int(v) for v in line.split()])
            want = [[e["session"], e["frame"], e["valid"], e["present"], e["cls"],
                     e["count"], e["xmin"], e["xmax"], e["ymin"], e["ymax"],
                     e["cx"], e["cy"]] for e in expect]
            if got != want:
                print(f"FAIL  {name}  [结果与模型不符]")
                print(f"      got  = {got}")
                print(f"      want = {want}")
                continue
            passed += 1
            print(f"PASS  {name}  (published={len(want)})")

    print(f"\n{passed}/{total} 用例通过  [sim={args.sim}]")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
