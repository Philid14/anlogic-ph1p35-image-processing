# TRACK_REGION_FIX_V1 BUILD_INFO

- Branch: codex/main/track-region-fix-v1; baseline 4d0f779cefd680363b8a3f0d4d5c33a42d81197f; dependent on unmerged Draft PR28.
- Actual build source commit: 0e054712064041a18047f13c8ee76c57ad8e29f8
- Archive driver commit: 20635615a60bdcc27a45ce46812993bf26445250; tag: track-region-fix-v1-candidate
- Time: 2026-11-02T20:59:48.326009+08:00; device/top: PH1P35MDG324 speed3 / design_top_wrapper
- Original bit: D:/anlogic_formal_project/tmp/track_region_fix/full_r2/camera_to_dsi_display.bit
- SHA256: 049adbf16065b6ce0b7d9d0d32eb318573c872df1b8a7a1aa4350efbfc583a99
- Final routed resources: {'slice': 20942, 'lut6': 19498, 'ff': 20368, 'eram': 105, 'dsp': 25}
- Delta vs INSPECTION_SHAPE_TRACK_V1: {'slice': -161, 'lut6': -311, 'ff': -131, 'eram': 0, 'dsp': 0}
- Setup WNS/TNS: +0.137ns/0.0; Hold WNS/TNS: +0.020ns/0.0; coverage 95.67%.
- Complete SYN / PHY / final STA / bitgen PASS; constraints, clocks, Sensor and teammate RTL unchanged.
- Common pixel path31 clocks, extra0; no added image RAM/DSP; result one clock after EOF.
- Critical warnings: ['PHY-5060', 'PHY-5079']; new types: [].
- Validation: 15 native groups; independent model16 frames+7 full720p frames with old RTL failure;18 full720p ISP/packer regression; exact MAIN31cycle TRACK; inherited dimension/BG/format/reset/font tests rerun. Scope: post-AWB/synchronized UI, not physical MIPI/DDR/HDMI validation.
- Board Test NOT_RUN; no statement of real-camera improvement before user tests.
- Limits: ['Not general CCL: one longest run per row; solid single red object on non-red background', 'Pale pink, thin/hollow targets or glare holes can under-detect; similarly sized red objects can swap', 'N is selected chain support area in4px groups, not raw red count or calibrated object area', 'LAST bbox may lag one capture frame; no new DDR/display identity association', 'Inherited FIFO/Gray coverage, high-density, thermal and long-run risks require board tests']
- Rollback: inspection-shape-track-v1-candidate; SHA256 5d93f2ec5b80ee288455bc942a654de84166ecb202cda7b139b7a4f701b13f9a.
- Packing failures r0=21312/r1=21226 >21216 preserved; no failed-build bit released.

See DESIGN / REPORT / BOARD_TEST. Remote publication is separately confirmed after actual push.
