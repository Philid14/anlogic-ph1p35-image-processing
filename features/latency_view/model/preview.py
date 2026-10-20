#!/usr/bin/env python3
"""Render the latency panel over a synthetic video frame (demo / PPT asset).

Standard library only: the PNG is encoded with zlib, the glyphs come from
model/latency_model.py, so the preview is exactly the RTL panel layout.

    python model/preview.py --out .build/preview.png
    python model/preview.py --lat 3330 --avg 3342 --age 6660 --cap 30 --dsp 60 \
        --frame 12345 --cnt 4321 --err 1 --out .build/preview.png
"""
from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import latency_model as model  # noqa: E402

BARS = ((180, 180, 180), (180, 180, 0), (0, 180, 180), (0, 180, 0),
        (180, 0, 180), (180, 0, 0), (0, 0, 180), (30, 30, 30))


def write_png(path: Path, width: int, height: int, rows) -> None:
    raw = b"".join(b"\x00" + row for row in rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def scene(x: int, y: int, w: int, h: int):
    bar = BARS[(x * len(BARS)) // w]
    ramp = 90 + (200 * y) // max(1, h - 1)
    r, g, b = (bar[0] * ramp) // 255, (bar[1] * ramp) // 255, (bar[2] * ramp) // 255
    if (w // 6 <= x < w // 3) and (h // 3 <= y < 2 * h // 3):
        r = g = b = 210
    if (2 * w // 3 <= x < 5 * w // 6) and (h // 4 <= y < h // 2):
        r = g = b = 60
    return r, g, b


def render(width, height, buf, x0, y0, scale_log2, fg=(255, 255, 255), bg_dim=True):
    cell = model.cell_size(scale_log2)
    x1, y1 = x0 + model.OSD_COLS * cell, y0 + model.OSD_ROWS * cell
    rows = []
    for y in range(height):
        row = bytearray()
        in_rows = y0 <= y < y1
        for x in range(width):
            r, g, b = scene(x, y, width, height)
            if in_rows and x0 <= x < x1:
                if model.overlay_mask(x, y, buf, x0, y0, scale_log2):
                    r, g, b = fg
                elif bg_dim:
                    r, g, b = r >> 1, g >> 1, b >> 1
            row += bytes((r, g, b))
        rows.append(bytes(row))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".build/preview.png")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--lat", type=int, default=3330)
    ap.add_argument("--avg", type=int, default=3342)
    ap.add_argument("--age", type=int, default=6660)
    ap.add_argument("--cap", type=int, default=30)
    ap.add_argument("--dsp", type=int, default=60)
    ap.add_argument("--frame", type=int, default=12345)
    ap.add_argument("--cnt", type=int, default=4321)
    ap.add_argument("--err", type=int, default=0)
    ap.add_argument("--x0", type=int, default=model.OSD_X0)
    ap.add_argument("--y0", type=int, default=model.OSD_Y0)
    ap.add_argument("--scale-log2", type=int, default=model.OSD_SCALE_LOG2)
    a = ap.parse_args()

    buf = model.char_buffer(a.lat, a.avg, a.age, a.cap, a.dsp, a.frame, a.cnt, a.err)
    for i in range(model.OSD_ROWS):
        print("|%s|" % buf[i * model.OSD_COLS:(i + 1) * model.OSD_COLS])

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = render(a.width, a.height, buf, a.x0, a.y0, a.scale_log2)
    write_png(out, a.width, a.height, rows)
    print("wrote", out)

    cell = model.cell_size(a.scale_log2)
    zw, zh = model.OSD_COLS * cell + 16, model.OSD_ROWS * cell + 16
    zrows = [rows[y][(a.x0 - 8) * 3:(a.x0 - 8 + zw) * 3] for y in range(a.y0 - 8, a.y0 - 8 + zh)]
    zoom = out.with_name(out.stem + "-panel.png")
    write_png(zoom, zw, zh, zrows)
    print("wrote", zoom)


if __name__ == "__main__":
    main()
