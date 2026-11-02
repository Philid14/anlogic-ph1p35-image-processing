# TRACK_REGION_FIX_V1 — MAIN integration fix

2026-11-02. Role MAIN. User authorization: latest TRACK board failure report,
green outline almost full-screen with and without a stationary red cap.
Base: `4d0f779cefd680363b8a3f0d4d5c33a42d81197f`, branch
`codex/main/inspection-shape-track-v1`, Draft PR #28 (not merged).
Task branch: `codex/main/track-region-fix-v1`, dependent Draft PR; no merges.

## Evidence and scope

The photograph is board feedback, **not sensor RGB**. X=0x27f/Y=0x167 is the
full-frame center, consistent with distant outliers expanding global extrema.
Code confirms old MAIN sends every red hit to one global bounding box; only
64 total hits are required. Old tests used clean blue-gray backgrounds and
did not exercise this failure. Exact in-situ pixel contributions remain unmeasured.

The independent synthetic test reproduces the old RTL failure: at160x120,
644 scattered red hits with no object produce xmin0/xmax159/ymin0/ymax119.
Warm neutral RGB208/192/176 also passes the old hue30/chroma24 classifier.
The new same-input tests reject both; a24x24 red target amid outliers yields
40..63/32..55,576 support pixels, rather than a full-frame box.

Only compiled `vision_source_observer.v` changes. The MAIN-owned adapter
contains the new spatial selector. TARGET's classifier, statistics, tracking
guard and all teammate files remain byte-identical. The original statistics
module remains archived and in the source list but is no longer instantiated.
Notice to TARGET: MAIN admission/result semantics change as described below;
this does not claim a new TARGET standalone release or teammate approval.
Sensor/AWB, pixel path, UI, seven modes, switches, dimensions, color comparison,
MOTION, DDR/MIPI/HDMI, PLL/pins/SDC and old archived bits are frozen.

## Implementation and interface semantics

1. Existing red hue±30°,chroma>=24,max>=32 predicate is retained. MAIN additionally
   requires G and B <= R-floor(R/4), rejecting warm near-neutral highlights.
   This may reject very pale pink/low-saturation red, intentionally.
2. Each aligned4-pixel group needs at least3 red hits. Each row retains only
   its longest uninterrupted run, at least2 groups=8px.
3. Consecutive selected rows join only if their spans overlap or are within
   one group=4px. A chain needs at least4 rows and64 support pixels.
4. Select the chain with the greatest support area; tie retains the earlier
   chain. No frame RAM, line RAM, division, DSP or backpressure is introduced.
5. X is quantized to4-pixel groups; boundary uncertainty of the mask is up to
   a group, in addition to input/classification uncertainty. Y is source-row.
   N now means **selected chain support area**,4 times accepted run groups,
   not all raw classified red pixels and not an exact geometric object area.
6. X/Y remain the bbox center, not a centroid. FRAME is source frame identity.
   LAST means last completed observation, possibly one capture frame behind
   the moving image; this is not new DDR/display identity matching.
7. Existing authoritative source geometry/abort/session validation qualifies
   results. The selector publishes after the final-row stage; MAIN reads it
   two clocks after EOF, one clock later than before. Common video latency
   stays31 clocks. Guard acquisition, stale handling and disappearance semantics
   remain; no target immediately disables the displayed bbox.

## Limits and validation

This is a low-cost, single main solid-red-region selector, **not general CCL**.
Only the longest run per row is retained. Hollow red rings, narrow lines,
strong glare splitting a target, red/skin-colored clutter and competing similarly
sized red objects can cause undercoverage or selection changes. A solid matte
red cap against non-red background is the acceptance target. It cannot infer
semantic object identity or recover color lost to clipping/ISP.

`tests/run_track_region.py` independently models classification, runs and chains,
then checks native ModelSim RTL. `--full` checks1280x720 including bottom-right
last-beat object and full-frame red count921600. Both SOF forms, valid gaps,
no blank line clocks, disappearance, borders and malformed stream are covered.
The old committed RTL must fail the identical noise vectors; failure logs are
preserved. Existing native12-group regression is rerun to a new evidence folder.
Formal build driver freezes88/89 actual inputs and all old bits against PR28;
SYN/PHY/STA/bitgen gates reject area/timing failure and stale bit reuse.

Physical board success is pending. Synthetic improvement does not prove all
camera backgrounds will work. Do not increase confidence based on simulation
alone; use empty-plane/target/move/remove board comparison and check artifacts.
