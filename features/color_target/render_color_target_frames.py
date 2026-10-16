"""把三级链路的**逐像素输出**渲染成 PNG 帧图，并顺带做一次逐像素回归。

这个脚本干两件事：

  1. **回归**：用 tb_color_target_chain_render 跑一条合成的多帧画面序列，逐拍比对
     track 的状态/显示、**逐像素**比对 overlay 的覆盖与合成结果（4 个 lane 全部比对，
     不像 tb_color_target_chain 那样只采 lane0）。比对对象是 model/ 里的链路模型。
  2. **产出**：把 RTL 输出的"合成后像素"写成 PNG，让整条 detect → track → overlay
     的行为可以被**看见**——框在哪里、什么时候出现、什么时候保持、什么时候消失。

跑的是 **XW=9 / YW=8 的 320x240 非默认几何**，顺带证明这三个模块的参数化是真的
（默认参数是 XW=11 / YW=10 的 1280x720）。

⚠️ 画面是**合成**的，不是实拍：几何、颜色、噪声都是按判据构造的。它的用途是
"让行为可见 + 顺带回归"，**不代表上板效果**，也不能当作对摄像头数据的验证。

用法：
    python features/color_target/render_color_target_frames.py
    python features/color_target/render_color_target_frames.py --out D:/somewhere/frames
    python features/color_target/render_color_target_frames.py --scale 2 --width 240
"""

import argparse
import importlib.util
import random
import struct
import sys
import tempfile
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
RTL = HERE / "rtl"
TB = HERE / "tb"

BG = (150, 150, 150)          # 浅灰背景：C=0，不该被判成任何颜色
RED = (230, 30, 30)           # 目标红

STATE_NAMES = ["SEARCH", "ACQ", "TRACK", "HOLD"]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def simlib():
    return _load("ct_simlib", HERE / "tools" / "simlib.py")


def load_chain_model():
    return _load("ref_ct_chain_render", HERE / "model" / "ref_color_target_chain.py")


def load_overlay_model():
    return _load("ref_ct_ovl_render", HERE / "model" / "ref_color_target_overlay.py")


def load_detect_model():
    return _load("ref_ct_det_render", HERE / "model" / "ref_color_target.py")


def load_detect_runner():
    """借它生成激励（make_frame / write_stim / idle 已经写好，没必要复制一份）。"""
    return _load("ct_detect_runner_render", HERE / "run_color_target.py")


# ---------------------------------------------------------------------------
# PNG 输出：只用标准库（zlib + struct），不引第三方依赖
# ---------------------------------------------------------------------------
def write_png(path, width, height, rows):
    """rows 每项是长度 3*width 的 bytes（RGB888，行优先）。"""
    raw = b"".join(b"\x00" + r for r in rows)      # 每行前缀 filter type 0

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


def frame_to_png(pixels, width, height, scale, path):
    """pixels: {(x,y): (r,g,b)} -> PNG（最近邻放大 scale 倍）。"""
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            r, g, b = pixels.get((x, y), (0, 0, 0))
            row += bytes((r, g, b)) * scale
        for _ in range(scale):
            rows.append(bytes(row))
    write_png(path, width * scale, height * scale, rows)


# ---------------------------------------------------------------------------
# 合成画面
# ---------------------------------------------------------------------------
def square_painter(x0, y0, size, color=RED, bg=BG):
    def f(x, y):
        if x0 <= x < x0 + size and y0 <= y < y0 + size:
            return color
        return bg
    return f


