"""Algorithm Lab plugin: latency OSD panel (latency measurement read-out).

Thin NumPy adapter around work/models/latency_osd_model.py and
work/models/latency_osd_preview.py, which are also the golden models used by the
RTL testbench. The visual reference renders the glyphs with a 3x3 supersampled
coverage blend; the hardware equivalent is the exact 1-bit glyph mask with the
LSB-truncating half brightness of work/rtl/osd/text_overlay.v.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from plugins.base import BaseAlgorithm

MODELS = Path(__file__).resolve().parents[2] / "models"
if str(MODELS) not in sys.path:
    sys.path.insert(0, str(MODELS))

import latency_osd_model as model  # noqa: E402


def _layout(params):
    return (int(params.get("x0", model.OSD_X0)), int(params.get("y0", model.OSD_Y0)),
            int(params.get("scale_log2", model.OSD_SCALE_LOG2)))


def _buffer(params):
    return model.char_buffer(int(round(float(params.get("lat_frame_ms", 33.30)) * model.TICKS_PER_MS)),
                             int(round(float(params.get("lat_pipe_ms", 1.24)) * model.TICKS_PER_MS)),
                             int(params.get("frame_index", 0)),
                             int(params.get("err_nibble", 0)))


def _panel_mode(params):
    mode = params.get("panel", "dim")
    return (mode != "none", mode == "dim")


class LatencyOsdAlgorithm(BaseAlgorithm):
    algorithm_id = "latency_osd"
    display_name = "Latency OSD (延迟测量与显示)"
    category = "Overlay"
    description = ("Draws the end-to-end latency read-out (frame latency, pipeline "
                   "latency, frame counter, sticky error nibble) on the video stream.")
    source_reference = "work/models/latency_osd_model.py, font8x8 (public domain)"
    license = "MIT (plugin), public domain (font)"

    def get_parameter_specs(self) -> list[dict]:
        return [
            {"id": "lat_frame_ms", "label": "Frame latency (ms)", "type": "float",
             "default": 33.30, "min": 0.0, "max": 999.99, "step": 0.01},
            {"id": "lat_pipe_ms", "label": "Pipeline latency (ms)", "type": "float",
             "default": 1.24, "min": 0.0, "max": 999.99, "step": 0.01},
            {"id": "frame_index", "label": "Frame counter", "type": "int",
             "default": 12345, "min": 0, "max": 99999999, "step": 1},
            {"id": "x0", "label": "Panel X", "type": "int", "default": model.OSD_X0,
             "min": 0, "max": 1000, "step": 8},
            {"id": "y0", "label": "Panel Y", "type": "int", "default": model.OSD_Y0,
             "min": 0, "max": 600, "step": 8},
            {"id": "scale_log2", "label": "Glyph scale", "type": "select", "default": 1,
             "options": [{"value": 0, "label": "1x (8x8)"}, {"value": 1, "label": "2x (16x16)"},
                         {"value": 2, "label": "4x (32x32)"}]},
            {"id": "panel", "label": "Panel background", "type": "select", "default": "dim",
             "options": [{"value": "dim", "label": "Half brightness video"},
                         {"value": "solid", "label": "Solid black"},
                         {"value": "none", "label": "Glyphs only"}]},
            {"id": "err_nibble", "label": "Error nibble (hex)", "type": "int",
             "default": 0, "min": 0, "max": 15, "step": 1},
        ]

    # -- visual reference: supersampled coverage blend ----------------------
    def process_visual_reference(self, image_rgb: np.ndarray, params: dict):
        buffer = _buffer(params)
        x0, y0, scale_log2 = _layout(params)
        panel_en, bg_dim = _panel_mode(params)
        out = image_rgb.copy()
        height, width = image_rgb.shape[:2]
        cell = model.cell_size(scale_log2)
        steps = 3
        for y in range(max(0, y0), min(height, y0 + model.OSD_ROWS * cell)):
            for x in range(max(0, x0), min(width, x0 + model.OSD_COLS * cell)):
                hits = 0
                for sy in range(steps):
                    for sx in range(steps):
                        px = x + (2 * sx + 1) / (2.0 * steps)
                        py = y + (2 * sy + 1) / (2.0 * steps)
                        if model.overlay_mask(int(px), int(py), buffer, x0, y0, scale_log2):
                            hits += 1
                coverage = hits / float(steps * steps)
                base = out[y, x].astype(np.float32)
                if panel_en:
                    base = base * 0.5 if bg_dim else np.zeros(3, np.float32)
                blended = base * (1.0 - coverage) + np.float32(255.0) * coverage
                out[y, x] = np.clip(blended, 0, 255).astype(np.uint8)
        metrics = {"text": [buffer[i * model.OSD_COLS:(i + 1) * model.OSD_COLS]
                            for i in range(model.OSD_ROWS)],
                   "note": "supersampled glyph coverage, floating point blend"}
        return out, metrics

    # -- hardware equivalent: exact 1-bit mask and truncated half brightness --
    def process_hardware_equivalent(self, image_rgb: np.ndarray, params: dict):
        buffer = _buffer(params)
        x0, y0, scale_log2 = _layout(params)
        panel_en, bg_dim = _panel_mode(params)
        out = image_rgb.copy()
        height, width = image_rgb.shape[:2]
        cell = model.cell_size(scale_log2)
        for y in range(max(0, y0), min(height, y0 + model.OSD_ROWS * cell)):
            for x in range(max(0, x0), min(width, x0 + model.OSD_COLS * cell)):
                region = (x0 <= x < x0 + model.OSD_COLS * cell
                          and y0 <= y < y0 + model.OSD_ROWS * cell)
                if not region or not panel_en:
                    continue
                if model.overlay_mask(x, y, buffer, x0, y0, scale_log2):
                    out[y, x] = (255, 255, 255)
                elif bg_dim:
                    out[y, x] = (int(out[y, x, 0]) >> 1, int(out[y, x, 1]) >> 1,
                                 int(out[y, x, 2]) >> 1)
                else:
                    out[y, x] = (0, 0, 0)
        metrics = {"text": [buffer[i * model.OSD_COLS:(i + 1) * model.OSD_COLS]
                            for i in range(model.OSD_ROWS)],
                   "note": "bit exact model of work/rtl/osd/text_overlay.v"}
        return out, metrics
