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

DEFAULTS = dict(target_class=0, hue_half_width_deg=30, c_min=24, v_min=32,
                min_count=4, xw=11, yw=10)

RED = (230, 30, 30)
WHITE = (200, 200, 200)
ORANGE = (250, 150, 40)      # hue 31.43°，偏出默认 ±30 度窗口
# 下面两个各**只**踩一条门限，取值是按判据反推的——原先的 (200,170,170)/(60,12,12)
# 其实三条门限都过得去（C=30 与 C=48 都 >= C_MIN=24），名字叫"低彩/亮度低"却根本没测到
# 那两条门限，注释"都不应计入"与事实相反。这里是订正后的取值：
PINK = (200, 180, 180)       # C=20 < C_MIN=24：只踩彩度门限
DARKRED = (28, 2, 2)         # C=26 >= 24 但 max=28 < V_MIN=32：只踩亮度门限


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
    """返回 [(名称, beats, 该用例的参数覆盖[, 硬编码期望])]。

    第 4 项可选：一组**不经过参考模型**直接写死的期望结果行
    （与转储同格式：[session, frame, valid, present, cls, count, xmin, xmax,
      ymin, ymax, cx, cy]）。审查意见明确要求关键用例"期望值应根据数学判据
    独立计算"或直接按意见给出——这类期望由人手写，模型与 RTL 一起错也拦得住。
    """
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

    # 复查补的覆盖缺口：此前只在"首拍"中断过，中途中断与"空闲拍中断"两条路径都没测。
    # 中途中断：应同样作废整帧（RTL 的中断标志是帧内粘滞的）。
    mid = make_frame(32, 8, rect, 1, 24)
    mid[len(mid) // 2]["abort"] = 1
    cases.append(("abort_mid_frame", mid, {}))

    # 空闲拍中断 + 紧随一帧正常帧：中断不得泄漏到下一帧（start_f 会重写 aborted_f）。
    leaky = make_frame(32, 8, rect, 1, 25)
    leaky.append(dict(valid=0, sof=0, eol=0, eof=0, abort=1, x0=0, y=0,
                      data96=0, session=0, frame=0))
    cases.append(("abort_on_idle_no_leak",
                  leaky + make_frame(32, 8, rect, 1, 26), {}))

    # 复查发现的参数陷阱：MIN_COUNT=0 曾会让"零命中"的帧也判为存在，并输出中性元包围框
    # （xmin=2047 / xmax=0 → 中心 1023）这类垃圾坐标。RTL 与模型现在都在编译期夹到 1，
    # 本用例锁住这个行为——这一帧全白、零命中，期望 present=0 且坐标全 0。
    cases.append(("mincount_zero_is_clamped",
                  make_frame(8, 2, lambda x, y: WHITE, 1, 27), {"min_count": 0}))

    # 截断帧（不发 eof）后接一帧正常帧：只应发布后者的结果
    trunc = make_frame(16, 4, rect, 1, 17, emit_eof=False)
    ok = make_frame(16, 4, rect, 1, 18)
    cases.append(("truncated_then_ok", trunc + idle(2) + ok, {}))

    # 颜色门限各踩一条：橙偏出色相窗、粉彩度不足、暗红亮度不足，都不应计入。
    # 期望值硬编码：valid=1（帧本身正常）但 present=0、计数与坐标全 0（协议 §4.3）。
    no_target = lambda sess, fid: [[sess, fid, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]]
    cases.append(("orange_out_of_hue",
                  make_frame(8, 2, lambda x, y: ORANGE, 1, 19), {}, no_target(1, 19)))
    cases.append(("low_chroma",
                  make_frame(8, 2, lambda x, y: PINK, 1, 20), {}, no_target(1, 20)))
    cases.append(("dark_red",
                  make_frame(8, 2, lambda x, y: DARKRED, 1, 21), {}, no_target(1, 21)))

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

    # —— 审查意见②：上一帧被中止后，紧跟一帧**正常**的单拍全红帧 ——
    # 缺陷：eff_abort 写成 aborted_f | I_frame_abort，上一帧遗留的 aborted_f 会泄漏进
    # 新帧；当新帧是"sof 与 eof 同拍"的单拍帧时，整帧结果被错误作废（valid=0）。
    # 多拍帧侥幸没事（start_f 那一拍就把 aborted_f 清掉了，而那一拍不发布结果），
    # 单拍帧的 sof 与 eof 是同一拍，于是直接踩中。
    # 期望值按审查意见**硬编码**，不经过模型：valid=1、present=1、count=4。
    # 单拍全红帧 4x1：4 个像素全命中 → count=4，x 0..3、y 0，中心 (1,0)。
    after_abort = (make_frame(32, 8, rect, 2, 89, abort=True) + idle(2)
                   + make_frame(4, 1, lambda x, y: RED, 3, 90))
    cases.append(("abort_then_single_beat_ok", after_abort, {"min_count": 1},
                  [[2, 89, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                   [3, 90, 1, 1, 0, 4, 0, 3, 0, 0, 1, 0]]))

    # 反向用例：单拍帧**自己**被中止时仍必须作废。
    # 防止②的修复矫枉过正——把"sof 同拍的中止"这条合法路径也一起放过。
    single_abort = make_frame(4, 1, lambda x, y: RED, 3, 91)
    single_abort[0]["abort"] = 1
    cases.append(("single_beat_aborted_still_void", single_abort, {"min_count": 1},
                  [[3, 91, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]))

    # —— 参数合法范围：越界值必须被编译期夹取，不能变成静默失效 ——
    # MIN_COUNT 上界 2^20-1：不夹的话 2^20 会被 [19:0] 截成 0，本意"严到不可能命中"
    # 反变成"零命中也算存在"。这里给一整帧全红（4 命中），期望仍是 present=0。
    cases.append(("mincount_over_20bit_is_clamped",
                  make_frame(4, 1, lambda x, y: RED, 1, 30), {"min_count": 1 << 20},
                  [[1, 30, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]]))

    # XW=2 / YW=2：旧实现在这里直接**编译失败** —— 拍内 x0+k 的显式零扩展写成
    # {{(XW-3){1'b0}}, ...}，XW<3 时是负数重复次数。去掉那个多余扩展后，任意 XW>=1
    # 都能编译，坐标按位宽自然截断。4x4 画面、左上 2x2 红块 -> 4 命中，框 0..1 / 0..1，中心 (0,0)。
    def tiny_block(x, y):
        return RED if (x <= 1 and y <= 1) else WHITE
    cases.append(("tiny_geometry_xw2_yw2",
                  make_frame(4, 4, tiny_block, 1, 31), {"xw": 2, "yw": 2, "min_count": 1},
                  [[1, 31, 1, 1, 0, 4, 0, 1, 0, 1, 0, 0]]))

    # XW=3 / YW=2（旧实现同样编译失败）：8x4 画面、左上 4x2 红块 -> 8 命中，框 0..3 / 0..1，中心 (1,0)
    def small_block(x, y):
        return RED if (x <= 3 and y <= 1) else WHITE
    cases.append(("small_geometry_xw3_yw2",
                  make_frame(8, 4, small_block, 1, 32), {"xw": 3, "yw": 2},
                  [[1, 32, 1, 1, 0, 8, 0, 3, 0, 1, 1, 0]]))

    # 跨帧身份：两帧不同 session/frame，结果必须各自对应
    f1 = make_frame(8, 2, rect, 7, 100)
    f2 = make_frame(8, 2, rect, 7, 101)
    cases.append(("frame_id_propagation", f1 + idle(2) + f2, {}))

    # A completed EOF must close the frame. A repeated EOF without SOF must
    # never republish the previous count as a fresh valid result. Hard-coded
    # independently of the reference model; recovery still starts a new frame.
    good = make_frame(4, 1, lambda x, y: RED, 9, 199)
    stray = make_frame(4, 1, lambda x, y: RED, 9, 199)
    stray[0]["sof"] = 0
    recovery = make_frame(4, 1, lambda x, y: RED, 9, 200)
    cases.append(("stray_eof_after_complete_frame", good + stray + recovery, {},
                  [[9,199,1,1,0,4,0,3,0,0,1,0],
                   [9,199,0,0,0,0,0,0,0,0,0,0],
                   [9,200,1,1,0,4,0,3,0,0,1,0]]))

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


def main():
    ap = argparse.ArgumentParser()
    simlib = _simlib()
    simlib.add_args(ap)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--case", help="run one named regression")
    ap.add_argument("--rtl", type=Path, help="alternate detector RTL for negative controls")
    args = ap.parse_args()

    model = load_model()
    cases = build_cases(DEFAULTS)
    if args.full:
        cases += extra_full_frame(DEFAULTS)
    if args.case:
        cases = [c for c in cases if c[0] == args.case]
        if not cases: raise ValueError("Unknown case: " + args.case)

    total = passed = 0
    for case in cases:
        name, beats, over = case[0], case[1], case[2]
        hard = case[3] if len(case) > 3 else None
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
            ok, out, err = simlib.simulate(
                srcs=[RTL / "color_classify.v", args.rtl or RTL / "color_target_detect.v",
                      TB / "tb_color_target.v"],
                tb_top="tb_color_target", params=params,
                plusargs=dict(STIM=stim.as_posix(), OUT=outp.as_posix()),
                requested=args.sim, msim_root=args.msim, workdir=tmp, name="ct")
            if not ok:
                print(f"FAIL  {name}  [仿真]\n      " + err.strip().replace("\n", "\n      "))
                return 2
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
            # 先比硬编码期望：它是"不依赖模型"的那一份，出问题时最该先被看到
            if hard is not None and got != hard:
                print(f"FAIL  {name}  [硬编码期望不符，未经模型]")
                print(f"      got  = {got}")
                print(f"      want = {hard}")
                continue
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
