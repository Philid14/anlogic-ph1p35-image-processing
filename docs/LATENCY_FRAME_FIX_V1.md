# LATENCY_FRAME_FIX_V1 — MAIN expedited board candidate

Baseline793c9d3 / INSPECTION_PARTS_MOTION_V1. User reports LAT/MIN/MAX/AGE0, N0, BAD, E5BAB; video alive. No qualified samples; zeros are not measured latency.

Scope: correct RAW error ownership. Previous adapter invalidated a completed RAW frame for PHY lane errors during following vertical blanking while its ISP tail was still being packed. Only errors within first-to-last RAW beat now belong to that frame; active errors, geometry, overflow and journal/display checks remain mandatory. This is a confirmed code defect, not yet proof of the particular physical failure in the photo.

Native original VTC/DDR/mixer timing and actual720p ISP with overlapping RAW/RGB streams can qualify clean frames. This does not reproduce physical lane activity or prove hardware fixed.

Added fifth panel line C:xx W:xx D:xx, hexadecimal diagnostic status only. C is last packed-frame rejection mask: bits0 lane error,1 RAW geometry,2 no RAW identity,3 RAW incomplete,4 pack bad,5 pack not started,6 camera FIFO full,7 identity exhausted. C00 means source qualified. W live status: upper nibble committed slot mask; low bits0 writing,1 read_bad,2 write_bad,3 reference-clock fault. W is live and may show an adjacent instant. D is last displayed-frame rejection: bits0 missing tuple,1 unqualified tuple,2 frame_bad,3 read_bad,4 pixel count,5 age bound,6 backward identity. All-zero D means clean publication. Diagnostic bits use2FF and are not used to qualify timestamps or identities.

All Sensor/ISP numerical settings, algorithms including AWB resource optimization/T-L/motion, switches, DDR payload/scheduling, HDMI format, PLL/pin/SDC unchanged. No extra control. No formal algorithm development. Historic bits retained.

User explicitly requests fastest bit, deferring broad regression/report/PR. Required focused native tests, SYN/PHY/STA/bitgen and minimum bit/source/hash archive remain. Board status NOT_RUN. No merge.

Board: PROGRAM_SRAM new bit. After5 seconds record LAT/status/N/E and C/W/D. N should increase on new identities, REP must not incrementN. If stillBAD/N0, send full panel C/W/D; do not interpret zero as latency or call this fixed. Roll back inspection-parts-motion-v1-candidate directly.
