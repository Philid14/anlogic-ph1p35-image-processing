"""Software golden model for the latency measurement and OSD display deliverable.

This file is the single source of truth shared by

  * the on-screen-text preview  (work/models/latency_osd_preview.py)
  * the Algorithm Lab plugin    (work/algorithm_lab/plugins/latency_osd.py)
  * the RTL layout include      (work/rtl/osd/osd_layout.vh, generated)
  * the character ROM           (work/rtl/osd/char_rom.v, generated)
  * the RTL testbenches         (work/tests/run_latency_sim.py)

Everything here is integer / bit exact on purpose: the values produced by these
functions are compared against the RTL simulation, so no float rounding, no
"close enough" constants and no library that is missing on the target machine.

Units used everywhere:

  tick = 0.01 ms (10 us).  ``lat_ticks`` is the number of ticks measured by
  latency_meter.v; the OSD prints it as milliseconds with two decimals.

Standard library only: this module must run on the project machine without
NumPy/Pillow as well as inside the Algorithm Lab where both are available.
"""
from __future__ import annotations

from bisect import bisect_right
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from font8x8_public_domain import (  # noqa: E402  (generated table)
    FONT_FIRST_CODE,
    FONT_LAST_CODE,
    GLYPH_COLS,
    GLYPH_ROWS,
    glyph_rows,
)

# ---------------------------------------------------------------------------
# 1. Timing constants
# ---------------------------------------------------------------------------

TICKS_PER_MS = 100          # one tick = 0.01 ms
MAX_TICKS = 99999           # largest value the 5 digit field can show (999.99 ms)
MAX_TICK_VALUE = 999.99     # ms, documentation helper

# Clock presets: (clk_hz, tick_base, tick_remainder, tick_mod)
#   tick_base      = clk_hz // 100000
#   tick_remainder = clk_hz %  100000
# The RTL takes the two numbers as parameters so that no divider is inferred.
CLOCK_PRESETS = {
    "74.25MHz": (74_250_000, 742, 50000, 100000),
    "27MHz":    (27_000_000, 270, 0,     100000),
    "25.2MHz":  (25_200_000, 252, 0,     100000),
    "148.5MHz": (148_500_000, 1485, 0,   100000),
}


def clock_params(clk_hz: int) -> tuple[int, int, int]:
    """Return (tick_base, tick_remainder, tick_mod) for a clock frequency."""
    if clk_hz <= 0:
        raise ValueError("clk_hz must be positive")
    return clk_hz // 100000, clk_hz % 100000, 100000


def tick_edges(tick_base: int, tick_remainder: int, tick_mod: int, count: int) -> list[int]:
    """Edge indices at which the RTL tick counter increments (1-based).

    Mirrors latency_meter.v exactly: ``tick_run`` counts the cycles inside the
    current interval; the interval is TICK_BASE, or TICK_BASE+1 whenever the
    fractional accumulator crosses TICK_MOD.
    """
    if count < 0:
        raise ValueError("count must not be negative")
    if not 0 <= tick_remainder < tick_mod:
        raise ValueError("require 0 <= tick_remainder < tick_mod")
    edges: list[int] = []
    run = 0
    interval = tick_base
    acc = 0
    cycle = 0
    while len(edges) < count:
        cycle += 1
        if run >= interval - 1:
            edges.append(cycle)
            run = 0
            total = acc + tick_remainder
            if total >= tick_mod:
                acc = total - tick_mod
                interval = tick_base + 1
            else:
                acc = total
                interval = tick_base
        else:
            run += 1
    return edges


def tick_count_at(edges: list[int], cycle: int) -> int:
    """Value of the RTL tick counter during ``cycle``."""
    return bisect_right(edges, cycle)


# ---------------------------------------------------------------------------
# 2. Latency-meter model (same-clock, phase aligned case = bit exact)
# ---------------------------------------------------------------------------

# latency_meter.v detects a source token with a 2-flop synchroniser plus one
# edge-detect stage, i.e. the time stamp is taken 3 destination cycles after
# the cycle that carried the token. The destination-side pop is taken on the
# edge that ends the cycle carrying out_token.
SYNC_CYCLES = 3


