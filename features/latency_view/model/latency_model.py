"""Golden model for features/latency_view (protocol TEAM_PROTOCOL_V1).

The model is integer/bit exact and is shared by the OSD testbench, the preview
script and the documentation. It does not model the association logic of the
RTL (that is verified against independently recorded event times), it only
models the panel layout, the decimal formatting and the glyph mask so the
display side can be compared bit for bit.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from font8x8_public_domain import (  # noqa: E402
    FONT_FIRST_CODE, FONT_LAST_CODE, GLYPH_COLS, GLYPH_ROWS, glyph_rows,
)

TICKS_PER_MS = 100            # one tick = 0.01 ms
MAX_TICKS = 99999             # 5 digits -> 999.99 ms

# (clk_hz, tick_base, tick_remainder, tick_mod); TICK_BASE = clk/100000
CLOCK_PRESETS = {
    "74.25MHz": (74_250_000, 742, 50000, 100000),
    "148.5MHz": (148_500_000, 1485, 0, 100000),
    "27MHz":    (27_000_000, 270, 0, 100000),
    "25.2MHz":  (25_200_000, 252, 0, 100000),
}


def clock_params(clk_hz: int) -> tuple[int, int, int]:
    if clk_hz <= 0:
        raise ValueError("clk_hz must be positive")
    return clk_hz // 100000, clk_hz % 100000, 100000


OSD_COLS = 16
OSD_ROWS = 5
OSD_CELL_PX = GLYPH_COLS          # 8
OSD_SCALE_LOG2 = 1                # 2x -> 16x16 pixel cell
OSD_X0 = 24
OSD_Y0 = 24

_TEMPLATE_ROWS = (
    "LAT  ######MS   ",
    "AGE  ######MS   ",
    "CAP   #####FPS  ",
    "DSP   #####FPS  ",
    "FRM ######## E# ",
)

FIELD_LAT = 5
FIELD_AGE = 21
FIELD_CAP = 38
FIELD_DSP = 54
FIELD_FRM = 68
FIELD_ERR = 78
FIELD_LEN_MS = 6
FIELD_LEN_FPS = 5
FIELD_LEN_FRM = 8
FIELD_LEN_ERR = 1

TEMPLATE = "".join(_TEMPLATE_ROWS)
assert len(TEMPLATE) == OSD_COLS * OSD_ROWS == 80

ERR_UNMATCHED = 0b0001
ERR_RECORD = 0b0010
ERR_EVENT = 0b0100
ERR_SESSION = 0b1000


def _digit(nibble: int) -> str:
    return "0123456789ABCDEF"[nibble & 0xF]


def _decimal_digits(value: int, count: int) -> list[int]:
    value = max(0, int(value))
    out = [0] * count
    for index in range(count - 1, -1, -1):
        out[index] = value % 10
        value //= 10
    if value:
        raise ValueError("value needs more than %d digits" % count)
    return out


def format_ms_field(ticks: int, valid: bool = True) -> str:
    """Six characters DDD.DD from 0.01 ms ticks, leading zeros blanked."""
    if not valid:
        return "---.--"
    value = MAX_TICKS if ticks > MAX_TICKS else max(0, int(ticks))
    digits = _decimal_digits(value, 5)
    out = []
    for position in range(3):
        if position < 2 and digits[position] == 0 and all(d == 0 for d in digits[:position + 1]):
            out.append(" ")
        else:
            out.append(_digit(digits[position]))
    out.append(".")
    out.append(_digit(digits[3]))
    out.append(_digit(digits[4]))
    return "".join(out)


def format_fps_field(value: int, valid: bool = True) -> str:
    """Five characters, right aligned 0..999, or '  ---'."""
    if not valid:
        return "  ---"
    return ("%3d" % min(999, max(0, int(value)))).rjust(5)


def format_frame_field(frame_count: int) -> str:
    return "".join(_digit(d) for d in _decimal_digits(int(frame_count) % 100_000_000, 8))


def format_err_field(err_nibble: int) -> str:
    return _digit(err_nibble)


def char_buffer(lat_ticks: int, age_ticks: int, cap_fps: int, dsp_fps: int,
                frame_count: int, err_nibble: int = 0, lat_valid: bool = True,
                age_valid: bool = True, fps_valid: bool = True) -> str:
    """Full 80 character panel exactly as latency_osd.v writes it."""
    buf = list(TEMPLATE)
    for start, text in (
        (FIELD_LAT, format_ms_field(lat_ticks, lat_valid)),
        (FIELD_AGE, format_ms_field(age_ticks, age_valid)),
        (FIELD_CAP, format_fps_field(cap_fps, fps_valid)),
        (FIELD_DSP, format_fps_field(dsp_fps, fps_valid)),
        (FIELD_FRM, format_frame_field(frame_count)),
        (FIELD_ERR, format_err_field(err_nibble)),
    ):
        for offset, ch in enumerate(text):
            buf[start + offset] = ch
    return "".join(buf)


def template_bits() -> int:
    value = 0
    for ch in TEMPLATE:
        value = (value << 8) | (ord(ch) & 0xFF)
    return value


def cell_size(scale_log2: int = OSD_SCALE_LOG2) -> int:
    return OSD_CELL_PX << scale_log2


def overlay_mask(x: int, y: int, char_buf: str, x0: int = OSD_X0, y0: int = OSD_Y0,
                 scale_log2: int = OSD_SCALE_LOG2, cols: int = OSD_COLS,
                 rows: int = OSD_ROWS):
    """Glyph coverage of one pixel (True/False), or None outside the panel."""
    cell = cell_size(scale_log2)
    if not (x0 <= x < x0 + cols * cell and y0 <= y < y0 + rows * cell):
        return None
    bx = x - x0
    by = y - y0
    cx = bx >> (3 + scale_log2)
    cy = by >> (3 + scale_log2)
    col = (bx >> scale_log2) & (GLYPH_COLS - 1)
    row = (by >> scale_log2) & (GLYPH_ROWS - 1)
    ch = char_buf[cy * cols + cx]
    return bool((glyph_rows(ch)[row] >> col) & 1)


def glyph_pixel(ch: str, row: int, col: int) -> int:
    return (glyph_rows(ch)[row] >> col) & 1


def dim_rgb(rgb: int) -> int:
    red = (rgb >> 16) & 0xFF
    green = (rgb >> 8) & 0xFF
    blue = rgb & 0xFF
    return ((red >> 1) << 16) | ((green >> 1) << 8) | (blue >> 1)


def output_hash_step(current: int, rgb: int) -> int:
    return ((current * 33) + rgb) & 0xFFFFFFFF


def self_test() -> int:
    assert format_ms_field(3330) == " 33.30"
    assert format_ms_field(124) == "  1.24"
    assert format_ms_field(0) == "  0.00"
    assert format_ms_field(99999) == "999.99"
    assert format_ms_field(10, False) == "---.--"
    assert format_fps_field(30) == "   30"
    assert format_fps_field(0, False) == "  ---"
    assert format_frame_field(12345) == "00012345"
    buf = char_buffer(3330, 1240, 30, 60, 12345, 0)
    assert len(buf) == 80
    assert buf[FIELD_LAT:FIELD_LAT + 6] == " 33.30"
    assert buf[FIELD_AGE:FIELD_AGE + 6] == " 12.40"
    assert buf[FIELD_CAP:FIELD_CAP + 5] == "   30"
    assert buf[FIELD_DSP:FIELD_DSP + 5] == "   60"
    assert buf[FIELD_FRM:FIELD_FRM + 8] == "00012345"
    assert buf[FIELD_ERR] == "0"
    assert glyph_rows("A")[0] == 0x0C
    assert glyph_pixel("A", 0, 2) == 1
    print("latency_model self-test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(self_test())
