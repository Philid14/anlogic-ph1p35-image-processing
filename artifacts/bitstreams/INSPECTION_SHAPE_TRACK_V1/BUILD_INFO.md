# INSPECTION_SHAPE_TRACK_V1 BUILD_INFO

- Role / Branch: MAIN / codex/main/inspection-shape-track-v1
- Actual TD source commit: 517697c7f3ad3328ed62a976867b5185fbcb7df0
- Archive driver commit: 56159a46f661eb3cf37c393dfec08d47e6ac2170
- Candidate tag: inspection-shape-track-v1-candidate
- Build time: 2026-11-02T14:01:23.002507+08:00
- Device / Top: PH1P35MDG324 speed3 / design_top_wrapper
- Original bit: D:/anlogic_formal_project/tmp/inspection_shape_track/full_r5/camera_to_dsi_display.bit
- Bit SHA256: 5d93f2ec5b80ee288455bc942a654de84166ecb202cda7b139b7a4f701b13f9a
- Routed resources: {'slice': 21103, 'lut6': 19809, 'ff': 20499, 'eram': 105, 'dsp': 25}
- Delta vs RULER_CM_CAL_V1: {'slice': 377, 'lut6': 364, 'ff': 269, 'eram': 3, 'dsp': 0}
- Setup WNS/TNS: +0.111ns / 0.0; Hold WNS/TNS: +0.020ns / 0.0
- STA coverage: 95.69%; worst setup: CSI color_compare_osd held_rgb[15] to char_d[3], slow_m40c, 13 logic levels.
- SYN → PHY → final Timing Check → bitgen: PASS. No changed SDC, clocks, Sensor, DDR or teammate RTL.
- Critical warning types: ['PHY-5060', 'PHY-5079']; new types: [].
- Common pixel path: 31 clocks, extra0; only measurement-statistics branch +2 clocks.
- Validation: native vendor ERAM/GSR; old/new9frame720p ISP/packer=18frames,4147200beats/3110400words; D/R two full720p frames; BG four720p frames/all1152cells; actual MAIN TRACK128x96;160-frame geometry/240 formatter cases; font4096; config/reset/selection tests.
- Scope: post-AWB/UI simulation boundaries, not physical MIPI/DDR-controller/HDMI validation. Full720p ruler288-row search inherited unchanged; integrated tests use12 search rows for runtime.
- D/R is EXPLICIT operator mode, not automatic circle/arc detection. Automatic near-round attempt not used.
- Board Test Status: NOT_RUN. FIFO/CDC and high-density physical risks remain.
- Rollback: RULER_CM_CAL_V1 / ruler-cm-cal-v1-candidate / 6372f765f61ec31d8a18923596c8326ce84a0fd7637850847d5ac364cc3aebc2.

See docs/INSPECTION_SHAPE_TRACK_V1_DESIGN.md and BOARD_TEST.md. Historical bits/tags are unchanged. Remote publication status is recorded after actual push; this file is not proof of push.