def measured_latency(src_token_cycle: int, out_token_cycle: int,
                     tick_base: int, tick_remainder: int, tick_mod: int) -> tuple[int, int]:
    """Return (lat_ticks, lat_cycles) the RTL reports for one token pair.

    Only valid when clk_src and clk are the same clock. For different clocks
    the result is bounded by :func:`measured_latency_bounds`.
    """
    stamp_cycle = src_token_cycle + SYNC_CYCLES
    lat_cycles = out_token_cycle - stamp_cycle
    if lat_cycles < 0:
        raise ValueError("out_token precedes the stamped source event")
    edges = tick_edges(tick_base, tick_remainder, tick_mod, lat_cycles + tick_base + 2)
    lat_ticks = tick_count_at(edges, out_token_cycle) - tick_count_at(edges, stamp_cycle)
    return lat_ticks, lat_cycles


def measured_latency_bounds(true_cycles: int) -> tuple[int, int]:
    """Cycle bounds of a measurement taken across two asynchronous clocks.

    The 2-flop synchroniser delays the time stamp by a non-negative, bounded
    amount: the stamp can never be earlier than the physical source event and
    never later than 4 destination cycles after it (2 flops + edge detect +
    one cycle of sampling uncertainty). Measured latency therefore lies in
    [true, true+4] cycles.
    """
    return true_cycles, true_cycles + 4


# ---------------------------------------------------------------------------
# 3. OSD layout (mirrored by the generated Verilog include osd_layout.vh)
# ---------------------------------------------------------------------------

OSD_COLS = 16
OSD_ROWS = 3
OSD_CELL_PX = GLYPH_COLS          # 8
OSD_SCALE_LOG2 = 1                # default: 2x, i.e. a 16x16 pixel cell
OSD_X0 = 24
OSD_Y0 = 24

# Character buffer layout, one string per row, OSD_COLS characters each.
# '#' marks a field that latency_osd.v rewrites every frame; the character in
# the template is only the power-on placeholder.
_TEMPLATE_ROWS = (
    "LAT-F ######MS  ",
    "LAT-P ######MS  ",
    "FRM ######## E# ",
)

FIELD_LAT_FRAME = 6      # index in the 48 byte buffer, 6 characters
FIELD_LAT_PIPE = 22      # 16 + 6
FIELD_FRAME = 36         # 32 + 4
FIELD_ERR = 46           # 32 + 14
FIELD_LEN_LAT = 6
FIELD_LEN_FRAME = 8
FIELD_LEN_ERR = 1

TEMPLATE = "".join(_TEMPLATE_ROWS)
assert len(TEMPLATE) == OSD_COLS * OSD_ROWS == 48

ERR_OVERFLOW = 0b0001     # time-stamp queue overflowed: pairing lost
ERR_UNDERFLOW = 0b0010    # destination event with no pending time stamp
ERR_CLAMPED = 0b0100      # latency exceeded the 5 digit field


def _digit(nibble: int) -> str:
    return "0123456789ABCDEF"[nibble & 0xF]


def format_latency_field(ticks: int, valid: bool) -> str:
    """Six characters ``DDD.DD`` from a tick value, or ``---.--`` when invalid.

    Leading zeros of the integer part are blanked (``"033.30"`` -> ``" 33.30"``);
    the units digit is always shown. Values above MAX_TICKS saturate at 999.99.
    """
    if not valid:
        return "---.--"
    value = MAX_TICKS if ticks > MAX_TICKS else (0 if ticks < 0 else ticks)
    digits = _decimal_digits(value, 5)   # digits[0] most significant
    out = []
    for position in range(3):            # integer part, positions 0..2
        if position < 2 and digits[position] == 0 and all(d == 0 for d in digits[:position + 1]):
            out.append(" ")
        else:
            out.append(_digit(digits[position]))
    out.append(".")
    out.append(_digit(digits[3]))
    out.append(_digit(digits[4]))
    return "".join(out)


