"""color_target_detect 的位精确参考模型（与 RTL 逐拍等价）。

对应 RTL：features/color_target/rtl/color_classify.v 与 color_target_detect.v。
模型刻意逐条复现 RTL 的时序语义，包括：
  * 帧末结果用**含 eof 那一拍**的累加值（NXT），不是旧的 acc；
  * open/abort 在同拍 sof+eof（单拍帧）时也成立（eff_open / eff_abort）；
  * 包围框中心 = (xmin+xmax)>>1 向下取整，**不是像素质心**。
"""

DEFAULTS = dict(target_class=0, hue_half_width_deg=30, c_min=24, v_min=32,
                min_count=64, xw=11, yw=10)


def classify(r, g, b, p):
    """单像素分类，与 color_classify.v 等价。"""
    mx = max(r, g, b)
    mn = min(r, g, b)
    chroma = mx - mn
    w = p["hue_half_width_deg"]
    slope = (60 * 256 + w // 2) // w          # HUE_SLOPE_Q8
    tc = p["target_class"]
    if tc == 1:
        sel = (g > r) and (g >= b)
        d = abs(r - b)
    elif tc == 2:
        sel = (b > r) and (b > g)
        d = abs(r - g)
    else:
        sel = (r >= g) and (r >= b)
        d = abs(g - b)
    return bool(sel and (d * slope <= chroma * 256)
                and (chroma >= p["c_min"]) and (mx >= p["v_min"]))


def lanes(data96):
    """96 位 -> 4 个 (r,g,b)。lane0=[95:72] ... lane3=[23:0]，每 lane {R,G,B}。"""
    out = []
    for k in range(4):
        w = (data96 >> (24 * (3 - k))) & 0xFFFFFF
        out.append(((w >> 16) & 0xFF, (w >> 8) & 0xFF, w & 0xFF))
    return out


def run(beats, p=None):
    """跑一串 beat，返回发布出来的结果列表（每项一个 dict）。"""
    p = dict(DEFAULTS, **(p or {}))
    XMAX = (1 << p["xw"]) - 1
    YMAX = (1 << p["yw"]) - 1

    open_f = False
    aborted_f = False
    cur_session = cur_frame = 0
    cnt = 0
    xmin, xmax = XMAX, 0
    ymin, ymax = YMAX, 0
    published = []

    for bt in beats:
        valid = bt["valid"]
        start_f = valid and bt["sof"]
        pend = valid and bt["eof"]

        hits = 0
        hx_min, hx_max = XMAX, 0
        if valid:
            for k, (r, g, b) in enumerate(lanes(bt["data96"])):
                if classify(r, g, b, p):
                    hits += 1
                    x = bt["x0"] + k
                    hx_min = min(hx_min, x)
                    hx_max = max(hx_max, x)

        hit_ymin = bt["y"] if hits else YMAX
        hit_ymax = bt["y"] if hits else 0

        base_cnt = 0 if start_f else cnt
        base_xmin = XMAX if start_f else xmin
        base_xmax = 0 if start_f else xmax
        base_ymin = YMAX if start_f else ymin
        base_ymax = 0 if start_f else ymax

        nxt_cnt = base_cnt + hits
        nxt_xmin = min(hx_min, base_xmin)
        nxt_xmax = max(hx_max, base_xmax)
        nxt_ymin = min(hit_ymin, base_ymin)
        nxt_ymax = max(hit_ymax, base_ymax)

        if pend:
            eff_ok = (open_f or start_f) and not (aborted_f or bt["abort"])
            # 与 RTL 一致：MIN_COUNT 夹到 >=1（取 0 时会用中性元包围框输出垃圾坐标）
            present = eff_ok and (nxt_cnt >= max(1, p["min_count"]))
            published.append(dict(
                # 单拍帧（sof 与 eof 同拍）时 cur_* 还没更新，必须取本拍身份，
                # 与 RTL 的 eff_session / eff_frame 一致。
                session=(bt["session"] if start_f else cur_session),
                frame=(bt["frame"] if start_f else cur_frame),
                valid=int(eff_ok), present=int(present),
                cls=(p["target_class"] if present else 0),
                count=(nxt_cnt if present else 0),
                xmin=(nxt_xmin if present else 0), xmax=(nxt_xmax if present else 0),
                ymin=(nxt_ymin if present else 0), ymax=(nxt_ymax if present else 0),
                cx=(((nxt_xmin + nxt_xmax) >> 1) if present else 0),
                cy=(((nxt_ymin + nxt_ymax) >> 1) if present else 0)))

        # 寄存器更新（非阻塞语义：上面用的是更新前的值）
        if start_f:
            open_f = True
            aborted_f = bool(bt["abort"])
            cur_session, cur_frame = bt["session"], bt["frame"]
        elif bt["abort"]:
            aborted_f = True
        if valid:
            cnt, xmin, xmax, ymin, ymax = nxt_cnt, nxt_xmin, nxt_xmax, nxt_ymin, nxt_ymax

    return published
