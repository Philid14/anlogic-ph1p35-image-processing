"""color_target_text_overlay 的独立自检：生成激励 -> 仿真 -> 逐像素比对。

比对对象是 model/ref_color_target_text.py，但**关键结论不依赖它**：
  · 十进制转换：模型用 Python 的十进制格式化，RTL 用双-dabble——两套独立实现；
  · 字符内容：直接按 Python 拼出的字符串（`f"{v:06d}"`）核对 RTL 请求到的字符；
  · 区域外：RTL 必须一个像素都不覆盖（这条只看转储本身）。

字形是桩（stub），不是 MAIN 的 osd_char_lib：本模块不实例化字库，字库由 MAIN 统一维护。

用法：
    python features/color_target/run_color_target_text_overlay.py
    python features/color_target/run_color_target_text_overlay.py --sim modelsim
"""

import argparse
import importlib.util
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RTL = HERE / "rtl"
TB = HERE / "tb"

TB_NAME = "tb_color_target_text_overlay"
MOD_NAME = "color_target_text_overlay"


def _simlib():
    spec = importlib.util.spec_from_file_location("ct_simlib", HERE / "tools" / "simlib.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_model():
    spec = importlib.util.spec_from_file_location(
        "ref_ct_text", HERE / "model" / "ref_color_target_text.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------------------
# 用例：(名称, state, count, cx, cy, show, 参数覆盖, 触发方式)
# 数值刻意覆盖十进制进位边界与饱和边界——这些正是"不用除法器的转换"最容易错的地方。
# ---------------------------------------------------------------------------
BOUNDARY_VALUES = [
    (0, 0, 0), (1, 0, 0), (9, 9, 9), (10, 10, 10), (99, 99, 99), (100, 100, 100),
    (999, 999, 999), (1000, 1000, 0), (9999, 1279, 719), (99999, 5, 6),
    (100000, 1279, 0), (921600, 640, 360), (999999, 1, 1),
    (1000000, 1279, 719),            # count 超显示位数 -> 饱和成 999999
    (1048575, 2047, 1023),           # 20 位满量程 + y 超三位 -> 都饱和
]
# 注意：cx/cy 的饱和只有在位宽足够宽时**才可达**——XW=11 最大 2047，永远到不了 9999。
# 所以 x 的饱和要用一条 XW=14 的用例来测（否则测的是测试台自己的截断，不是 RTL 的饱和）。


def build_cases():
    cases = []
    cases.append(("basic_track", 2, 3600, 512, 340, 1, {}, "pulse"))
    cases.append(("track_dimmed", 2, 3600, 512, 340, 0, {}, "pulse"))
    cases.append(("state_search", 0, 0, 0, 0, 0, {}, "pulse"))
    cases.append(("state_acq", 1, 123, 7, 8, 0, {}, "pulse"))
    cases.append(("state_hold", 3, 45678, 1000, 500, 1, {}, "pulse"))
    # I_update 全程为 0：只靠"输入变化"触发转换（MAIN 不接 I_update 时的路径）
    cases.append(("no_update_pin", 2, 654321, 1279, 719, 1, {}, "none"))
    # 放大一档：字符格 32x32（与主线 edge_status_osd 同规格）
    cases.append(("scale2", 2, 3600, 512, 340, 1, {"scale": 2}, "pulse"))
    # 区域换到右上（MAIN 可以任意改）
    cases.append(("region_top_right", 2, 111, 222, 33, 1,
                  {"x0": 800, "y0": 16}, "pulse"))
    # 关掉整个模块
    cases.append(("disabled", 2, 3600, 512, 340, 1, {"enable": 0}, "pulse"))
    # 十进制边界与饱和：每次换一组数值，靠"输入变化"触发（update 只给一次）
    for i, (c, x, y) in enumerate(BOUNDARY_VALUES):
        cases.append((f"dec_{i}_{c}_{x}_{y}", 2, c, x, y, 1, {}, "pulse"))
    # 单行更短/更长也要能对上
    cases.append(("chars_10", 2, 3600, 512, 340, 1, {"line_chars": 10}, "pulse"))
    cases.append(("chars_20", 2, 3600, 512, 340, 1, {"line_chars": 20}, "pulse"))
    # 更宽的坐标位宽：这时 cx 才可能超过 9999，x 的饱和显示才真的可达
    cases.append(("x_saturate_xw14", 2, 3600, 16000, 340, 1, {"xw": 14}, "pulse"))
    cases.append(("y_saturate_yw12", 2, 3600, 512, 2000, 1, {"yw": 12}, "pulse"))
    return cases


def geom_of(model, ov):
    p = dict(model.TEXT_DEFAULTS, **ov)
    _s, _l, cell, gap, reg_w, reg_h = model.geom(p)
    return p, cell, gap, reg_w, reg_h


def build_stim(model, case):
    """返回 (行列表, 本用例要核对的像素列表)。

    每行 9 字段：valid x y update show state count cx cy
    结构：先 110 拍沉降（valid=0，让十进制转换跑完），再扫区域内外若干像素。
    """
    _name, state, count, cx, cy, show, ov, mode = case
    p, cell, gap, reg_w, reg_h = geom_of(model, ov)
    x0, y0 = p["x0"], p["y0"]
    xw, yw = ov.get("xw", 11), ov.get("yw", 10)
    rows = []
    upd_first = 1 if mode == "pulse" else 0
    for i in range(110):
        rows.append((0, x0, y0, upd_first if i == 0 else 0, show, state, count, cx, cy))
    # 扫：区域 + 左右上下各 3 像素余量；再加几个远点确认区域外不覆盖
    xs = list(range(max(0, x0 - 3), x0 + reg_w + 3))
    ys = list(range(max(0, y0 - 3), y0 + reg_h + 3))
    xs += [0, 1, x0 + reg_w + 40]
    ys += [0, 1, y0 + reg_h + 40]
    # 扫点必须落在该用例的位宽能表示的坐标内（否则测的是测试台自己的截断）
    xs = sorted({v for v in xs if v < (1 << xw)})
    ys = sorted({v for v in ys if v < (1 << yw)})
    pixels = [(x, y) for y in ys for x in xs]
    for (x, y) in pixels:
        rows.append((1, x, y, 0, show, state, count, cx, cy))
    return rows, pixels, p


def write_stim(path, rows):
    with open(path, "w", encoding="ascii") as f:
        for r in rows:
            f.write("%d %d %d %d %d %d %d %d %d\n" % r)


def main():
    ap = argparse.ArgumentParser()
    simlib = _simlib()
    simlib.add_args(ap)
    ap.add_argument("--only", default=None, help="只跑名字里含该子串的用例")
    ap.add_argument("--font", default="auto", choices=["auto", "stub", "real"],
                    help="字形来源：auto=有主线字库就用真字库（默认），stub=只用桩，real=强制真字库")
    ap.add_argument("--font-path", default=None, help="主线 osd_char_lib.v 的路径")
    args = ap.parse_args()

    model = load_model()

    # 字形来源：真字库能把"字形位索引约定"也验掉，所以默认优先用它；
    # 拿不到时退回桩并明确打印（不静默换实现）。
    glyph_fn, font_srcs = None, [TB / "ct_text_font_stub.v"]
    font_path = model.find_font(args.font_path)
    use_real = (args.font == "real") or (args.font == "auto" and font_path)
    if use_real and not font_path:
        print("FAIL  --font real 但找不到主线字库（用 --font-path 指定）")
        return 2
    if use_real:
        glyphs = model.parse_font(font_path)
        glyph_fn = model.make_font_bit(glyphs)
        font_srcs = [TB / "ct_text_font_real.v", font_path]
        print(f"[字形] 用主线真字库：{font_path}（解析到 {len(glyphs)} 条 (字符,行) 记录）")
    else:
        print("[字形] 用桩 ct_text_font_stub.v（没找到主线字库或指定了 --font stub）")

    cases = [c for c in build_cases() if not args.only or args.only in c[0]]

    total = passed = 0
    n_px_total = 0
    for case in cases:
        name = case[0]
        rows, pixels, p = build_stim(model, case)
        total += 1
        params = dict(XW=case[6].get("xw", 11), YW=case[6].get("yw", 10),
                      ENABLE=p["enable"], X0=p["x0"], Y0=p["y0"],
                      SCALE=p["scale"], LINE_CHARS=p["line_chars"],
                      TEXT_RGB=p["text_rgb"], DIM_RGB=p["dim_rgb"], BG_RGB=p["bg_rgb"])
        with tempfile.TemporaryDirectory(prefix="cttxt-") as td:
            tmp = Path(td)
            stim, outp = tmp / "stim.txt", tmp / "dut.txt"
            write_stim(stim, rows)
            ok, out, err = simlib.simulate(
                srcs=[RTL / "color_target_text_overlay.v"] + font_srcs
                     + [TB / "tb_color_target_text_overlay.v"],
                tb_top=TB_NAME, params=params,
                plusargs=dict(STIM=stim.as_posix(), OUT=outp.as_posix()),
                requested=args.sim, msim_root=args.msim, workdir=tmp, name="txt")
            if not ok:
                print(f"FAIL  {name}  [仿真]\n      " + err.strip().replace("\n", "\n      "))
                return 2
            if "FAIL" in out or f"PASS {MOD_NAME}" not in out:
                print(f"FAIL  {name}  [仿真台]\n      " + out.strip().replace("\n", "\n      "))
                continue

            got = {}
            if outp.exists():
                for ln in outp.read_text().splitlines():
                    if ln.strip():
                        xs, ys, ov_v, rgb, ch, grow = ln.split()
                        got[(int(xs), int(ys))] = (int(ov_v), int(rgb, 16),
                                                   int(ch), int(grow))
            if len(got) != len(pixels):
                print(f"FAIL  {name}  [转储行数] {len(got)} != 期望 {len(pixels)}")
                continue

            # ---- 1) 逐像素与模型比对 ----
            # 只在 overlay_valid=1 时比颜色/字符：区域外 RTL 仍驱动着组合输出（无意义但确定），
            # 消费方（MAIN 的 mixer）也只看 overlay_valid。"区域外必须不覆盖"另有一条独立断言。
            line0, line1 = model.text_lines(case[1], case[2], case[3], case[4], p)
            bad = []
            for (x, y) in pixels:
                wv, wrgb, wch, wrow = model.overlay_pixel(x, y, line0, line1, case[5], p,
                                                          glyph_fn=glyph_fn)
                g = got[(x, y)]
                if g[0] != wv:
                    bad.append(((x, y), g, (wv, wrgb, wch, wrow)))
                elif wv and g != (wv, wrgb, wch, wrow):
                    bad.append(((x, y), g, (wv, wrgb, wch, wrow)))
            if bad:
                print(f"FAIL  {name}  [与模型不符]  {len(bad)}/{len(pixels)} 像素")
                for px, g, w in bad[:5]:
                    print(f"      像素{px}: got=(ov={g[0]} rgb=0x{g[1]:06x} ch={chr(g[2])!r} "
                          f"row={g[3]})  want=(ov={w[0]} rgb=0x{w[1]:06x} "
                          f"ch={chr(w[2])!r} row={w[3]})")
                continue

            # ---- 2) 区域外必须一个像素都不覆盖（只看转储，不依赖模型）----
            _s, _l, cell, gap, reg_w, reg_h = model.geom(p)
            outside = [(x, y) for (x, y) in pixels
                       if not (p["x0"] <= x < p["x0"] + reg_w
                               and p["y0"] <= y < p["y0"] + reg_h)]
            leak = [(x, y) for (x, y) in outside if got[(x, y)][0]]
            if leak:
                print(f"FAIL  {name}  [区域外泄漏] {len(leak)} 个像素被覆盖，例如 {leak[:4]}")
                continue
            if not p["enable"] and any(got[px][0] for px in pixels):
                print(f"FAIL  {name}  [ENABLE=0 却仍有覆盖]")
                continue

            # ---- 3) 字符内容：直接按 Python 拼的字符串核对 RTL 请求到的字符 ----
            # 取每个字符格的左上角像素，它对应该格的第 0 列第 0 行
            wrong = []
            if p["enable"]:
                step_y = cell + gap
                for lineno, want_line in ((0, line0), (1, line1)):
                    ty = p["y0"] + (step_y if lineno else 0)
                    for col in range(p["line_chars"]):
                        tx = p["x0"] + col * cell
                        g = got.get((tx, ty))
                        if g is None:
                            continue
                        want_ch = ord(want_line[col]) if col < len(want_line) else 0x20
                        if g[2] != want_ch or g[3] != 0:
                            wrong.append((lineno, col, tx, ty, g, want_ch))
            if wrong:
                print(f"FAIL  {name}  [字符内容不符]  {len(wrong)} 处")
                for lineno, col, tx, ty, g, want_ch in wrong[:6]:
                    print(f"      第{lineno}行第{col}列 @({tx},{ty}): "
                          f"got={chr(g[2])!r}(row={g[3]}) want={chr(want_ch)!r}")
                continue

            passed += 1
            n_px_total += len(pixels)
            print(f"PASS  {name}  (pixels={len(pixels)}  \"{line0.strip()}\" / \"{line1.strip()}\")")

    print(f"\n{passed}/{total} 用例通过，共 {n_px_total} 像素逐点比对  [sim={args.sim}]")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
