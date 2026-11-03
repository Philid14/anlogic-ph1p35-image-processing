"""color_target_detect 的位精确参考模型（与 RTL 逐拍等价）。

对应 RTL：features/color_target/rtl/color_classify.v 与 color_target_detect.v。
模型刻意逐条复现 RTL 的时序语义，包括：
  * 帧末结果用**含 eof 那一拍**的累加值（NXT），不是旧的 acc；
  * open/abort 在同拍 sof+eof（单拍帧）时也成立（eff_open / eff_abort）；
  * 包围框中心 = (xmin+xmax)>>1 向下取整，**不是像素质心**。
"""

DEFAULTS = dict(target_class=0, hue_half_width_deg=30, c_min=24, v_min=32,
                min_count=64, xw=11, yw=10)


def clamp_hue_width(v):
    """与 RTL 的 W_DEG 一致：夹到 0..60（目标通道为最大的扇区只有 60 度宽）。"""
    return 0 if v < 0 else (60 if v > 60 else v)


def clamp_c_min(v):
    """与 RTL 的 CMIN_D 一致：夹到 0..511（内部按 9 位比较）。

    不夹的话，512 会被低 9 位截成 0（本意"严到不可能命中"反变成"完全不滤彩度"），
    而 -1 的低 9 位是 511（等于"永不命中"）。
    """
    return 0 if v < 0 else (511 if v > 511 else v)


def clamp_v_min(v):
    """与 RTL 的 VMIN_D 一致：夹到 0..255（内部按 8 位比较）。"""
    return 0 if v < 0 else (255 if v > 255 else v)


def clamp_min_count(v):
    """与 RTL 的 MIN_COUNT_EFF 一致：夹到 1..1048575（20 位计数域）。

    下界 1：取 0 会让零命中的帧也判为存在，而那时包围框还是中性元。
    上界 2^20-1：它要跟 20 位计数比较，2^20 会被截成 0，语义正好反过来。
    """
    return 1 if v < 1 else (1048575 if v > 1048575 else v)


def effective_target_class(value):
    return value if value in (1, 2) else 0


def classify(r, g, b, p):
    """单像素分类，与 color_classify.v 等价。"""
    mx = max(r, g, b)
    mn = min(r, g, b)
    chroma = mx - mn
    w = clamp_hue_width(p["hue_half_width_deg"])
    tc = p["target_class"]
    if tc == 1:
        sel = (g > r) and (g >= b)
        d = abs(r - b)
    elif tc == 2:
        sel = (b > r) and (b > g)
        d = abs(r - g)
    else:
        # 除 1/2 之外一律按红处理（与 RTL 的 generate 一致），不存在"选不中任何类"
        sel = (r >= g) and (r >= b)
        d = abs(g - b)
    # 判据用交叉乘积 60*|d| <= W*C（与 RTL 一致），不再预合并 Q8 斜率
    return bool(sel and (d * 60 <= chroma * w)
                and (chroma >= clamp_c_min(p["c_min"]))
                and (mx >= clamp_v_min(p["v_min"])))


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
            # 与 RTL 一致：start_f 那一拍只看本帧的中止输入，
            # 不带上一帧遗留的 aborted_f（否则单拍帧会被误判为中止帧）
            eff_abort = bt["abort"] if start_f else (aborted_f or bt["abort"])
            eff_ok = (open_f or start_f) and not eff_abort
            # 与 RTL 一致：MIN_COUNT 夹到 1..2^20-1（取 0 时会用中性元包围框输出垃圾坐标）
            present = eff_ok and (nxt_cnt >= clamp_min_count(p["min_count"]))
            published.append(dict(
                # 单拍帧（sof 与 eof 同拍）时 cur_* 还没更新，必须取本拍身份，
                # 与 RTL 的 eff_session / eff_frame 一致。
                session=(bt["session"] if start_f else cur_session),
                frame=(bt["frame"] if start_f else cur_frame),
                valid=int(eff_ok), present=int(present),
                cls=(effective_target_class(p["target_class"]) if present else 0),
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
        if pend:
            open_f = False

    return published
