# INSPECTION_PARTS_MOTION_V1 BUILD_INFO

- Branch: codex/main/inspection-parts-motion-v1; baseline: 6ad4f7cd70b5614240c07db2a16775aa492d9f14; role MAIN.
- Actual compiled source: bb1f8811cafd441815b2248bcc19b263b02657eb; archive driver: 86b5d9139d19f1139673b44475f7c5ba24ef67bc.
- Tag: inspection-parts-motion-v1-candidate; Draft PR31 depends on unmerged30. No merge.
- Build time: 2026-11-03T19:51:48.327621+08:00; device/top: PH1P35MDG324 speed3 / design_top_wrapper.
- Original bit: D:\anlogic_formal_project\tmp\inspection_parts_motion\full_r3\camera_to_dsi_display.bit; SHA256: 1a1737923e33e0f8c87ca918978fff08d8dd4c7d6120e54f4835bfc911f1bf11.
- Final resources: {'slice': 19209, 'lut6': 18551, 'ff': 16340, 'eram': 105, 'dsp': 25}; delta vs LATENCY_PERFORMANCE: {'slice': -1622, 'lut6': -981, 'ff': -4997, 'eram': 0, 'dsp': 0}.
- Setup WNS/TNS +0.257ns/0.0; Hold WNS/TNS +0.020ns/0.0; STA coverage 94.4%.
- Complete SYN/PHY/final STA/bitgen PASS. Clock/PLL/pin/SDC and Sensor/ISP numerical parameters unchanged; AWB computation reused with native cycle/numeric equivalence. Original application controls unchanged.
- Critical warnings: ['PHY-5060', 'PHY-5079']; new types: [].
- Common pixel stream31cycles, extra0; original pixel/DDR throughput and video format unchanged.
- Verification: 15 profile cases,7 simultaneous7-field native720p overlay frames,8 actual31-cycle streams,311 native divider math vectors/all50 reset offsets,12 native whole-AWB256x64 frames, original18 full720p reference frames and application/latency regression; 58 result/native-source hashes. Software/RTL/TD, not physical camera/DDR/HDMI evidence.
- Board Test NOT_RUN; follow docs/INSPECTION_PARTS_MOTION_V1_BOARD_TEST.md.
- CDC: exact routed DB inspected; inherited Gray/long-run hardware risks remain.
- Rejected R0 at21710Slice and resource attempts preserved under build_evidence/attempts; no rejected trial bit.
- Rollback: latency-performance-v1-candidate, SHA256 062b48ec7c002b56b4a025cd36a0e0f5e9138178f5706d6390a7f91eef3a27a4.
- Remote publication is recorded separately after actual push.
