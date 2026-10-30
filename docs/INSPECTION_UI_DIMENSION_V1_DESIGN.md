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

User supplied photos of T plates, rectangular plates, corner brackets,
hinges, white plastic brackets and a circular black component. Start with
one thin flat plate on a plain matte contrasting background; wooden grain,
specular highlights, raised brackets and cylindrical hinges are unsuitable
for an unqualified planar accuracy claim. Phone photos are geometry/use-case
evidence, not captured FPGA RGB or dimensional ground truth.
User has a 45 cm T-square; use a known 100 mm interval of that ruler on the
workpiece plane for each axis. Do not require a purchased calibration target.
Pixel spans and calibration must be explicit; no guessed mm-per-pixel.
Camera perpendicular to the plane, fixed position/focus/height. No claim of
perspective/lens-distortion correction, arbitrary CAD fitting or precision
beyond real ruler-based board validation. Thin planar objects only.

SW1 selects dimension display, taking priority over color if both are on.
SW2 selects dark(0)/bright(1) silhouette in RUN; X(0)/Y(1) axis in CAL.
SW3 selects ruler calibration. In CAL, K2 short decreases the selected
pixel interval by 4; hold increases by 4 and repeats at nominal 10 Hz after
0.7 s. X spans 16..736 px, Y 16..352 px. Initial interval 256 px is NOT a
calibration. Put two ruler ticks exactly 100 mm apart at the guide end
marks; adjust X then rotate/position ruler and adjust Y without moving
camera. Visit both axes, then SW3 OFF explicitly confirms. Disabling SW1
during calibration does not confirm. Reset clears calibration; camera,
focus or work plane movement requires recalibration. Confirmation asserts
operator alignment, not automatic verification of ruler marks.

Dimensions use all 1280 source samples per row. Working ROI is x256..1023,
y160..543. Reuse existing RGB luma/binary mask, with the existing BINARY
threshold; select BINARY with K3 and adjust K4 to tune silhouette. K3/K4
semantics are unchanged. Reject horizontal runs shorter than 3 pixels and
rows with fewer than 8 qualified pixels; require >=3 accepted rows and
>=64 pixels. A silhouette touching the working ROI boundary is invalid.
At most ONE isolated workpiece in the working ROI: multiple parts merge.
This is a conditional silhouette measurement, not general object recognition.

SIZE W/H are axis-aligned outer extents, not rotation-invariant CAD lengths.
GAPX/GAPY are background spans between qualified foreground runs through
fixed x640/y352 crosshair, with 3 central pixels required to be background.
They can measure an opening or slot cross-section. Only a centered circular
hole justifies interpreting both equal spans as inner diameter; there is no
automatic circle fit, multi-hole discovery, center finding or topology proof.
Outer spans approximate a circle's outer diameter only for a flat circle.
For a T plate, SIZE measures overall width/height, not all branch lengths.

The screen shows pixel units until calibration. Afterwards each axis uses
round(pixels*1000/calibration_pixels) tenths of mm with a shared serial
divider. Decimal resolution 0.1 mm is NOT demonstrated measurement accuracy.
No universal combinational division or extra frame storage. The constant
scale multiplication is left to TD mapping; actual DSP usage is reported
from the final implementation rather than assumed zero. Per-frame
results refer to the preceding complete sample (LAST), as color comparison
does; moving objects have one capture-frame measurement age, not same-frame
tracking. Blank/clipped/malformed result prints dashes/NO VALID OBJECT.
Full-frame geometry is checked and invalid data never gates video writes.

K3/K4 five-mode and threshold semantics stay unchanged. Dimension
measurements must use real pre-effect RGB/luma, not rendered STYLE/EDGE pixels.
No new frame cache, video admission gate, PLL or SDC change is authorized.

Current candidate is resource-constrained (Slice19336/21216, setup +0.000ns).
Full regression and routed STA are required before any new candidate bit.
Source checkpoints and actual TD source commit will be tracked separately.
