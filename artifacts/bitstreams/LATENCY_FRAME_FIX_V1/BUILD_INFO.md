# LATENCY_FRAME_FIX_V1

- Source commit: ebbd3cd7b41bde86c06bdd5bc436dcb3195990d8; baseline: 793c9d3de58420524007474bafb2125cbad104f1; branch: codex/main/latency-frame-fix-v1.
- Tag: latency-frame-fix-v1-candidate; Draft PR deferred by user's fastest-bit request. No merge.
- Build time: 2026-11-03T21:31:49.554151+08:00; PH1P35MDG324 speed3; top design_top_wrapper.
- Original bit: D:\anlogic_formal_project\tmp\latency_frame_fix\full_r0\camera_to_dsi_display.bit; archived bit: D:\anlogic_formal_project\artifacts\bitstreams\LATENCY_FRAME_FIX_V1\camera_to_dsi_display.bit.
- SHA256: d516c1d81ec30999d3510ac82e32e354dd31e1e40dd374ad376e2b572a1f2c16.
- SYN/PHY/STA/bitgen PASS; Setup +0.137ns, Hold +0.020ns; TNS0.
- Routed resources: {'slice': 19177, 'lut6': 18498, 'ff': 16374, 'eram': 105, 'dsp': 25}; delta: {'slice': -32, 'lut6': -53, 'ff': 34, 'eram': 0, 'dsp': 0}.
- Critical warnings: ['PHY-5060', 'PHY-5079']; new types: [].
- Validation: Native old-fails/new-passes blanking ownership; active source/line/full rejection; journal/display units; exact native5-line OSD raster; actual240-word DDR FIFO/mixer path12commits10samples.
- Limitations: Specific board root not yet proved; C/W/D needed if BAD persists. Full unrelated regression and physical long-run/PVT deferred. Unchanged production video clocks/SDC/payload and existing CDC risk; added diagnostic bit synchronizers not an atomic measurement bus.
- Board NOT_RUN. PROGRAM_SRAM; after5s inspect N/status/C/W/D. Do not call zero a valid latency.
- Rollback: inspection-parts-motion-v1-candidate. Historical bits unchanged.
- Push status pending, report actual result separately.