def add_specks(base, count, w, h, seed, color=(255, 0, 0)):
    """撒 count 个**孤立单像素**的高饱和点（椒盐噪声）。

    刻意避开目标方块、且彼此不挨着：这样它们才是"背景里的孤立噪点"，用来暴露
    README §5 已知限制 2 —— 无形态学滤波时孤立噪点会把包围框拉大。
    """
    rnd = random.Random(seed)
    specks = set()
    guard = 0
    while len(specks) < count and guard < count * 500:
        guard += 1
        x, y = rnd.randrange(w), rnd.randrange(h)
        if base(x, y) != BG:            # 落在目标上就不算孤立噪点
            continue
        if any((x + dx, y + dy) in specks for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            continue                    # 也别让噪点彼此挨着，否则就不"孤立"了
        specks.add((x, y))

    def f(x, y):
        return color if (x, y) in specks else base(x, y)
    return f


def warm_cast(base, gain_g=4.0, off_g=5, gain_b=0.5):
    """极端白平衡漂移：绿通道被抬起、蓝通道被压低 —— 红目标的 hue 被推成橙。

    RED=(230,30,30) 经此变换 -> (230,125,15)：C=215、d=|G-B|=110，
    hue = 60*110/215 = 30.7 度，刚好越出默认的 ±30 度窗口 —— 于是"红方块明明还在
    画面里，检测却丢了"。这正是 README §5 已知限制 4（强偏色下阈值可能失效）。
    """
    def f(x, y):
        r, g, b = base(x, y)
        return (min(255, int(r)), min(255, int(g * gain_g + off_g)),
                min(255, int(b * gain_b)))
    return f


def build_scene(width, height):
    """返回 [(帧号, 名称, 这一帧想演示什么, 该帧的 painter)]。

    参数取 ACQ_FRAMES=2 / LOST_FRAMES=2，10 帧之内能看全
    "确认 → 跟踪 → 丢失保持 → 彻底失去 → 重现"的完整循环。

    **说明文字按实际语义写**：某一帧画面上的框，来自**上一帧**的检测结果
    （detect 在 eof 之后 1 拍才发布、track 在那一拍消费，所以框在下一帧才生效）。
    这一点在 README §2.4 与 INTERFACE §6 都记着，也是 MAIN 必须在帧边界寄存一级的原因。
    第一版说明按"本帧结果本帧就画"写，与实测转储不符，已按实测订正。
    """
    size = 60
    sx = (width - size) // 2
    sy = (height - size) // 2
    rows = [
        ("frame_01_appear", "目标出现（第 1 帧）：链路还没有任何结果，画面无框",
         square_painter(20, sy, size)),
        ("frame_02_confirm1", "目标移到中间（第 2 帧）：上一帧结果已消费 → ACQ，还差 1 帧，仍无框",
         square_painter(sx, sy, size)),
        ("frame_03_track", "目标移到右侧：确认完成 → TRACK，框出现——框画的是**上一帧**（目标在中间）的位置",
         square_painter(width - size - 20, sy, size)),
        ("frame_04_noise", "目标回到中间 + 椒盐噪声：画面上的框仍是上一帧（目标在右侧）的位置",
         add_specks(square_painter(sx, sy, size), 40, width, height, seed=20261016)),
        ("frame_05_absent1", "目标离开：框来自上一帧——那一帧的孤立噪点把框撑大了（已知限制 2）",
         square_painter(-999, -999, size)),
        ("frame_06_absent2", "继续无目标（第 1 次丢失）→ HOLD：框保持在被噪声撑大的位置",
         square_painter(-999, -999, size)),
        ("frame_07_lost", "第 2 次丢失达 LOST_FRAMES=2 → SEARCH：框消失",
         square_painter(-999, -999, size)),
        ("frame_08_reappear1", "目标重现（第 1 帧）：重新走确认流程，仍无框",
         square_painter(sx, sy, size)),
        ("frame_09_reappear2", "目标重现（第 2 帧）：TRACK，框回来（画的是上一帧的位置）",
         square_painter(sx, sy, size)),
        ("frame_10_cast", "极端白平衡漂移：本帧检测丢失（已知限制 4）；框仍显示上一帧的位置",
         warm_cast(square_painter(sx, sy, size))),
    ]
    return [(i + 1, name, note, painter) for i, (name, note, painter) in enumerate(rows)]


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    sl = simlib()
    sl.add_args(ap)
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--height", type=int, default=240)
    ap.add_argument("--scale", type=int, default=3, help="PNG 最近邻放大倍数")
    ap.add_argument("--out", default=None,
                    help="PNG 输出目录；默认写到系统临时目录（不往仓库里写生成物）")
    ap.add_argument("--acq-frames", type=int, default=2)
    ap.add_argument("--lost-frames", type=int, default=2)
    args = ap.parse_args()

    w, h = args.width, args.height
    if w % 4:
        print(f"FAIL  宽度必须是 4 的倍数（每拍 4 像素），收到 {w}")
        return 2
    xw, yw = max(1, (w - 1).bit_length()), max(1, (h - 1).bit_length())

    det_run = load_detect_runner()
    chain_model = load_chain_model()
    ovl_model = load_overlay_model()
    det_model = load_detect_model()

    # 每帧一个 frame 身份，session 固定为 1
    scene = build_scene(w, h)
    beats, spans = [], []
    for fid, _name, _note, painter in scene:
        fbeats = det_run.make_frame(w, h, painter, 1, fid)
        spans.append((fid, len(beats), len(beats) + len(fbeats)))
        beats.extend(fbeats)
        beats.extend(det_run.idle(1))       # 帧间空拍，与真实流的帧边界更接近

    det_p = dict(target_class=0, hue_half_width_deg=30, c_min=24, v_min=32,
                 min_count=64, xw=xw, yw=yw)
    trk_p = dict(acq_frames=args.acq_frames, lost_frames=args.lost_frames, max_jump=0)
    ovl_p = dict(box_thick=3, cross_arm=12, cross_thick=1)
    params = dict(TARGET_CLASS=0, HUE_HALF_WIDTH_DEG=30, C_MIN=24, V_MIN=32,
                  MIN_COUNT=64, XW=xw, YW=yw,
                  ACQ_FRAMES=args.acq_frames, LOST_FRAMES=args.lost_frames, MAX_JUMP=0,
                  BOX_THICK=ovl_p["box_thick"], CROSS_ARM=ovl_p["cross_arm"],
                  CROSS_THICK=ovl_p["cross_thick"])

    cfg = (f"几何 {w}x{h}（XW={xw} YW={yw}）、ACQ_FRAMES={args.acq_frames}、"
           f"LOST_FRAMES={args.lost_frames}、MIN_COUNT=64、hue ±30°、"
           f"BOX_THICK={ovl_p['box_thick']}、CROSS_ARM={ovl_p['cross_arm']}")
    print(f"[场景] {len(scene)} 帧，{len(beats)} 拍，{cfg}")

    recs = chain_model.sim_chain(beats, dict(detect=det_p, track=trk_p, overlay=ovl_p))
    if len(recs) != len(beats):
        print(f"FAIL  模型返回 {len(recs)} 拍，激励 {len(beats)} 拍")
        return 2

    outdir = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="ct-render-"))
    outdir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ct-render-sim-") as td:
        tmp = Path(td)
        stim, pixf, beatf = tmp / "stim.txt", tmp / "pix.txt", tmp / "beat.txt"
        det_run.write_stim(stim, beats)
        ok, out, err = sl.simulate(
            srcs=[RTL / "color_classify.v", RTL / "color_target_detect.v",
                  RTL / "color_target_track.v", RTL / "color_target_overlay.v",
                  TB / "tb_color_target_chain_render.v"],
            tb_top="tb_color_target_chain_render", params=params,
            plusargs=dict(STIM=stim.as_posix(), PIX=pixf.as_posix(),
                          BEAT=beatf.as_posix()),
            requested=args.sim, msim_root=args.msim, workdir=tmp, name="render")
        if not ok:
            print("FAIL  [仿真]\n      " + err.strip().replace("\n", "\n      "))
            return 2
        if "FAIL" in out or "PASS color_target_render" not in out:
            print("FAIL  [仿真台]\n      " + out.strip().replace("\n", "\n      "))
            return 2

        # ---- 逐拍：状态与显示 ----
        got_beat = [[int(v) for v in ln.split()]
                    for ln in beatf.read_text().splitlines() if ln.strip()]
        want_beat = [[r["state"], r["show"]] for r in recs]
        if len(got_beat) != len(want_beat):
            print(f"FAIL  [逐拍] 转储 {len(got_beat)} 拍 != 激励 {len(want_beat)} 拍")
            return 2
        bad = [(i, g, x) for i, (g, x) in enumerate(zip(got_beat, want_beat)) if g != x]
        if bad:
            print(f"FAIL  [逐拍与模型不符]  {len(bad)}/{len(want_beat)} 拍")
            for i, g, x in bad[:5]:
                print(f"      拍{i}（frame={beats[i]['frame']}）: got={g} want={x}")
            return 1

        # ---- 逐像素：覆盖与合成结果（4 个 lane 全比）----
        # 像素按 (帧号, x, y) 建索引：多帧画面里坐标会重复，只按坐标建图会被后一帧覆盖。
        pixels = {}
        for ln in pixf.read_text().splitlines():
            if not ln.strip():
                continue
            fid, ys, xs, rgb, ov = ln.split()
            v = int(rgb, 16)
            pixels[(int(fid), int(xs), int(ys))] = (v >> 16 & 0xFF, v >> 8 & 0xFF, v & 0xFF)

        def lane_rgb(data96, k):
            w24 = (data96 >> (24 * (3 - k))) & 0xFFFFFF
            return (w24 >> 16 & 0xFF, w24 >> 8 & 0xFF, w24 & 0xFF)

        n_pix = 0
        for i, b in enumerate(beats):
            if not b["valid"]:
                continue
            r = recs[i]
            for k in range(4):
                px = (b["x0"] + k, b["y"])
                color = ovl_model.overlay_pixel(
                    px[0], px[1], r["show"], r["show"], r["xmin"], r["xmax"],
                    r["ymin"], r["ymax"], r["cx"], r["cy"], ovl_p)
                # 两边都用 (r,g,b) 元组比较：overlay_pixel 返回的是 24 位整数，
                # 直接和转储出来的"合成像素"比会变成 int 与 tuple 比（值对、类型错）。
                want = ((color >> 16 & 0xFF, color >> 8 & 0xFF, color & 0xFF)
                        if color else lane_rgb(b["data96"], k))
                got = pixels.get((b["frame"], px[0], px[1]))
                n_pix += 1
                if got != want:
                    print(f"FAIL  [逐像素与模型不符] 帧{b['frame']} 像素 {px}: "
                          f"got={got} want={want}（覆盖色=0x{color:06x}）")
                    return 1
        if len(pixels) != n_pix:
            print(f"FAIL  [逐像素] 转储 {len(pixels)} 个像素 != 期望 {n_pix}")
            return 1
        print(f"PASS  逐拍 {len(want_beat)} 拍、逐像素 {n_pix} 像素与链路模型一致")

    # ---- 渲染 ----
    index = ["# 渲染帧图索引（**合成画面，非实拍**）", "",
             f"参数：{cfg}", "",
             "## 怎么读这些图",
             "",
             "**画面上画的框来自上一帧的检测结果。** detect 在 eof 之后 1 拍才发布、track 在那一拍才消费，",
             "所以第 N 帧画面上的框是第 N-1 帧算出来的（README §2.4、INTERFACE §6）。",
             "这不是缺陷，而是协议 §4.3 要求 MAIN 在帧边界寄存一级的原因——本表如实标出每个框的来源。",
             ""]
    for fid, name, note, _painter in scene:
        first, last = [(a, b) for f, a, b in spans if f == fid][0]
        idxs = [i for i in range(first, last) if beats[i]["valid"]]
        fpx = {}
        for i in idxs:
            b = beats[i]
            for k in range(4):
                px = (b["x0"] + k, b["y"])
                fpx[px] = pixels.get((fid, px[0], px[1]), (0, 0, 0))
        frame_to_png(fpx, w, h, args.scale, outdir / f"{name}.png")
        r = recs[idxs[-1]]
        st = STATE_NAMES[r["state"]]
        if r["show"]:
            box = (f"框 x{r['xmin']}..{r['xmax']} y{r['ymin']}..{r['ymax']}，"
                   f"中心({r['cx']},{r['cy']})，count={r['count']}，"
                   f"来自帧{r['frame']}的结果")
        else:
            box = "本帧画面无框"
        print(f"      帧{fid:02d} {name}  state={st} show={r['show']}  {box}")
        index.append(f"- `{name}.png` — {note}")
        index.append(f"  - 本帧期间状态 **{st}**，{box}")
    (outdir / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"\nPASS  渲染 {len(scene)} 帧到 {outdir}")
    print(f"      索引：{outdir / 'index.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
