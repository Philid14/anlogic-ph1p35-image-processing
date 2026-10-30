# INSPECTION_UI_DIMENSION_V1

Role MAIN / 2026-10-30. Base 1cc05016eaef482a87f31bd37bc20a9aae541689,
COLOR_COMPARE_V1, Draft PR #17 -> #13 -> #12, none merged by this task.
User authorizes color overlay switch, transparent uniform-font status and
the planar workpiece measurement described in 最终作品实现/关于最终作品实现.txt.
Keep the color means/classification/tolerance exactly. No height measurement.

## Checkpoint 1: user interface

- Four level switches SW0..3 verified against local HX1P35B_FT_40P sheets
  3/9 (files _3.pdf/_8.pdf): A4/B4/E11/D11, 3.3 V, selector to 3.3 V or GND.
  K2/KEY1 is A9 active-low, 3.3 V; existing K3 B9/K4 C7 remain unchanged.
  Do not use K1/KEY0, whose pull-up supply is 1.5 V.
- SW0 controls both color sampling outlines and all four result lines.
  Controls synchronize/debounce in CSI domain; display changes only at SOF.
- Transparent empty glyph pixels in comparison and MODE/THRESHOLD/B/S;
  unmodified original RGB passes through instead of a black rectangle.
- Original uniform 5x7 ASCII glyphs in the existing 16x16 interface, uniform
  stroke/cell size for A-Z, 0-9, punctuation. Preserve Chinese 安路 bitmaps,
  Logo ROM, CNT behavior. Generator is repository-native, no external font code.
- 3 complete 720p overlay frames / 691200 four-pixel beats compared to an
  independent pixel model, off/on/off plus changes during a frame: PASS.
  Asynchronous switch bounce, short/long K2 and reset: PASS.
  This checkpoint is a source/test checkpoint, not a separately generated bit.

## Planar measurement boundary

Await supplied workpiece pictures for actual segmentation suitability.
User has a 45 cm T-square; use a known 100 mm interval of that ruler on the
workpiece plane for each axis. Do not require a purchased calibration target.
Pixel spans and calibration must be explicit; no guessed mm-per-pixel.
Camera perpendicular to the plane, fixed position/focus/height. No claim of
perspective/lens-distortion correction, arbitrary CAD fitting or precision
beyond real ruler-based board validation. Thin planar objects only.

SW1 reserves dimension display enable. SW2/SW3 reserve foreground/calibration
controls. K3/K4 five-mode and threshold semantics stay unchanged. Dimension
measurements must use real pre-effect RGB/luma, not rendered STYLE/EDGE pixels.
No new frame cache, video admission gate, PLL or SDC change is authorized.

Current candidate is resource-constrained (Slice19336/21216, setup +0.000ns).
Full regression and routed STA are required before any new candidate bit.
Source checkpoints and actual TD source commit will be tracked separately.
