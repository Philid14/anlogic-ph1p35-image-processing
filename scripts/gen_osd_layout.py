#!/usr/bin/env python3
"""Generate the Verilog OSD layout include from the Python golden model.

Single source of truth : work/models/latency_osd_model.py
Generated output       : work/rtl/osd/osd_layout.vh

Keeping the character buffer template and the field indices in one place means
the on-screen preview and the RTL cannot silently drift apart.

Usage:
    python scripts/gen_osd_layout.py
    python scripts/gen_osd_layout.py --check
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "work/models"))

import latency_osd_model as model  # noqa: E402


def render() -> str:
    bits = model.template_bits()
    hex_width = (model.OSD_COLS * model.OSD_ROWS * 8 + 3) // 4
    lines = [
        "//======================================================================",
        "// osd_layout.vh - latency OSD character buffer layout",
        "//",
        "// GENERATED FILE - do not edit by hand.",
        "//   generator : scripts/gen_osd_layout.py",
        "//   model     : work/models/latency_osd_model.py",
        "//",
        "// The template holds the static text of the panel; '#' field positions are",
        "// rewritten every frame by latency_osd.v. Byte 0 of the buffer is the most",
        "// significant byte of OSD_TEMPLATE.",
        "//======================================================================",
        "localparam integer OSD_COLS = %d;" % model.OSD_COLS,
        "localparam integer OSD_ROWS = %d;" % model.OSD_ROWS,
        "localparam [%d:0] OSD_BUF_BITS = %d'd%d;" % (
            (model.OSD_COLS * model.OSD_ROWS * 8 - 1),
            (model.OSD_COLS * model.OSD_ROWS * 8),
            48),
        "localparam [%d:0] OSD_TEMPLATE = %d'h%0*s;" % (
            (model.OSD_COLS * model.OSD_ROWS * 8 - 1),
            (model.OSD_COLS * model.OSD_ROWS * 8),
            hex_width,
            "%X" % bits),
        "",
    ]
    for name, value, comment in (
        ("OSD_FLD_LAT_FRAME", model.FIELD_LAT_FRAME, "row 0 latency field, 6 characters"),
        ("OSD_FLD_LAT_PIPE", model.FIELD_LAT_PIPE, "row 1 pipeline field, 6 characters"),
        ("OSD_FLD_FRAME", model.FIELD_FRAME, "row 2 frame counter, 8 characters"),
        ("OSD_FLD_ERR", model.FIELD_ERR, "row 2 sticky error nibble, 1 character"),
        ("OSD_FLD_LAT_LEN", model.FIELD_LEN_LAT, "latency field length"),
        ("OSD_FLD_FRAME_LEN", model.FIELD_LEN_FRAME, "frame field length"),
        ("OSD_FLD_ERR_LEN", model.FIELD_LEN_ERR, "error field length"),
    ):
        lines.append("localparam [5:0] %s = 6'd%d;  // %s" % (name, value, comment))
    lines.append("")
    lines.append("// %s" % _ascii_comment())
    lines.append("")
    return "\n".join(lines)


def _ascii_comment() -> str:
    parts = []
    for row in range(model.OSD_ROWS):
        text = model.TEMPLATE[row * model.OSD_COLS:(row + 1) * model.OSD_COLS]
        parts.append('"%s"' % text)
    return "template rows: " + " ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    out = ROOT / "work/rtl/osd/osd_layout.vh"
    text = render()
    if out.exists() and out.read_text(encoding="utf-8") == text:
        print("osd_layout.vh up to date")
        return 0
    if args.check:
        print("STALE: %s" % out.relative_to(ROOT).as_posix(), file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s" % out.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
