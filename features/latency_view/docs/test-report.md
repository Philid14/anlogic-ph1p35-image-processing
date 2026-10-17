# 测试报告 - latency_view

## 命令

```powershell
python features/latency_view/tests/run_latency_sim.py           # 12 场景
iverilog -g2012 -s tb_overlay_align -o align.vvp \
  features/latency_view/tests/tb_overlay_align.v \
  features/latency_view/rtl/text_overlay.v features/latency_view/rtl/char_rom.v
vvp align.vvp
```

## 结果（2026-10-17，Icarus Verilog 14.0）

`cases: 12, failed: 0` / `RESULT: PASS`

| 场景 | 验证点 | 结果 |
|---|---|---|
| s1_normal | 10/15 拍两次测量，精确 | PASS |
| s2_skip | **审查复现**：A/B/C 只显示 C，测得 C 的 10 拍（不是 27） | PASS |
| s3_abort_skip | A/B 中止后只计 C | PASS |
| s4_repeat | 首次计入；第二次只报图像年龄 | PASS |
| s5_unmatched | 未匹配不入统计，告警 bit0，随后恢复 | PASS |
| s6_overflow_recovery | 表满→无效；`alarm_clr` 后仍无效；`resync_req` 后恢复 | PASS |
| s7_session_switch | 会话切换清旧记录，无跨会话误配 | PASS |
| s8_multi_pulse | 3.5 拍高电平只算 1 个事件 | PASS |
| s9_abort_then_display | 中止帧的显示判为未匹配 | PASS |
| s10_resync | 重同步后旧帧未匹配，新配对有效 | PASS |
| s11_mid_frame | 半帧/任意时刻启动仍配对 | PASS |
| s12_cross_clock | 24 ns vs 10 ns，误差 ≤ ±1 拍 | PASS |
| 坐标对齐 | 先制造 6 行无同步 DE 突发，再起正常帧；字形行仍落在正确位置 | PASS（`ALIGN_ERRORS 0`） |

## 真值如何得到（不复制 RTL 假设）

测试台按**绝对时间**驱动事件并打印 `EVT CAP/EVT DSP <实际采样沿时刻>`；
运行器用这些时刻计算 `真值 = (t_dsp - t_cap) / T_display`，再与 RTL 输出比较。
同钟容差 0 拍，跨钟容差 ±1 拍，刻度 ±1。

## 未验证（如实标记）

- TD 综合 / 布局布线 / 位流 / 时序：**未执行**（本环境无 TD）。
- 上板实测：**未执行**。
- 原 `latency_osd.v` 格式化顶层：**未迁入、未仿真**（等待 MAIN 确认事件接口后接线）。
- 因此**不得**声称“进阶三已整机完成”。
