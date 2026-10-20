# DEMO_STEPS - 独立演示

1. `python model/latency_model.py` → `latency_model self-test: PASS`
2. `python tests/run_osd_sim.py` → `RESULT: PASS`，面板：
   ```text
   LAT    0.18MS
   AGE  ---.--MS
   CAP       1FPS
   DSP       1FPS
   FRM 00000003 E0
   ```
3. `python tests/run_latency_sim.py` → `cases: 18, failed: 0`
   重点：`s2_skip`（A/B/C 只显示 C → 报 C 的延迟）、`s4_repeat`（只报 AGE）、
   `s6_overflow_recovery`（`alarm_clr` 不恢复统计）、`s13_incomplete`（未完成不计统计）。
4. 坐标对齐：`ALIGN_ERRORS 0`。
5. 口径：全部为**仿真**；未接主线、无 bit、未上板。
