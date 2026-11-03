"""color_classify 的参数化自检 —— **期望值按数学判据独立计算**，不经过 model/。

为什么单独成文件（复查发现的覆盖缺口）：原来的回归只在默认参数
（HUE_HALF_WIDTH_DEG=30）下跑了几组颜色，所以"小色相半宽下乘积被截断"
这个缺陷（缺陷①）长期没有被任何用例覆盖。本文件做三件事：
  1. 把 W 扫过 0..60 的多个取值（外加 90 用来验证夹取）；
  2. 把 C_MIN / V_MIN 也推到判据边界（取等号的两侧各测一次）；
  3. 每个参数组合喂一整张 RGB 网格 + 一组手算边界像素，逐像素比对。

**期望值不来自 model/ref_color_target.py**：判据在下面 criterion() 里重写了一遍
（第三份独立实现），所以"RTL 与模型一起错"这种情形在这里也能暴露。

判据（W = hue 半宽，单位度；d = 另两个通道之差的绝对值；C = max-min）：
    hit = (目标通道为最大) and (60*|d| <= W*C) and (C >= C_MIN) and (max >= V_MIN)
W 夹到 0..60、C_MIN 夹到 0..511、V_MIN 夹到 0..255，TARGET_CLASS 除 1/2 外一律按红
——都与 RTL 的编译期夹取逐条对应。**是夹取不是位截断**：这四类越界参数原先会让判据
静默失效（例如 C_MIN=512 被低 9 位截成 0，"严到不可能命中"变成"完全不滤彩度"）。

用法：
    python features/color_target/run_color_classify.py
    python features/color_target/run_color_classify.py --sim modelsim
    python features/color_target/run_color_classify.py --locked-only   # 只跑手算用例，最快
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


# 网格取样点：刻意跳过 2 的幂之间的规律性，兼顾 0/1/255 这类极端
GRID_VALS = [0, 1, 3, 7, 15, 31, 63, 127, 191, 255]


def w_eff(w):
    """与 RTL 的 W_DEG 夹取一致。"""
    return 0 if w < 0 else (60 if w > 60 else w)


def c_min_eff(v):
    """与 RTL 的 CMIN_D 夹取一致（0..511）。"""
    return 0 if v < 0 else (511 if v > 511 else v)


def v_min_eff(v):
    """与 RTL 的 VMIN_D 夹取一致（0..255）。"""
    return 0 if v < 0 else (255 if v > 255 else v)


def criterion(r, g, b, tc, w, c_min, v_min):
    """数学判据的独立实现（不调用 model/）。返回值 0/1。

    位宽与 RTL 对齐：C_MIN 按 9 位、V_MIN 按 8 位参与比较，超出即按**夹取**语义
    （不是位截断——夹取与截断在越界时结果相反，下方锁定用例专门钉住这一点）。
    TARGET_CLASS 除 1/2 外一律按红处理（与 RTL 的 generate 一致）。
    """
    mx, mn = max(r, g, b), min(r, g, b)
    chroma = mx - mn
    if tc == 1:
        sel, d = (g > r) and (g >= b), abs(r - b)
    elif tc == 2:
        sel, d = (b > r) and (b > g), abs(r - g)
    else:
        sel, d = (r >= g) and (r >= b), abs(g - b)
    return int(bool(sel and (60 * d <= w_eff(w) * chroma)
                    and (chroma >= c_min_eff(c_min)) and (mx >= v_min_eff(v_min))))


# ---------------------------------------------------------------------------
# 手算锁定用例：期望值由上面判据**手工推导**（每条 why 里写了算式），
# 先说清"期望为什么是这个数"，再看 RTL 是否给出同一个数。
# 同时会断言手算值 == criterion()，两者不一致说明判据实现或手算有错，直接报错。
# ---------------------------------------------------------------------------
LOCKED = [
    # (tc, w, c_min, v_min, (r,g,b), exp, why)
    (0, 10, 24, 32, (255, 200, 0), 0, "hue=60*200/255=47.06° > 10°；缺陷①在此被截断误判为红"),
    (0, 47, 24, 32, (255, 200, 0), 0, "同上：60*200=12000 > 47*255=11985"),
    (0, 48, 24, 32, (255, 200, 0), 1, "同上：12000 <= 48*255=12240，紧邻上一条锁定判据边界"),
    (0, 10, 24, 32, (255, 42, 0), 1, "hue=60*42/255=9.88° <= 10°"),
    (0, 10, 24, 32, (255, 43, 0), 0, "hue=60*43/255=10.12° > 10°，W=10 的另一侧边界"),
    (0, 0, 24, 32, (255, 0, 0), 1, "W=0：纯红 d=0，是唯一被允许的色相"),
    (0, 0, 24, 32, (255, 1, 0), 0, "W=0：d=1 → 60 > 0"),
    (0, 15, 24, 32, (255, 1, 0), 1, "hue=60/255=0.235° <= 15°"),
    (0, 60, 24, 32, (255, 255, 0), 1, "黄正好 60°：W 夹到 60 后 15300<=15300 取等号成立"),
    (0, 59, 24, 32, (255, 255, 0), 0, "W=59：60*255=15300 > 59*255=15045"),
    (0, 30, 24, 32, (255, 255, 255), 0, "白：C=0 < C_MIN"),
    (0, 30, 24, 32, (128, 128, 128), 0, "灰：C=0 < C_MIN"),
    (0, 30, 0, 32, (128, 128, 128), 1, "C_MIN=0 的退化语义：灰的 C=0>=0 且 d=0，按判据命中"),
    (0, 30, 24, 32, (100, 76, 76), 1, "C=24 恰等于 C_MIN=24（判据含等号）"),
    (0, 30, 25, 32, (100, 76, 76), 0, "C_MIN=25：C=24 不达"),
    (0, 30, 24, 32, (32, 8, 8), 1, "max=32 恰等于 V_MIN=32"),
    (0, 30, 24, 33, (32, 8, 8), 0, "V_MIN=33：max=32 不达"),
    (0, 30, 24, 32, (250, 150, 40), 0, "橙：hue=60*110/210=31.43° > 30°"),
    (0, 32, 24, 32, (250, 150, 40), 1, "60*110=6600 <= 32*210=6720"),
    (0, 31, 24, 32, (250, 150, 40), 0, "60*110=6600 > 31*210=6510"),
    (0, 30, 24, 32, (255, 0, 255), 0, "品红：红通道并列最大，但 hue 偏移 60°"),
    (2, 30, 24, 32, (255, 0, 255), 0, "品红不算蓝：sel_max_b 要求 b 严格大于 r，并列时判红（分类互斥）"),
    (1, 30, 24, 32, (30, 220, 40), 1, "绿：d=|r-b|=10，C=190"),
    (0, 30, 24, 32, (30, 220, 40), 0, "同一像素在红色类下：r 不是最大通道"),
    (2, 30, 24, 32, (30, 40, 220), 1, "蓝：d=|r-g|=10，C=190"),
    (2, 30, 24, 32, (220, 30, 40), 0, "红在蓝色类下：b 不是最大通道"),

    # —— 越界参数：必须是"夹取"，不能是"位截断"。下面四条都刻意构造成两种语义结果相反，
    #    所以它们能真正区分"我夹了"和"我让低位截断了"。——
    (0, 30, 512, 32, (128, 128, 128), 0,
     "C_MIN=512 夹到 511；灰的 C=0 < 511 → 否。若按位截断则 512→0，会判成命中，方向正好相反"),
    (0, 30, -1, 32, (128, 128, 128), 1,
     "C_MIN=-1 夹到 0；灰的 C=0>=0 且 d=0 → 是。若按位截断则 -1→511，会判成否"),
    (0, 30, 24, 300, (200, 40, 40), 0,
     "V_MIN=300 夹到 255；max=200 < 255 → 否。若按位截断则 300→44，200>=44 会判成命中"),
    (0, 30, 24, -1, (30, 6, 6), 1,
     "V_MIN=-1 夹到 0；C=24 达标、max=30>=0 → 是。若按位截断则 -1→255，会判成否"),
    (3, 30, 24, 32, (200, 40, 40), 1,
     "TARGET_CLASS=3 按红处理（与 RTL 的 generate 一致），不是'选不中任何类'的静默失效"),
]

# ---------------------------------------------------------------------------
# 参数扫描组合
# ---------------------------------------------------------------------------
SWEEP_W = [0, 1, 2, 5, 10, 15, 25, 30, 31, 32, 45, 47, 48, 59, 60, 90]

# 阈值边界组合（tc, w, c_min, v_min）
THRESH_COMBOS = [
    (0, 30, 0, 32), (0, 30, 1, 32), (0, 30, 24, 33), (0, 30, 24, 0),
    (0, 30, 255, 32), (0, 30, 511, 32), (0, 10, 64, 64), (0, 10, 0, 0),
    (0, 30, 24, 255), (0, 30, 24, 1),
    # 越界：验证是"夹取"而不是"位截断"（夹到上/下界，不是丢掉低位）
    (0, 30, 512, 32), (0, 30, -1, 32), (0, 30, 24, 300), (0, 30, 24, -1),
]

# 三个目标类各自扫一遍（含小半宽），确认剪枝没有串类；3 与 7 是越界值，
# 应与红（0）逐像素完全一致（见下方 EQUIV 的等价性断言）。
CLASS_COMBOS = [(1, 30, 24, 32), (1, 10, 24, 32), (2, 30, 24, 32), (2, 10, 24, 32),
                (1, 60, 24, 32), (2, 60, 24, 32),
                (3, 30, 24, 32), (3, 10, 24, 32), (7, 30, 24, 32)]

# 参数组合等价性断言（不依赖判据、也不依赖模型）：左边的参数应与右边逐像素完全一致。
# 用在"越界值应当退化到合法值"和"夹取后应当与显式取值等价"两类情形上。
EQUIV = [
    ((3, 30, 24, 32), (0, 30, 24, 32), "TARGET_CLASS=3 应当与红(0)完全一致"),
    ((3, 10, 24, 32), (0, 10, 24, 32), "TARGET_CLASS=3 在小半宽下也应与红(0)一致"),
    ((7, 30, 24, 32), (0, 30, 24, 32), "TARGET_CLASS=7 应当与红(0)完全一致"),
    ((0, 60, 24, 32), (0, 90, 24, 32), "W=90 夹到 60，应与显式 60 完全一致"),
    ((0, 30, 512, 32), (0, 30, 511, 32), "C_MIN=512 夹到 511，应与显式 511 完全一致"),
    ((0, 30, -1, 32), (0, 30, 0, 32), "C_MIN=-1 夹到 0，应与显式 0 完全一致"),
    ((0, 30, 24, 300), (0, 30, 24, 255), "V_MIN=300 夹到 255，应与显式 255 完全一致"),
    ((0, 30, 24, -1), (0, 30, 24, 0), "V_MIN=-1 夹到 0，应与显式 0 完全一致"),
]


def build_combos(locked_only=False):
    """返回 {参数元组: [像素列表]}，参数元组 = (tc, w, c_min, v_min)。"""
    combos = {}

    def add(combo, pixels):
        combos.setdefault(combo, [])
        combos[combo].extend(pixels)

    if not locked_only:
        grid = [(r, g, b) for r in GRID_VALS for g in GRID_VALS for b in GRID_VALS]
        for w in SWEEP_W:
            add((0, w, 24, 32), grid)
            add((0, w, 24, 32), [(255, 200, 0), (250, 150, 40), (255, 255, 0)])
        for c in THRESH_COMBOS:
            add(c, grid)
        for c in CLASS_COMBOS:
            add(c, grid)

    # 手算用例的像素必须真的进到对应组合里被仿真
    for tc, w, cmin, vmin, px, _exp, _why in LOCKED:
        add((tc, w, cmin, vmin), [px])

    return combos


def check_locked():
    """先自检手算期望与判据实现一致 —— 不一致说明其中一方有错，直接失败。"""
    bad = []
    for tc, w, cmin, vmin, px, exp, why in LOCKED:
        got = criterion(px[0], px[1], px[2], tc, w, cmin, vmin)
        if got != exp:
            bad.append((tc, w, cmin, vmin, px, exp, got, why))
    return bad


def write_stim(path, pixels):
    with open(path, "w", encoding="ascii") as f:
        for (r, g, b) in pixels:
            f.write("%d %d %d\n" % (r, g, b))


def run_combo(simlib, args, combo, pixels, tmp):
    tc, w, cmin, vmin = combo
    stim, outp = tmp / "stim.txt", tmp / "dut.txt"
    write_stim(stim, pixels)
    ok, out, err = simlib.simulate(
        srcs=[RTL / "color_classify.v", TB / "tb_color_classify.v"],
        tb_top="tb_color_classify",
        params=dict(TARGET_CLASS=tc, HUE_HALF_WIDTH_DEG=w, C_MIN=cmin, V_MIN=vmin),
        plusargs=dict(STIM=stim.as_posix(), OUT=outp.as_posix()),
        requested=args.sim, msim_root=args.msim, workdir=tmp,
        name=f"cls_{tc}_{w}_{cmin}_{vmin}")
    if not ok:
        return None, err
    if "FAIL" in out or "PASS color_classify" not in out:
        return None, "仿真台断言失败：\n" + out.strip()
    if not outp.exists():
        return None, "没有输出文件"
    got = []
    for line in outp.read_text().splitlines():
        s = line.strip()
        if s:
            # 非 0/1 的转储（例如未定态 x）当成"失配值"，而不是让 int() 抛异常中断整轮回归
            got.append(int(s) if s.lstrip("-").isdigit() else None)
    return got, None


def main():
    ap = argparse.ArgumentParser()
    simlib = _simlib()
    simlib.add_args(ap)
    ap.add_argument("--locked-only", action="store_true",
                    help="只跑手算锁定用例所在的参数组合（最快，用于快速回归）")
    args = ap.parse_args()

    bad = check_locked()
    if bad:
        print("FAIL 手算期望与判据实现不一致（先修这个，否则后面全无意义）：")
        for tc, w, cmin, vmin, px, exp, got, why in bad:
            print(f"      tc={tc} w={w} cmin={cmin} vmin={vmin} px={px} "
                  f"手算={exp} 判据={got}  ({why})")
        return 2
    print(f"PASS 手算锁定用例自检 {len(LOCKED)} 条（手算值 == 判据实现）")

    combos = build_combos(locked_only=args.locked_only)
    total_px = sum(len(v) for v in combos.values())
    print(f"      参数组合 {len(combos)} 个，待检像素 {total_px} 个")

    n_combo = n_px = 0
    bad_combos = []
    dumps = {}                      # combo -> 该组合的逐像素转储，供 EQUIV 等价性断言使用
    with tempfile.TemporaryDirectory(prefix="ct-cls-") as td:
        tmp = Path(td)
        for combo in sorted(combos):
            pixels = combos[combo]
            tc, w, cmin, vmin = combo
            n_combo += 1
            got, err = run_combo(simlib, args, combo, pixels, tmp)
            if got is None:
                print(f"FAIL  tc={tc} w={w} cmin={cmin} vmin={vmin}\n      "
                      + err.strip().replace("\n", "\n      "))
                return 2
            if len(got) != len(pixels):
                print(f"FAIL  tc={tc} w={w} cmin={cmin} vmin={vmin}  "
                      f"输出行数 {len(got)} != 激励行数 {len(pixels)}")
                return 2
            dumps[combo] = (pixels, got)
            mism = [(px, g, criterion(px[0], px[1], px[2], tc, w, cmin, vmin))
                    for px, g in zip(pixels, got)
                    if g != criterion(px[0], px[1], px[2], tc, w, cmin, vmin)]
            if mism:
                print(f"FAIL  tc={tc} w={w} cmin={cmin} vmin={vmin}  "
                      f"失配 {len(mism)}/{len(pixels)}")
                for px, g, e in mism[:6]:
                    print(f"      RGB={px} RTL={g} 判据={e} "
                          f"(C={max(px)-min(px)} d 见判据)")
                bad_combos.append((combo, len(mism), len(pixels)))
                continue
            n_px += len(pixels)
            print(f"PASS  tc={tc} w={w} cmin={cmin} vmin={vmin}  pixels={len(pixels)}")

    # —— 参数组合等价性：不依赖判据、也不依赖模型，直接比两次 RTL 运行的转储 ——
    # 缺任何一侧都算测试脚手架故障（而不是静默跳过），否则一个笔误就能让断言蒸发。
    n_equiv = n_equiv_skip = 0
    for lhs, rhs, why in EQUIV:
        if lhs not in dumps or rhs not in dumps:
            if args.locked_only:
                # --locked-only 只仿真手算用例所在的组合，未覆盖的组合按预期跳过
                n_equiv_skip += 1
                continue
            missing = lhs if lhs not in dumps else rhs
            print(f"FAIL  等价性断言引用了未仿真的参数组合 {missing}（check {lhs} vs {rhs}）")
            return 2
        px_l, got_l = dumps[lhs]
        px_r, got_r = dumps[rhs]
        # 两个组合的激励列表不一定相同（各自还带自己的手算边界像素），所以在**共同像素**
        # 上比较，并把实际比对了多少个像素报出来——"PASS" 不该掩盖它只比了 2 个像素。
        map_l = dict(zip(px_l, got_l))
        map_r = dict(zip(px_r, got_r))
        common = sorted(set(map_l) & set(map_r))
        if not common:
            # --locked-only 每个组合只带自己的手算像素，两侧可能没有交集；按预期跳过。
            # 全量模式下每个组合都含整张网格，没有交集就说明脚手架有问题，按故障处理。
            if args.locked_only:
                n_equiv_skip += 1
                continue
            print(f"FAIL  等价性断言两侧没有共同激励：{lhs} vs {rhs}")
            return 2
        diff = [(px, map_l[px], map_r[px]) for px in common if map_l[px] != map_r[px]]
        if diff:
            print(f"FAIL  等价性 {lhs} vs {rhs}：{why}，但 {len(diff)}/{len(common)} 像素不同")
            for px, a, b in diff[:6]:
                print(f"      RGB={px} 左={a} 右={b}")
            return 1
        n_equiv += 1
        print(f"PASS  等价性 {lhs} == {rhs}（共同 {len(common)} 像素）  {why}")

    n_bad = len(bad_combos)
    print(f"\n{n_combo - n_bad}/{n_combo} 参数组合通过，共 {n_px} 像素逐点比对；"
          f"等价性断言 {n_equiv}/{len(EQUIV) - n_equiv_skip} 通过"
          + (f"（--locked-only 跳过 {n_equiv_skip} 条）" if n_equiv_skip else "")
          + f"  [sim={args.sim}]")
    if n_bad:
        # 不撞到第一个就退出：把全部失配组合都列出来，失败时的证据才是完整的
        print(f"失配组合 {n_bad} 个：")
        for (tc, w, cmin, vmin), m, tot in bad_combos:
            print(f"      tc={tc} w={w} cmin={cmin} vmin={vmin}  失配 {m}/{tot}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
