"""color_target_track 的独立自检：生成逐帧激励 -> 仿真 -> 与参考模型逐帧比对。

用法：
    python features/color_target/run_color_target_track.py
    python features/color_target/run_color_target_track.py --sim modelsim
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


TB_NAME = "tb_color_target_track"
MOD_NAME = "color_target_track"


def load_model():
    spec = importlib.util.spec_from_file_location(
        "ref_ct_tr", HERE / "model" / "ref_color_target_track.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# 转储每行的字段顺序（与 tb_color_target_track.v 的 $fwrite 一致）
FIELDS = ["state", "show", "count", "xmin", "xmax", "ymin", "ymax",
          "cx", "cy", "session", "frame", "change"]


def check_hard(got, hard):
    """硬编码期望检查：hard = {帧序号: {字段名: 期望值}}，只查写出来的字段。

    为什么需要：参考模型是照同一套意图写的，"RTL 与模型一起错"时逐帧对拍永远一致。
    这里的期望值来自审查意见与状态机语义的推演，**不经过模型**，能独立兜底。
    """
    bad = []
    for idx in sorted(hard):
        if idx >= len(got):
            bad.append(f"帧{idx}: 转储只有 {len(got)} 帧，缺这一帧")
            continue
        for f, v in hard[idx].items():
            j = FIELDS.index(f)
            if got[idx][j] != v:
                bad.append(f"帧{idx} {f}: got={got[idx][j]} want={v}（整行 {got[idx]}）")
    return bad


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

    # ==================================================================
    # 审查意见③：最小门限 / 默认门限 / 目标重现 / 会话切换 / 计数器范围
    #
    # 缺陷：S_TRACK 收到首次丢失时**无条件**进 HOLD，没有走门限判断（S_HOLD 分支
    # 却有），于是 LOST_FRAMES=1 时目标不会立刻隐藏，要多丢一帧才消失——比配置
    # 要求的晚一帧，也和其他门限的行为不一致。
    #
    # 下面这些用例的期望值**不经过参考模型**，直接按状态机的语义写死在第 4 项里
    # （{帧序号: {字段名: 期望值}}），所以"模型与 RTL 一起错"时它们照样会失败。
    # ==================================================================

    # LOST_FRAMES=1：首次丢失就必须立刻回 SEARCH 并停止显示
    cases.append(("lost_frames_1_hides_on_first_miss",
                  [B(frame=1), B(present=0, frame=2)],
                  {"acq_frames": 1, "lost_frames": 1},
                  {0: dict(state=2, show=1, change=1),    # 确认
                   1: dict(state=0, show=0, change=1)}))  # 首次丢失即隐藏

    # LOST_FRAMES=2：首次丢失只到 HOLD（框保持），第二次丢失才回 SEARCH
    cases.append(("lost_frames_2_holds_once",
                  [B(frame=1), B(present=0, frame=2), B(present=0, frame=3)],
                  {"acq_frames": 1, "lost_frames": 2},
                  {1: dict(state=3, show=1, change=1),
                   2: dict(state=0, show=0, change=1)}))

    # 默认门限 LOST_FRAMES=15：前 14 次丢失保持 HOLD 且一直显示，第 15 次才失去
    dflt = ([B(frame=1), B(frame=2), B(frame=3)]
            + [B(present=0, frame=4 + i) for i in range(15)])
    hard_dflt = {2: dict(state=2, show=1)}                 # 第 3 帧确认 TRACK
    for i in range(1, 16):                                 # 第 i 次丢失
        hard_dflt[2 + i] = dict(state=(3 if i < 15 else 0),
                                show=(1 if i < 15 else 0))
    cases.append(("default_lost_frames_holds_14_then_search", dflt, {}, hard_dflt))

    # 目标重现：彻底失去后再出现，必须重新走一遍确认，不能直接 TRACK
    cases.append(("reappear_after_loss_reacquires",
                  [B(frame=1), B(frame=2), B(frame=3),
                   B(present=0, frame=4), B(frame=5), B(frame=6), B(frame=7)],
                  {"acq_frames": 3, "lost_frames": 1},
                  {2: dict(state=2, show=1),
                   3: dict(state=0, show=0, change=1),     # LOST_FRAMES=1 -> 失去
                   4: dict(state=1, show=0, change=1),     # 重现 -> 回到 ACQ，仍不显示
                   5: dict(state=1, show=0, change=0),
                   6: dict(state=2, show=1, change=1)}))

    # 会话切换：不得继承旧会话的跟踪状态，但本帧仍要按新会话重新评估（不丢弃）
    cases.append(("session_switch_reevaluates_frame",
                  [B(frame=1), B(frame=2), B(frame=3), B(session=2, frame=1)],
                  {"acq_frames": 3, "lost_frames": 15},
                  {2: dict(state=2, show=1, session=1, frame=3),
                   3: dict(state=1, show=0, change=1, session=2, frame=1)}))

    # 计数器上限：ACQ_FRAMES / LOST_FRAMES 是 8 位，255 必须真的数到第 255 帧
    n255 = ([B(frame=i + 1) for i in range(255)]
            + [B(present=0, frame=300 + i) for i in range(255)])
    cases.append(("counter_full_range_255", n255,
                  {"acq_frames": 255, "lost_frames": 255},
                  {253: dict(state=1, show=0),      # 第 254 帧：还在 ACQ
                   254: dict(state=2, show=1),      # 第 255 帧：确认
                   255: dict(state=3, show=1),      # 首次丢失 -> HOLD（未到 255）
                   508: dict(state=3, show=1),      # 第 254 次丢失：仍在 HOLD
                   509: dict(state=0, show=0)}))    # 第 255 次丢失：达门限

    # 越界参数：0 与 1 同义（"立即"，不是"永不"）
    cases.append(("acq_frames_0_is_immediate",
                  [B(frame=1)], {"acq_frames": 0},
                  {0: dict(state=2, show=1, change=1)}))
    cases.append(("lost_frames_0_hides_immediately",
                  [B(frame=1), B(present=0, frame=2)],
                  {"acq_frames": 1, "lost_frames": 0},
                  {1: dict(state=0, show=0)}))

    # 越界参数：>255 夹到 255，而不是让高位被 [7:0] 截掉
    # （ACQ_FRAMES=256 截断成 0 会变成"第一帧就确认"，与"要 256 帧"完全相反）
    cases.append(("acq_frames_256_clamped_to_255",
                  [B(frame=i + 1) for i in range(255)], {"acq_frames": 256},
                  {253: dict(state=1, show=0), 254: dict(state=2, show=1)}))

    # 负的跳变门限夹到 0（关闭）：否则"任意偏移都超标"会把目标永久锁住
    cases.append(("negative_max_jump_is_disabled",
                  [B(frame=1, cx=100, cy=100), B(frame=2, cx=500, cy=100)],
                  {"acq_frames": 1, "max_jump": -5},
                  {1: dict(state=2, show=1, change=0)}))

    return cases


def write_stim(path, beats):
    with open(path, "w", encoding="ascii") as f:
        for b in beats:
            f.write("%d %d %d %0d %0d %0d %0d %0d %0d %0d %d %d\n" % (
                b["strobe"], b["rvalid"], b["present"], b["count"],
                b["xmin"], b["xmax"], b["ymin"], b["ymax"], b["cx"], b["cy"],
                b["session"], b["frame"]))


def check_invariants(beats, got):
    """**不依赖参考模型**的性质断言，直接检查 RTL 的逐帧转储。

    为什么需要：参考模型是照同一套意图写的，"RTL 与模型一起错"时逐帧对拍永远一致。
    这里只用**激励与转储本身**就能判定的性质——它们独立于我的状态机设计意图：

      P0 show 必须恰好等价于 state ∈ {TRACK, HOLD}
      P1 显示时，结果必须来自某个"被接受"的帧（rvalid=1 且 present=1）
      P2 显示时坐标合法：min<=max、在 1280x720 内、count>=1
      P3 SEARCH 不得显示
      P4 change 必须恰好表示"状态发生了变化"（含会话变化的语义）
      P5 连续 HOLD 期间结果不得变化
    """
    accepted = {(b["count"], b["xmin"], b["xmax"], b["ymin"], b["ymax"],
                 b["cx"], b["cy"], b["session"], b["frame"])
                for b in beats if b["strobe"] and b["rvalid"] and b["present"]}
    bad = []
    prev_state, prev_sess = 0, None
    for i, r in enumerate(got):
        st, show, cnt, xmin, xmax, ymin, ymax, cx, cy, sess, fid, chg = r
        if show != (1 if st in (2, 3) else 0):
            bad.append(f"P0 帧{i}: show={show} 与 state={st} 不符")
        if show:
            if (cnt, xmin, xmax, ymin, ymax, cx, cy, sess, fid) not in accepted:
                bad.append(f"P1 帧{i}: 显示的结果（count={cnt} x={xmin}..{xmax} "
                           f"y={ymin}..{ymax} 中心=({cx},{cy}) 身份=({sess},{fid})）"
                           f"不来自任何被接受的帧")
            if not (xmin <= xmax and ymin <= ymax and cnt >= 1
                    and xmax <= 1279 and ymax <= 719 and cx <= 1279 and cy <= 719):
                bad.append(f"P2 帧{i}: 坐标/计数越界或反序")
        if st == 0 and show:
            bad.append(f"P3 帧{i}: SEARCH 却在显示")
        eff_prev = 0 if (prev_sess is not None and sess != prev_sess) else prev_state
        if chg != (1 if st != eff_prev else 0):
            bad.append(f"P4 帧{i}: change={chg} 但状态 {eff_prev}->{st}")
        if (st == 3 and prev_state == 3 and sess == prev_sess and i > 0
                and list(r[2:11]) != list(got[i - 1][2:11])):
            bad.append(f"P5 帧{i}: HOLD 期间结果发生了变化")
        prev_state, prev_sess = st, sess
    return bad


def main():
    ap = argparse.ArgumentParser()
    simlib = _simlib()
    simlib.add_args(ap)
    args = ap.parse_args()

    model = load_model()
    total = passed = 0
    for case in build_cases():
        name, beats, over = case[0], case[1], case[2]
        hard = case[3] if len(case) > 3 else None
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
            ok, out, err = simlib.simulate(
                srcs=[RTL / "color_target_track.v", TB / "tb_color_target_track.v"],
                tb_top=TB_NAME, params=params,
                plusargs=dict(STIM=stim.as_posix(), OUT=outp.as_posix()),
                requested=args.sim, msim_root=args.msim, workdir=tmp, name="tr")
            if not ok:
                print(f"FAIL  {name}  [仿真]\n      " + err.strip().replace("\n", "\n      "))
                return 2
            if "FAIL" in out or f"PASS {MOD_NAME}" not in out:
                print(f"FAIL  {name}  [仿真台]\n      " + out.strip().replace("\n", "\n      "))
                continue

            got = []
            if outp.exists():
                for line in outp.read_text().splitlines():
                    if line.strip():
                        got.append([int(v) for v in line.split()])
            # 先查硬编码期望：它不依赖模型，出问题时最该先被看到
            if hard:
                hb = check_hard(got, hard)
                if hb:
                    print(f"FAIL  {name}  [硬编码期望不符，未经模型]  {len(hb)} 处")
                    for line in hb[:8]:
                        print("      " + line)
                    continue
            if got != want:
                bad = [(i, got[i], want[i]) for i in range(min(len(got), len(want)))
                       if got[i] != want[i]]
                print(f"FAIL  {name}  [与模型不符]  {len(bad)}/{len(want)} 帧不同")
                for i, g, w in bad[:5]:
                    print(f"      帧{i}: got={g} want={w}")
                continue
            # 与实现无关的性质断言（能抓到"RTL 与模型一起错"的情况）
            inv = check_invariants(beats, got)
            if inv:
                print(f"FAIL  {name}  [性质不变量]  {len(inv)} 条违反")
                for line in inv[:6]:
                    print("      " + line)
                continue
            passed += 1
            print(f"PASS  {name}  (frames={len(want)})")

    print(f"\n{passed}/{total} 用例通过  [sim={args.sim}]")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
