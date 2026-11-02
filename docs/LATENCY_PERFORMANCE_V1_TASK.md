# LATENCY_PERFORMANCE_V1 / MAIN

User authorization: add end-to-end latency visualization to the current candidate,
continue performance/resource optimization, preserve every existing function.
Base072bc0f8858ceb3009659f8df7cb02b9da05ed36 / TRACK_REGION_FIX_V1 / Draft PR29.
Branch codex/main/latency-performance-v1. No merge or main push authorization.

Read AGENTS.md, TEAM_PROTOCOL_V1 and original contest PDF16-18. Role MAIN.
LATENCY PR5 is unmerged at87bb9a5375843c4f3e9696eb0dbd028f3e364f47.
Its interface semantics are the reference; do not edit teammate directories or
assume that simulation-only completion/display events already exist in hardware.

Plan and independent checkpoints:
1. Bit-exact memory scheduling: coalesce the two four-hop row memories into
   one native dual-port RAM per hop; preserve3 clocks/hop. Investigate exact
   shared RGB/gray payload delays if more LUT savings are needed. No algorithm,
   border, threshold, throughput, valid/SOF/last or common31-cycle change.
2. MAIN latency adapter: timestamp first valid decoded RAW pixel entering ISP;
   bind identity/time to the actual packed data crossing the write FIFO; validate
   exact DDR user transaction size/address and source error/overflow status.
   Snapshot selected slot generation at real read selection. Distinguish first
   display and repeats, and reject missing/incomplete/overwritten/reset data.
3. Transparent shared-font OSD in currently free top area. Measure first valid
   pixel at HDMI input, in0.01ms units with configured75MHz reference; report
   quantization/CDC bounds and configured versus physically calibrated frequency.
4. Independent model/native FIFO+RAM+read/write integration and old functionality
   regression, followed by SYN/PHY/final STA/bitgen, immutable archive/tag/Draft PR
   depending on29. Actual resource/timing, not standalone estimates, decide release.

Frozen: Sensor/BLC/AWB, all seven algorithms and applications, K3/K4/switch
semantics, Logo/CNT/old OSD, resolution, clocks, pins, SDC and vendor PHY/DDR IP.
MAIN may add observational ports to video_in/video_out/top/mixer. No added image
frame storage, no diagnostic video backpressure, no assumed UART/capture card.
New CDC paths require explicit protocol tests and as-built delay/structure audit;
the inherited global async/Gray coverage risk is not silently declared fixed.

Performance evidence must separate exact memory optimization from measurement
overhead. Do not claim lower end-to-end latency unless measurements support it.
Board validation belongs to the user; candidate construction is not board success.
