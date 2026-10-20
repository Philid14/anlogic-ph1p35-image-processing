#!/usr/bin/env python3
"""Generate rtl/osd_layout.vh from model/latency_model.py.

Usage: python model/gen_osd_layout.py [--check]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FEAT = HERE.parent
sys.path.insert(0, str(HERE))
import latency_model as m  # noqa: E402


def render() -> str:
    bits = m.template_bits()
    nbits = m.OSD_COLS * m.OSD_ROWS * 8
    hexw = (nbits + 3) // 4
    lines = [
        "//======================================================================",
        "// osd_layout.vh - latency_view panel layout (GENERATED, do not edit)",
        "//   generator: model/gen_osd_layout.py",
        "//   model    : model/latency_model.py",
        "//   rows     : LAT / AGE / CAP fps / DSP fps / FRM + alarm nibble",
        "//======================================================================",
        "localparam integer OSD_COLS = %d;" % m.OSD_COLS,
        "localparam integer OSD_ROWS = %d;" % m.OSD_ROWS,
        "localparam [%d:0] OSD_TEMPLATE = %d'h%0*s;" % (nbits - 1, nbits, hexw, "%X" % bits),
        "",
    ]
    for name, value, comment in (
        ("OSD_FLD_LAT", m.FIELD_LAT, "row0 latency, 6 chars"),
        ("OSD_FLD_AVG", m.FIELD_AVG, "row1 average latency, 6 chars"),
        ("OSD_FLD_AGE", m.FIELD_AGE, "row2 image age, 6 chars"),
        ("OSD_FLD_CAP", m.FIELD_CAP, "row3 capture fps, 5 chars"),
        ("OSD_FLD_DSP", m.FIELD_DSP, "row4 display fps, 5 chars"),
        ("OSD_FLD_FRM", m.FIELD_FRM, "row5 frame counter, 8 chars"),
        ("OSD_FLD_ERR", m.FIELD_ERR, "row5 alarm nibble, 1 char"),
        ("OSD_FLD_CNT", m.FIELD_CNT, "row6 first display count, 8 chars"),
        ("OSD_FLD_ALM_NIB", m.FIELD_ALM_NIB, "row7 alarm nibble, 1 char"),
        ("OSD_FLD_ALM_TXT", m.FIELD_ALM_TXT, "row7 alarm word, 8 chars"),
        ("OSD_LEN_MS", m.FIELD_LEN_MS, ""),
        ("OSD_LEN_FPS", m.FIELD_LEN_FPS, ""),
        ("OSD_LEN_FRM", m.FIELD_LEN_FRM, ""),
        ("OSD_LEN_CNT", m.FIELD_LEN_CNT, ""),
        ("OSD_LEN_ALM", m.FIELD_LEN_ALM, ""),
    ):
        lines.append("localparam [6:0] %s = 7'd%d;  // %s" % (name, value, comment))
    lines.append("")
    for row in range(m.OSD_ROWS):
        text = m.TEMPLATE[row * m.OSD_COLS:(row + 1) * m.OSD_COLS]
        lines.append('// row %d: "%s"' % (row, text))
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    out = FEAT / "rtl/osd_layout.vh"
    text = render()
    if out.exists() and out.read_text(encoding="utf-8") == text:
        print("osd_layout.vh up to date")
        return 0
    if a.check:
        print("STALE: %s" % out.relative_to(FEAT).as_posix(), file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print("wrote rtl/osd_layout.vh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
