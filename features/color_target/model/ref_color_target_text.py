"""color_target_text_overlay 的参考模型（与 rtl/color_target_text_overlay.v 等价）。

两个刻意的独立性：

1. **十进制转换不照着 RTL 的双-dabble 写**——这里直接用 Python 的十进制格式化
   （`f"{v:06d}"`）。于是"RTL 的双-dabble 与模型一起错"会被逐像素比对抓到。
2. **字形有两种来源**：默认用桩（`stub_glyph`，与 `tb/ct_text_font_stub.v` 逐位一致，
   不依赖主线任何文件）；也可以解析**主线真字库** `osd_char_lib.v`（`parse_font`），
   用来把"字形位索引（[15] 最左）"这条隐式约定也验掉——这条用桩验不出来。
   本模型不修改字库：共享 OSD 由 MAIN 维护（协议 §3）。
"""

import re
from pathlib import Path

TEXT_DEFAULTS = dict(
    enable=1, x0=16, y0=600, scale=1, line_chars=14,
    text_rgb=0xFFFFFF, dim_rgb=0x808080, bg_rgb=0x101010,
)

# 显示位数的上限：超范围时**饱和**显示（与 RTL 一致），不是截断
MAX_COUNT, MAX_CX, MAX_CY = 999999, 9999, 999

STATE_NAMES = {0: "SEARCH", 1: "ACQ", 2: "TRACK", 3: "HOLD"}


def stub_glyph(char, row):
    """与 tb 里 `ct_text_font_stub.v` 的桩逐位一致。"""
    return (((char & 0xFF) << 8) | ((row & 0xF) << 4)) ^ 0xABCD


# 主线共享字库的默认位置（**只读**引用；协议 §3：共享 OSD 由 MAIN 维护）
DEFAULT_FONT = (Path(__file__).resolve().parents[3] / "in_out_example"
                / "lab_ex3_osd_SC500_720P" / "lab_ex3_osd" / "user_source"
                / "hdl_source" / "osd_char_lib.v")


def find_font(path=None):
    """返回可用的字库路径，找不到返回 None。"""
    p = Path(path) if path else DEFAULT_FONT
    return p if p.exists() else None


def parse_font(path):
    """把主线 `osd_char_lib.v` 解析成 {(字符码, 行): 16 位点阵}。

    **为什么要解析真字库**：字形位的**索引约定**（`[15]` 最左、每行 16 位、共 16 行）是本
    模块与字库之间唯一的隐式契约。用桩测不出来——桩用什么约定，模块就跟着用什么约定，
    两边一起错也发现不了。解析真字库后逐位比对，才能在接入前把这条约定钉死。

    文件是 MAIN 标注为"frozen"的，格式固定：
        case(I_char) ... CHAR_X: begin case(I_row) 4'dN: O_row_bits = 16'hYYYY; ... endcase end ...
    解析失败会抛异常（不静默返回空表）——格式变了要立刻知道，而不是悄悄退化成"全 0 字形"。
    """
    txt = Path(path).read_text(encoding="utf-8", errors="replace")
    codes = {name: int(val, 16) for name, val in
             re.findall(r"localparam\s+CHAR_(\w+)\s*=\s*8'h([0-9a-fA-F]{2})", txt)}
    if not codes:
        raise ValueError(f"{path}: 没解析到任何 CHAR_* localparam，格式可能变了")
    glyphs = {}
    for name, body in re.findall(r"(CHAR_\w+)\s*:\s*begin(.*?)endcase\s*end\b", txt, re.S):
        code = codes.get(name[5:])
        if code is None:
            continue
        rows = {int(r): int(v, 16) for r, v in
                re.findall(r"4'd(\d+)\s*:\s*O_row_bits\s*=\s*16'h([0-9a-fA-F]{4})", body)}
        for r in range(16):
            glyphs[(code, r)] = rows.get(r, 0x0000)   # 未列出 = 空白（字库的 default 也是 0）
    if not glyphs:
        raise ValueError(f"{path}: 解析到 {len(codes)} 个字符码但没有任何字形行，格式可能变了")
    return glyphs


def make_font_bit(glyphs):
    """返回 glyph_fn(char, row, gcol) -> 0/1，按真字库的位序（[15] 最左）。"""
    def fn(char, row, gcol):
        bits = glyphs.get((char & 0xFF, row & 0xF), 0)
        return (bits >> (15 - gcol)) & 1
    return fn


def geom(p=None):
    """返回 (S, LOG2S, CELL, GAP, REG_W, REG_H)：字符格边长、行间隙、区域尺寸。"""
    p = dict(TEXT_DEFAULTS, **(p or {}))
    s = 1 if p["scale"] <= 1 else 2
    log2s = 0 if s == 1 else 1
    cell = 16 * s
    gap = 2 * s
    return s, log2s, cell, gap, p["line_chars"] * cell, 2 * cell + gap


def saturate(count, cx, cy):
    """与 RTL 的 sat_c/sat_x/sat_y 一致。"""
    return (min(count, MAX_COUNT), min(cx, MAX_CX), min(cy, MAX_CY))


def text_lines(state, count, cx, cy, p=None):
    """两行文字内容（第二行右侧按 6 字符位右补空格）。"""
    p = dict(TEXT_DEFAULTS, **(p or {}))
    n = p["line_chars"]
    c, x, y = saturate(count, cx, cy)
    line0 = f"RED X{x:04d} Y{y:03d}"
    line1 = f"N{c:06d} " + STATE_NAMES.get(state, "HOLD").ljust(6)
    return line0.ljust(n)[:n], line1.ljust(n)[:n]


def overlay_pixel(x, y, line0, line1, show, p=None, glyph_fn=None):
    """返回 (overlay_valid, rgb, glyph_char, glyph_row)。

    与 RTL 一致：区域内一律覆盖（底色），字形位为 1 时用文字色（I_show 决定亮/暗）。
    `glyph_fn(char, row, gcol) -> 0/1` 缺省用桩；接真字库时传 `make_font_bit(glyphs)`。
    """
    p = dict(TEXT_DEFAULTS, **(p or {}))
    if not p["enable"]:
        return 0, 0, 0, 0
    _s, log2s, cell, gap, reg_w, reg_h = geom(p)
    lx, ly = x - p["x0"], y - p["y0"]
    if not (0 <= lx < reg_w and 0 <= ly < reg_h):
        return 0, 0, 0, 0
    line1_sel = ly >= cell + gap
    ly_l = ly - (cell + gap) if line1_sel else ly
    col = lx // cell
    gcol = (lx % cell) >> log2s
    grow = (ly_l % cell) >> log2s
    line = line1 if line1_sel else line0
    ch = ord(line[col]) if col < len(line) else 0x20
    if glyph_fn is None:
        gbit = (stub_glyph(ch, grow) >> (15 - gcol)) & 1
    else:
        gbit = glyph_fn(ch, grow, gcol)
    rgb = (p["text_rgb"] if show else p["dim_rgb"]) if gbit else p["bg_rgb"]
    return 1, rgb, ch, grow
