#!/usr/bin/env python3
"""Render the latency OSD panel on a synthetic video frame (stage B/C preview).

This is the software-side visual preview for the latency display deliverable.
It uses the same golden model as the RTL (work/models/latency_osd_model.py), so
what is drawn here is exactly what the hardware draws, character for character.

No third party package is required: the PNG is encoded with zlib from the
standard library. If Pillow is available, --background loads a real image
instead of the synthetic test scene.

Examples
    python work/models/latency_osd_preview.py --out work/output/latency-osd/preview.png
    python work/models/latency_osd_preview.py --lat-frame 3330 --lat-pipe 124 --frame 1234
    python work/models/latency_osd_preview.py --background some_photo.jpg --out preview.png
"""
from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import latency_osd_model as model  # noqa: E402


# ---------------------------------------------------------------------------
# PNG output (standard library only)
# ---------------------------------------------------------------------------

def write_png(path: Path, width: int, height: int, rows: list[bytes]) -> None:
    raw = b"".join(b"\x00" + row for row in rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


# ---------------------------------------------------------------------------
# synthetic "camera" scene
# ---------------------------------------------------------------------------

BARS = (
    (180, 180, 180), (180, 180, 0), (0, 180, 180), (0, 180, 0),
    (180, 0, 180), (180, 0, 0), (0, 0, 180), (30, 30, 30),
)


def scene_pixel(x: int, y: int, width: int, height: int) -> tuple[int, int, int]:
    """Deterministic stand-in for a camera picture: colour bars, a brightness
    ramp and two grey objects, so the panel and the video behind it are both
    clearly visible in the preview."""
    bar = BARS[(x * len(BARS)) // width]
    ramp = 90 + (200 * y) // max(1, height - 1)
    red = (bar[0] * ramp) // 255
    green = (bar[1] * ramp) // 255
    blue = (bar[2] * ramp) // 255
    # two soft grey boxes, so the half brightness of the panel is obvious
    if (width // 6 <= x < width // 3) and (height // 3 <= y < (2 * height) // 3):
        red = green = blue = 210
    if ((2 * width) // 3 <= x < (5 * width) // 6) and (height // 4 <= y < height // 2):
        red = green = blue = 60
    return red, green, blue


# ---------------------------------------------------------------------------
# renderer (mirrors work/rtl/osd/text_overlay.v)
# ---------------------------------------------------------------------------

def render(width: int, height: int, char_buf: str, x0: int, y0: int, scale_log2: int,
           fg: tuple[int, int, int], bg: tuple[int, int, int], bg_dim: bool,
           panel_en: bool, background: str | None) -> list[bytes]:
    cell = model.cell_size(scale_log2)
    region = (x0, y0, x0 + model.OSD_COLS * cell, y0 + model.OSD_ROWS * cell)

    field = None
    if background:
        try:
            from PIL import Image
        except ImportError:
            raise SystemExit("--background needs Pillow (pip install pillow)")
        image = Image.open(background).convert("RGB").resize((width, height))
        field = image.load()

    fg_word = (fg[0] << 16) | (fg[1] << 8) | fg[2]
    bg_word = (bg[0] << 16) | (bg[1] << 8) | bg[2]
    rows: list[bytes] = []
    for y in range(height):
        row = bytearray()
        in_rows = region[1] <= y < region[3]
        for x in range(width):
            if field is not None:
                red, green, blue = field[x, y]
            else:
                red, green, blue = scene_pixel(x, y, width, height)
            if in_rows and region[0] <= x < region[2]:
                mask = model.overlay_mask(x, y, char_buf, x0, y0, scale_log2)
                if mask:
                    red, green, blue = fg_word >> 16, (fg_word >> 8) & 0xFF, fg_word & 0xFF
                elif panel_en:
                    if bg_dim:
                        red, green, blue = red >> 1, green >> 1, blue >> 1
                    else:
                        red, green, blue = bg_word >> 16, (bg_word >> 8) & 0xFF, bg_word & 0xFF
            row += bytes((red, green, blue))
        rows.append(bytes(row))
    return rows


def crop(rows: list[bytes], width: int, x0: int, y0: int, w: int, h: int) -> list[bytes]:
    out = []
    for y in range(y0, min(y0 + h, len(rows))):
        line = rows[y]
        start = max(0, x0) * 3
        out.append(line[start:start + w * 3])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="work/output/latency-osd/preview.png")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--lat-frame", type=int, default=3330, help="frame latency, 0.01 ms units")
    parser.add_argument("--lat-pipe", type=int, default=124, help="pipeline latency, 0.01 ms units")
    parser.add_argument("--frame", type=int, default=12345)
    parser.add_argument("--err", type=int, default=0, help="error nibble 0..15")
    parser.add_argument("--x0", type=int, default=model.OSD_X0)
    parser.add_argument("--y0", type=int, default=model.OSD_Y0)
    parser.add_argument("--scale-log2", type=int, default=model.OSD_SCALE_LOG2)
    parser.add_argument("--no-panel", action="store_true", help="glyphs only, no background panel")
    parser.add_argument("--solid-bg", action="store_true", help="solid panel instead of dimming")
    parser.add_argument("--background", default=None)
    parser.add_argument("--dump-text", action="store_true")
    args = parser.parse_args()

    buffer = model.char_buffer(args.lat_frame, args.lat_pipe, args.frame, args.err)
    for index in range(model.OSD_ROWS):
        print("|%s|" % buffer[index * model.OSD_COLS:(index + 1) * model.OSD_COLS])
    if args.dump_text:
        return 0

    rows = render(args.width, args.height, buffer, args.x0, args.y0, args.scale_log2,
                  (255, 255, 255), (0, 0, 0), not args.solid_bg, not args.no_panel,
                  args.background)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_png(out, args.width, args.height, rows)
    print("wrote %s (%dx%d)" % (out, args.width, args.height))

    cell = model.cell_size(args.scale_log2)
    zoom = crop(rows, args.width, args.x0 - 8, args.y0 - 8,
                model.OSD_COLS * cell + 16, model.OSD_ROWS * cell + 16)
    zoom_out = out.with_name(out.stem + "-panel.png")
    write_png(zoom_out, model.OSD_COLS * cell + 16, len(zoom), zoom)
    print("wrote %s" % zoom_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