def format_frame_field(frame_count: int) -> str:
    """Eight BCD digits of the frame counter, leading zeros kept."""
    value = frame_count % 100_000_000
    digits = _decimal_digits(value, 8)
    return "".join(_digit(d) for d in digits)


def format_err_field(err_nibble: int) -> str:
    return _digit(err_nibble)


def _decimal_digits(value: int, count: int) -> list[int]:
    """Most significant first list of ``count`` decimal digits."""
    value = max(0, int(value))
    out = [0] * count
    for index in range(count - 1, -1, -1):
        out[index] = value % 10
        value //= 10
    if value:
        raise ValueError("value needs more than %d digits" % count)
    return out


def clamp_ticks(ticks: int) -> tuple[int, bool]:
    """Clamp to the display range; returns (value, clamped)."""
    if ticks > MAX_TICKS:
        return MAX_TICKS, True
    return max(0, int(ticks)), False


def char_buffer(lat_frame_ticks: int, lat_pipe_ticks: int, frame_count: int,
                err_nibble: int = 0, frame_valid: bool = True,
                pipe_valid: bool = True) -> str:
    """Full 48 character OSD buffer exactly as latency_osd.v writes it."""
    buf = list(TEMPLATE)
    for start, text in (
        (FIELD_LAT_FRAME, format_latency_field(lat_frame_ticks, frame_valid)),
        (FIELD_LAT_PIPE, format_latency_field(lat_pipe_ticks, pipe_valid)),
        (FIELD_FRAME, format_frame_field(frame_count)),
        (FIELD_ERR, format_err_field(err_nibble)),
    ):
        for offset, ch in enumerate(text):
            buf[start + offset] = ch
    return "".join(buf)


def template_bits() -> int:
    """TEMPLATE as one 384 bit big-endian constant for the Verilog include.

    Byte 0 of the buffer is the most significant byte, matching
    ``OSD_TEMPLATE[(47 - index) * 8 +: 8]`` in the RTL.
    """
    value = 0
    for ch in TEMPLATE:
        value = (value << 8) | (ord(ch) & 0xFF)
    return value


# ---------------------------------------------------------------------------
# 4. Text overlay model (mirrors work/rtl/osd/text_overlay.v)
# ---------------------------------------------------------------------------

def cell_size(scale_log2: int = OSD_SCALE_LOG2) -> int:
    return OSD_CELL_PX << scale_log2


def overlay_mask(x: int, y: int, char_buf: str, x0: int = OSD_X0, y0: int = OSD_Y0,
                 scale_log2: int = OSD_SCALE_LOG2, cols: int = OSD_COLS,
                 rows: int = OSD_ROWS) -> bool | None:
    """Glyph coverage of one pixel.

    Returns True/False inside the text panel and None outside it (the RTL
    leaves those pixels untouched, ``panel_en`` draws the background).
    """
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


# ---------------------------------------------------------------------------
# 5. Self test (``python work/models/latency_osd_model.py --self-test``)
# ---------------------------------------------------------------------------

