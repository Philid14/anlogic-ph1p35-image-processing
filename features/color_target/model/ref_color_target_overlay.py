"""color_target_overlay 的参考模型（与 rtl/color_target_overlay.v 等价）。

单独成文件而不是并进 ref_color_target.py：标注（T3）与检测（T1/T2）是两个关注点，
分开也便于各自独立演进。
"""

OVERLAY_DEFAULTS = dict(box_thick=3, box_rgb=0x00FF00,
                        cross_arm=12, cross_thick=1, cross_rgb=0xFFFF00)


def overlay_pixel(x, y, result_valid, present, xmin, xmax, ymin, ymax, cx, cy, p=None):
    """返回该像素的覆盖颜色；0 表示不覆盖。

    与 RTL 一致：比较域加宽一位防溢出（in+THICK-1 可能越界），减法一侧饱和到 0
    防下溢（max-THICK+1 在框小于 THICK 时会为负）；十字压在框线之上。
    """
    p = dict(OVERLAY_DEFAULTS, **(p or {}))
    if not (result_valid and present):
        return 0
    b = p["box_thick"]

    xl_hi = xmin + (b - 1)
    xr_lo = xmax - (b - 1) if xmax >= (b - 1) else 0
    yt_hi = ymin + (b - 1)
    yb_lo = ymax - (b - 1) if ymax >= (b - 1) else 0

    x_in_span = xmin <= x <= xmax
    y_in_span = ymin <= y <= ymax
    x_in_band = (xmin <= x <= xl_hi) or (xr_lo <= x <= xmax)
    y_in_band = (ymin <= y <= yt_hi) or (yb_lo <= y <= ymax)
    box_hit = (y_in_band and x_in_span) or (x_in_band and y_in_span)

    a = p["cross_arm"]
    ax_lo = cx - a if cx >= a else 0
    ax_hi = cx + a
    ay_lo = cy - a if cy >= a else 0
    ay_hi = cy + a
    x_in_arm = ax_lo <= x <= ax_hi
    y_in_arm = ay_lo <= y <= ay_hi
    y_hbar = cy <= y <= cy + (p["cross_thick"] - 1)
    x_vbar = cx <= x <= cx + (p["cross_thick"] - 1)
    cross_hit = (x_in_arm and y_hbar) or (x_vbar and y_in_arm)

    if cross_hit:
        return p["cross_rgb"]
    if box_hit:
        return p["box_rgb"]
    return 0


def overlay_window(xmin, xmax, ymin, ymax, cx, cy, pad=3):
    """生成"值得比对"的像素集合：包围框外扩 pad 的一圈 + 十字臂范围。

    不扫全帧——组合模块的判定只与局部有关，采样这些位置即可覆盖所有分支。
    """
    xs = set()
    ys = set()
    for v in (xmin, xmax, cx):
        for d in range(-pad, pad + 1):
            xs.add(max(0, v + d))
    xs.update(range(max(0, xmin - 1), xmax + 2))
    for v in (ymin, ymax, cy):
        for d in range(-pad, pad + 1):
            ys.add(max(0, v + d))
    ys.update(range(max(0, ymin - 1), ymax + 2))
    # 十字半臂覆盖的范围也要采到
    for d in range(-OVERLAY_DEFAULTS["cross_arm"], OVERLAY_DEFAULTS["cross_arm"] + 1):
        xs.add(max(0, cx + d))
        ys.add(max(0, cy + d))
    return sorted(xs), sorted(ys)
