# RULER_CM_CAL_V1 BUILD_INFO

- Role / Branch: MAIN / codex/main/ruler-cm-cal-v1
- Actual TD source commit: 9d1eff3e1e88861bfac317c6064c51062282aa4d
- Tag: ruler-cm-cal-v1-candidate (created after archive)
- Build time: 2026-11-02T10:59:43.243923+08:00
- Device / Top: PH1P35MDG324 speed3 / design_top_wrapper
- Original bit: D:/anlogic_formal_project/tmp/ruler_cm/r0/camera_to_dsi_display.bit
- Bit SHA256: 6372f765f61ec31d8a18923596c8326ce84a0fd7637850847d5ac364cc3aebc2
- Physical resources: {'slice': 20726, 'lut6': 19445, 'ff': 20230, 'eram': 102, 'dsp': 25}
- Delta vs VISION_TRACK_MOTION_V1: {'slice': 32, 'lut6': -52, 'ff': -55, 'eram': 0, 'dsp': -2}
- Setup WNS/TNS: +0.145ns / 0.0; Hold WNS/TNS: +0.020ns / 0.0
- Synthesis → Physical Design → final Timing Check → bitgen: PASS
- Critical warning types: ['PHY-5060', 'PHY-5079']; new: []
- Common pixel delay: 31 cycles; extra cycles0. Sensor/ISP parameters, video_in/out, DDR, PLL/pins/SDC unchanged.
- Native vendor ERAM/GSR + ISP/packer (post-AWB/UI boundary; integrated reader search height12, full288 separately tested): 17 complete720p frames, 3916800 valid beats /2937600 packed words.
- CM19-unit checks, full production1280x720/768x288 reader top/bottom search27443319 cycles; two-line mean and exact native font/measurement packing PASS. Seven-mode keys/config CDC preserved.
- Board Test Status: NOT_RUN. No physical/long-run/thermal claim. No PR merged.
- Limits: Metric ruler/long centimeter ticks are an operator precondition, not OCR/unit recognition; Only a rough commonX/Y scale; perspective/height/blur/regular background patterns can bias scale; Full720p reader/768x288 search separately validated; integrated9frame test search height12 for scheduling runtime; Unchanged inherited FIFO/Gray/thermal/long-run risks and all new features still await physical board validation.
- Rollback: VISION_TRACK_MOTION_V1 / vision-track-motion-v1-candidate / SHA256 f3dfd9f1ad42bbca95199ac128b9d4808327d4482a1465019ce85a678c0b63a0.
