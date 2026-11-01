# VISION_TRACK_MOTION_V1 BUILD_INFO

- Role / Branch: MAIN / codex/main/vision-track-motion-v1
- Actual TD source commit: c3bdf9240647d9f98a2ff68c416693ad1e20f4b9
- Tag: vision-track-motion-v1-candidate (created after archive)
- Build time: 2026-11-01T19:11:13.666752+08:00
- Device / Top: PH1P35MDG324 speed3 / design_top_wrapper
- Original bit: D:/anlogic_formal_project/tmp/vision_track_motion/combined_r4/camera_to_dsi_display.bit
- Bit SHA256: f3dfd9f1ad42bbca95199ac128b9d4808327d4482a1465019ce85a678c0b63a0
- Physical resources: {'slice': 20694, 'lut6': 19497, 'ff': 20285, 'eram': 102, 'dsp': 27}
- Delta vs V4: {'slice': -300, 'lut6': -366, 'ff': 1169, 'eram': 12, 'dsp': 0}
- Setup WNS/TNS: +0.106ns / 0.0; Hold WNS/TNS: +0.020ns / 0.0
- Synthesis → Physical Design → final Timing Check → bitgen: PASS
- Critical warning types: ['PHY-5060', 'PHY-5079']; new: []
- Common pixel delay: 31 cycles; extra cycles0. Sensor/ISP parameters, video_in/out, DDR, PLL/pins/SDC unchanged.
- Native vendor ERAM/GSR + actual ISP/packer: 17 complete720p frames, 3916800 valid beats /2937600 packed words.
- Logo exhaustive32768-address and1857588-cycle bit-exact native equivalence; standalone guard/motion/error/timeout and seven-mode key/CDC tests PASS.
- Board Test Status: NOT_RUN. No physical/long-run/thermal claim. No PR merged.
- Limits: One red class, merged same-color components, bbox center not centroid; Coordinates/count are explicitly LAST capture frame, HEX format; no current-frame bbox; 32x16 block mean motion, changed-block count not object count, global lighting ambiguity; Ingress heartbeat does not prove DDR output freshness or provide end-to-end latency; Inherited FIFO sticky, Gray-pointer constraint and long-run board stability remain unverified.
- Rollback: INSPECTION_USABILITY_V4 / inspection-usability-v4-candidate / SHA256 2655fd65ebb245279b684fbdc5f3065dab8f654b387c7c61cfca3bdbadc64f39.
