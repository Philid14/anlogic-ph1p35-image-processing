"""color_target_track 的参考模型（与 rtl/color_target_track.v 逐拍等价）。

刻意复现的语义：
  * I_result_valid=0（中止帧）**不评估**，状态与结果都不变；
  * 会话变化时把本帧当作 SEARCH 重新评估，而不是丢弃（新会话首帧仍可开始跟踪）；
  * HOLD 期间显示结果保持"上一次被接受的那一帧"，不随丢失帧被清零；
  * 跳变门限 MAX_JUMP=0 表示关闭。
"""

TRACK_DEFAULTS = dict(acq_frames=3, lost_frames=15, max_jump=0)

S_SEARCH, S_ACQ, S_TRACK, S_HOLD = 0, 1, 2, 3
STATE_NAMES = {S_SEARCH: "SEARCH", S_ACQ: "ACQ", S_TRACK: "TRACK", S_HOLD: "HOLD"}


def clamp_frames(v):
    """与 RTL 的 ACQ_EFF / LOST_EFF 一致：8 位计数器，合法范围夹到 1..255。

    取 0 与取 1 同义（都表示"立即"）；超过 255 在 8 位里表示不了，一律夹到 255，
    而不是让高位被悄悄丢掉（ACQ_FRAMES=256 截成 0 会变成"第一帧就确认"）。
    """
    return 1 if v < 1 else (255 if v > 255 else v)


def clamp_max_jump(v):
    """与 RTL 的 MAX_JUMP_EFF 一致：0 表示关闭，负数夹到 0。"""
    return 0 if v < 0 else v


def sim_track(beats, p=None):
    """beats: 每项 dict(strobe, rvalid, present, count, xmin, xmax, ymin, ymax,
                        cx, cy, session, frame)。

    返回与输入等长的一串记录，每项 = 该拍之后（若该拍有效则可能是更新后）的输出。
    对应 tb 在每拍 posedge 之后立即采样的那一行。
    """
    p = dict(TRACK_DEFAULTS, **(p or {}))
    acq_f = clamp_frames(p["acq_frames"])
    lost_f = clamp_frames(p["lost_frames"])
    max_jump = clamp_max_jump(p["max_jump"])

    state = S_SEARCH
    acq = lost = 0
    last_cx = last_cy = 0
    cur_session = 0
    bundle = dict(count=0, xmin=0, xmax=0, ymin=0, ymax=0, cx=0, cy=0,
                  session=0, frame=0)
    out_state, out_show = S_SEARCH, 0

    recs = []
    for b in beats:
        strobe = bool(b["strobe"]) and bool(b["rvalid"])
        session_new = b["session"] != cur_session

        eff_state = S_SEARCH if session_new else state
        eff_acq = 0 if session_new else acq
        eff_lost = 0 if session_new else lost
        eff_tracked = eff_state in (S_TRACK, S_HOLD)

        ddx = abs(b["cx"] - last_cx)
        ddy = abs(b["cy"] - last_cy)
        jump_bad = bool(max_jump) and eff_tracked and (ddx > max_jump or ddy > max_jump)

        accept = strobe and b["present"] and not jump_bad

        nxt_state, nxt_acq, nxt_lost = eff_state, eff_acq, eff_lost
        change = 0
        if strobe:
            if accept:
                nxt_acq, nxt_lost = eff_acq + 1, 0
                if eff_state in (S_SEARCH, S_ACQ):
                    nxt_state = S_TRACK if (eff_acq + 1) >= acq_f else S_ACQ
                else:
                    nxt_state = S_TRACK
            else:
                nxt_acq = 0
                if eff_state in (S_SEARCH, S_ACQ):
                    nxt_state = S_SEARCH
                elif eff_state == S_TRACK:
                    # 与 RTL 一致：门限对 TRACK 的首次丢失同样生效，
                    # LOST_FRAMES=1 时立刻回 SEARCH，而不是先进 HOLD
                    nxt_lost = 1
                    nxt_state = S_SEARCH if 1 >= lost_f else S_HOLD
                else:
                    nxt_lost = eff_lost + 1
                    nxt_state = S_SEARCH if (eff_lost + 1) >= lost_f else S_HOLD

            state, acq, lost = nxt_state, nxt_acq, nxt_lost
            cur_session = b["session"]
            if accept:
                last_cx, last_cy = b["cx"], b["cy"]
                bundle = dict(count=b["count"], xmin=b["xmin"], xmax=b["xmax"],
                              ymin=b["ymin"], ymax=b["ymax"], cx=b["cx"], cy=b["cy"],
                              session=b["session"], frame=b["frame"])
            out_state = nxt_state
            out_show = 1 if nxt_state in (S_TRACK, S_HOLD) else 0
            change = 1 if nxt_state != eff_state else 0

        recs.append(dict(state=out_state, show=out_show, change=change, **bundle))
    return recs
