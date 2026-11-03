# LATENCY_PERFORMANCE_V1 BUILD_INFO

- Version/branch: LATENCY_PERFORMANCE_V1 / codex/main/latency-performance-v1
- Actual compiled source: 69521d7932c2fec94dd67c03a7362b4d6b0ceb8f; baseline: 072bc0f8858ceb3009659f8df7cb02b9da05ed36
- Archive driver: c071405fec685a39be546346b7e0d4151e018e75; tag: latency-performance-v1-candidate; Draft PR30, depends on29. No merge.
- Build time: 2026-11-03T09:50:24.284761+08:00; device/top: PH1P35MDG324 speed3 / design_top_wrapper
- Original bit: D:/anlogic_formal_project/tmp/latency_performance/full_r1/camera_to_dsi_display.bit
- SHA256: 062b48ec7c002b56b4a025cd36a0e0f5e9138178f5706d6390a7f91eef3a27a4
- Final routed resources: {'slice': 20831, 'lut6': 19532, 'ff': 21337, 'eram': 105, 'dsp': 25}
- Delta vs TRACK_REGION_FIX_V1: {'slice': -111, 'lut6': 34, 'ff': 969, 'eram': 0, 'dsp': 0}
- Setup WNS/TNS: +0.175ns/0.0; Hold WNS/TNS: +0.020ns/0.0; coverage: 95.33%.
- SYN/PHY/final STA/bitgen PASS. Original PLL, pin and SDC files unchanged.
- Critical warning types: ['PHY-5060', 'PHY-5079']; new types: [].
- Common post-AWB stream31cycles, extra0. No frame-buffer policy or pixel throughput changes.
- Tick10us from configured75MHz; end-to-end same-frame sample, repetitions counted as AGE only.
- Validation: 18 full720p reference ISP/packer frames, 4147200beats/3110400words; native Gaussian/NMS/link/cache/FIFO/journal/meter/OSD; native 1280x4 actual DDR-command FIFO/readout/mixer path; original applications/reset/font regression. These are software/RTL/TD results, not physical camera/DDR/HDMI verification.
- Board Test: NOT_RUN. Follow docs/LATENCY_PERFORMANCE_V1_BOARD_TEST.md.
- CDC: see build_evidence/cdc; inherited constraints/long-run risks are not silently declared fixed.
- Rollback: track-region-fix-v1-candidate, SHA256 049adbf16065b6ce0b7d9d0d32eb318573c872df1b8a7a1aa4350efbfc583a99.
- Remote publication receipt is recorded separately after actual push.