def _self_test() -> int:
    base, rem, mod = CLOCK_PRESETS["74.25MHz"][1:]
    edges = tick_edges(base, rem, mod, 2000)
    # Mean tick period must be exactly clk_hz/100000 = 742.5 cycles.
    total = edges[-1] - edges[0]
    mean = total / (len(edges) - 1)
    assert abs(mean - 742.5) < 0.02, mean
    assert tick_count_at(edges, edges[0]) == 1
    assert tick_count_at(edges, edges[0] - 1) == 0

    lat_ticks, lat_cycles = measured_latency(100, 100 + 3400, base, rem, mod)
    assert lat_cycles == 3397, lat_cycles
    # The tick field quantises to 10 us: the value equals the number of whole
    # tick boundaries crossed, which differs from cycles/742.5 by at most one
    # tick. lat_cycles carries the full resolution.
    assert abs(lat_ticks - 3397 / 742.5) <= 1.0, lat_ticks

    assert format_latency_field(3330, True) == " 33.30"
    assert format_latency_field(124, True) == "  1.24"
    assert format_latency_field(0, True) == "  0.00"
    assert format_latency_field(99999, True) == "999.99"
    assert format_latency_field(100000, True) == "999.99"
    assert format_latency_field(10, False) == "---.--"
    assert format_frame_field(1234) == "00001234"
    assert format_frame_field(99999999) == "99999999"

    buf = char_buffer(3330, 124, 1234, ERR_OVERFLOW | ERR_CLAMPED)
    assert len(buf) == 48
    assert buf[FIELD_LAT_FRAME:FIELD_LAT_FRAME + 6] == " 33.30"
    assert buf[FIELD_LAT_PIPE:FIELD_LAT_PIPE + 6] == "  1.24"
    assert buf[FIELD_FRAME:FIELD_FRAME + 8] == "00001234"
    assert buf[FIELD_ERR] == "5"
    assert template_bits().bit_length() <= 384

    # Glyph orientation: 'A' top row is 0x0C -> leftmost bits 2 and 3.
    assert glyph_rows("A")[0] == 0x0C
    assert glyph_pixel("A", 0, 2) == 1 and glyph_pixel("A", 0, 3) == 1
    assert glyph_pixel("A", 0, 0) == 0

    mask = overlay_mask(OSD_X0, OSD_Y0, buf, scale_log2=0)
    assert mask is True or mask is False
    assert overlay_mask(OSD_X0 - 1, OSD_Y0, buf) is None
    assert overlay_mask(OSD_X0, OSD_Y0 + OSD_ROWS * cell_size(), buf) is None

    print("latency_osd_model self-test: PASS")
    print("  tick mean period      : %.4f cycles (expected 742.5)" % mean)
    print("  field 3330 ticks      : %r" % format_latency_field(3330, True))
    print("  field 124 ticks       : %r" % format_latency_field(124, True))
    print("  frame 1234            : %r" % format_frame_field(1234))
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(_self_test())
    print(__doc__)

# ---------------------------------------------------------------------------
# 6. Clock-phase helpers for the cross-clock testbench
#
# The testbench generates every clock with ``always #(half) clk = ~clk`` from a
# starting value of 0, so the first rising edge of a clock is at time `half`
# and the following ones are spaced by the full period. Reset is held low and
# released at TB_RESET_RELEASE_NS, which makes the first rising edge after that
# instant edge number 1 of the meter. These helpers reproduce those times so
# the expected values of the cross-clock test can be computed exactly.
# ---------------------------------------------------------------------------

TB_RESET_RELEASE_NS = 40.0   # the testbenches hold reset for four clk falling edges (10 ns period)


def edge_times(half_period_ns: float, count: int,
               release_ns: float = TB_RESET_RELEASE_NS) -> list[float]:
    """Rising-edge times (ns) of edge 1..count, i.e. after the reset release."""
    period = 2.0 * half_period_ns
    times = []
    time = half_period_ns          # a clock that starts at 0 toggles at half first
    while len(times) < count:
        if time > release_ns:
            times.append(round(time, 6))
        time += period
    return times


