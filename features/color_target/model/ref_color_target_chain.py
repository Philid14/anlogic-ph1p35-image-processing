"""detect -> track -> overlay 三级链路的组合参考模型。

不是简单地把三个模型首尾相接，而是**按逐拍时序**接：关键是协议 §4.3 警告过的那件事——

  detect 的结果在 eof 那一拍之后 1 拍才发布（O_result_ready 单拍脉冲）；
  track 在那个脉冲那一拍消费它，于是 track 的输出在 eof 之后 1 拍才更新；
  overlay 纯组合，直接吃 track 的输出。

因此本模型按"第 i 拍用第 i-1 拍的发布结果"来推进 track，与 tb_color_target_chain 的
逐拍采样点严格对齐；而不是假设"帧结束的瞬间框就变了"。
"""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_det = _load("ct_det_chain", "ref_color_target.py")
_trk = _load("ct_trk_chain", "ref_color_target_track.py")
_ovl = _load("ct_ovl_chain", "ref_color_target_overlay.py")

CHAIN_DEFAULTS = dict(
    detect=dict(target_class=0, hue_half_width_deg=30, c_min=24, v_min=32,
                min_count=4, xw=11, yw=10),
    track=dict(acq_frames=3, lost_frames=15, max_jump=0),
    overlay=None,
)


def sim_chain(beats, p=None):
    """返回与输入等长的一串 {state, show, ov}，对应 tb 每拍的采样点。"""
    p = dict(CHAIN_DEFAULTS, **(p or {}))
    det_p, trk_p, ovl_p = p["detect"], p["track"], p["overlay"]

    # 1) detect：先算出它每帧发布的结果，并记下是哪一拍（valid&&eof）发布的
    eof_idx = [i for i, b in enumerate(beats) if b["valid"] and b["eof"]]
    pubs = _det.run([dict(b) for b in beats], det_p)
    assert len(pubs) == len(eof_idx), "detect 发布次数与 eof 拍数不一致"
    pub_by_beat = dict(zip(eof_idx, pubs))

    # 2) track：第 i 拍吃第 i-1 拍的发布（这正是 O_result_ready 延迟一拍的效果）
    n = len(beats)
    tin = []
    for i in range(n):
        pub = pub_by_beat.get(i - 1)
        if pub is None:
            tin.append(dict(strobe=0, rvalid=0, present=0, count=0,
                            xmin=0, xmax=0, ymin=0, ymax=0, cx=0, cy=0,
                            session=0, frame=0))
        else:
            tin.append(dict(strobe=1, rvalid=pub["valid"], present=pub["present"],
                            count=pub["count"], xmin=pub["xmin"], xmax=pub["xmax"],
                            ymin=pub["ymin"], ymax=pub["ymax"],
                            cx=pub["cx"], cy=pub["cy"],
                            session=pub["session"], frame=pub["frame"]))
    trecs = _trk.sim_track(tin, trk_p)

    # 3) overlay：与 tb 的接线一致 —— I_result_valid = I_target_present = track.O_show，
    #    坐标系用 lane0 的 (x0, y)
    out = []
    for i, b in enumerate(beats):
        t = trecs[i]
        ov = _ovl.overlay_pixel(b["x0"], b["y"], t["show"], t["show"],
                                t["xmin"], t["xmax"], t["ymin"], t["ymax"],
                                t["cx"], t["cy"], ovl_p)
        out.append(dict(state=t["state"], show=t["show"], ov=ov))
    return out