def dest_cycle_of_time(time_ns: float, dest_half_ns: float,
                       release_ns: float = TB_RESET_RELEASE_NS) -> int:
    """Destination cycle number that contains ``time_ns`` (0 before edge 1)."""
    if time_ns <= release_ns:
        return 0
    period = 2.0 * dest_half_ns
    first = dest_half_ns
    while first <= release_ns:
        first += period
    return int((time_ns - first) // period) + 1


def stamp_cycle_for_flip(flip_time_ns: float, dest_half_ns: float,
                         release_ns: float = TB_RESET_RELEASE_NS) -> int:
    """Destination cycle in which the meter samples the crossed event.

    The toggle is visible from ``flip_time_ns`` on. The first destination edge
    *strictly after* that time loads it into the first synchroniser flop (cycle
    c1); the second flop and the edge detector publish it one cycle later, and
    the push happens on the following edge, so the time stamp holds the cycle
    counters of cycle c1+1.
    """
    period = 2.0 * dest_half_ns
    first = dest_half_ns
    while first <= release_ns:
        first += period
    if flip_time_ns <= release_ns:
        c1 = 0
    else:
        c1 = int((flip_time_ns - first) // period) + 1 + 1
    return c1 + 1


def cross_clock_expected(src_assert_ns: float, src_half_ns: float,
                         out_cycle: int, dest_half_ns: float,
                         tick_base: int, tick_remainder: int, tick_mod: int,
                         release_ns: float = TB_RESET_RELEASE_NS) -> tuple[int, int, float]:
    """Exact expected (lat_ticks, lat_cycles, flip_time) for the two-clock test.

    The source pulse is held for one source period minus 1 ns, so exactly one
    source rising edge lies inside it and the toggle flips once.
    """
    width = 2.0 * src_half_ns - 1.0
    edges = edge_times(src_half_ns, 4096, release_ns)
    window = [t for t in edges if src_assert_ns <= t < src_assert_ns + width]
    if len(window) != 1:
        raise ValueError("source pulse must contain exactly one rising edge")
    flip = window[0]
    stamp = stamp_cycle_for_flip(flip, dest_half_ns, release_ns)
    cycles = out_cycle - stamp
    if cycles < 0:
        raise ValueError("out_token precedes the stamped source event")
    ticks = tick_count_at(tick_edges(tick_base, tick_remainder, tick_mod, cycles + tick_base + 4),
                          out_cycle) - \
            tick_count_at(tick_edges(tick_base, tick_remainder, tick_mod, cycles + tick_base + 4),
                          stamp)
    return ticks, cycles, flip


def simulate_meter(dest_half_ns: float, src_half_ns: float, src_token_cycles,
                   out_cycles, tick_base: int, tick_remainder: int, tick_mod: int,
                   depth: int = 8, release_ns: float = TB_RESET_RELEASE_NS,
                   max_edges: int = 4096, end_cycle: int | None = None):
    """Cycle accurate model of latency_meter.v, including the toggle CDC.

    Both clocks are generated by the testbench as ``always #half clk = ~clk``
    from 0, and reset is released at ``release_ns``, so every edge time is
    known exactly. The simulation applies the RTL's nonblocking semantics at
    each edge in time order (a destination edge is applied before a source edge
    at the same instant, matching the single clock configuration where the
    toggle flop and the synchroniser flops are clocked by the same signal).

    Returns (results, err_overflow, err_underflow, info):
        results          out_token cycle -> (lat_ticks, lat_cycles) or None
        err_overflow     a push was dropped because the queue was full
        err_underflow    a pop found an empty queue
        info['pushes']   (push cycle, stamp cycle) of every accepted push
    """
    from collections import deque

    dest_edges = edge_times(dest_half_ns, max_edges, release_ns)
    src_edges = edge_times(src_half_ns, max_edges, release_ns)
    tokens = set(src_token_cycles)
    outs = set(out_cycles)

    # at an identical instant the destination edge is applied first: with one
    # clock the toggle flop and the synchroniser flops are clocked by the same
    # edge, so the synchroniser must sample the *old* toggle value
    events = []
    for index, time in enumerate(dest_edges, start=1):
        events.append((time, 0, 1, index))
    for index, time in enumerate(src_edges, start=1):
        events.append((time, 1, 0, index))
    events.sort(key=lambda item: (item[0], item[1]))

    tok = 0
    s1 = s2 = s3 = 0
    cycle = 0
    tick_run = 0
    tick_interval = tick_base
    tick_acc = 0
    tick_cnt = 0
    tick_at = {}                      # cycle -> tick counter value during that cycle
    tick_at[0] = 0

    queue = deque()
    pending_tick = deque()
    occupancy = 0
    results = {}
    err_overflow = False
    err_underflow = False
    pushes = []

    for _time, _order, kind, index in events:
        if kind == 0:                                   # source edge
            if (index - 1) in tokens:                   # token high during source cycle index-1
                tok ^= 1
            continue

        # ---- destination edge: cycle `cycle + 1` starts here ----
        if end_cycle is not None and cycle + 1 > end_cycle:
            break                                       # the testbench has finished
        prev = cycle                                    # cycle that just ended
        prev_tick = tick_cnt
        prev_occ = occupancy
        src_evt = s2 ^ s3                               # value sampled during cycle `prev`
        pop_now = (prev in outs) and (prev_occ > 0)
        wr_ok = (prev_occ < depth) or pop_now
        push_now = src_evt and wr_ok

        if src_evt and not wr_ok:
            err_overflow = True
        if (prev in outs) and (prev_occ == 0):
            err_underflow = True

        s1, s2, s3 = tok, s1, s2                        # synchroniser advances

        if pop_now:
            occupancy -= 1
            stamp = queue.popleft()
            stamp_tick = pending_tick.popleft()
            results[prev] = (prev_tick - stamp_tick, prev - stamp)
        elif prev in outs:
            results[prev] = None

        if push_now:
            queue.append(prev)                          # the counters of cycle `prev`
            pending_tick.append(prev_tick)
            pushes.append((cycle + 1, prev))
            occupancy += 1

        cycle += 1
        if tick_run >= tick_interval - 1:
            tick_cnt += 1
            tick_run = 0
            total = tick_acc + tick_remainder
            if total >= tick_mod:
                tick_acc = total - tick_mod
                tick_interval = tick_base + 1
            else:
                tick_acc = total
                tick_interval = tick_base
        else:
            tick_run += 1
        tick_at[cycle] = tick_cnt

    info = {"pushes": pushes, "dest_edges": len(dest_edges)}
    return results, err_overflow, err_underflow, info


def dim_rgb(rgb: int) -> int:
    """Half brightness of a 24 bit RGB word, bit exact with text_overlay.v."""
    red = (rgb >> 16) & 0xFF
    green = (rgb >> 8) & 0xFF
    blue = rgb & 0xFF
    return ((red >> 1) << 16) | ((green >> 1) << 8) | (blue >> 1)


def simulate_queue(stamp_cycles, out_cycles, tick_base: int, tick_remainder: int,
                   tick_mod: int, depth: int = 8):
    """Bit exact model of the meter's time-stamp queue.

    stamp_cycles : destination cycle in which each source event is stamped
                   (the queue write itself happens one cycle later)
    out_cycles   : destination cycles that carry out_token
    depth        : queue depth, matching DEPTH_LOG2 in latency_meter.v

    Returns (results, err_overflow, err_underflow) where results maps an
    out_token cycle to (lat_ticks, lat_cycles) or None when the queue was empty
    (in which case the RTL keeps the previous reading).
    """
    from collections import deque

    stamp_cycles = list(stamp_cycles)
    out_cycles = list(out_cycles)
    pops = set(out_cycles)
    # a pop is evaluated against the occupancy at the start of the cycle, and a
    # write is accepted when the queue is not full *or* the same cycle pops
    events = sorted([(c + 1, 1, c) for c in stamp_cycles] + [(c, 0, c) for c in out_cycles],
                    key=lambda item: (item[0], item[1]))
    top = max(stamp_cycles + out_cycles + [1])
    edges = tick_edges(tick_base, tick_remainder, tick_mod, top + tick_base + 4)

    occupancy = 0
    queue = deque()
    results = {}
    err_overflow = False
    err_underflow = False
    for cycle, kind, payload in events:
        if kind == 0:
            if occupancy == 0:
                err_underflow = True
                results[payload] = None
            else:
                occupancy -= 1
                stamp = queue.popleft()
                results[payload] = (tick_count_at(edges, cycle) - tick_count_at(edges, stamp),
                                    cycle - stamp)
        else:
            if (occupancy == depth) and (cycle not in pops):
                err_overflow = True
            else:
                queue.append(payload)
                occupancy += 1
    return results, err_overflow, err_underflow


def output_hash_init() -> int:
    return 0


def output_hash_step(current: int, rgb: int) -> int:
    """32-bit running hash of the overlay output, identical in the testbench."""
    return ((current * 33) + rgb) & 0xFFFFFFFF
