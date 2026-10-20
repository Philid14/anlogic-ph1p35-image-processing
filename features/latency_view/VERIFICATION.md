# VERIFICATION - latency_view

## 命令

```powershell
python model/latency_model.py
python model/gen_osd_layout.py --check
python tests/run_latency_sim.py
python tests/run_osd_sim.py
iverilog -g2012 -s tb_overlay_align -o align.vvp tests/tb_overlay_align.v rtl/text_overlay.v rtl/char_rom.v
vvp align.vvp
```

## 结果（2026-10-20，Icarus Verilog 14.0）

| 项 | 结果 |
|---|---|
| 模型自检 | `latency_model self-test: PASS` |
| 布局生成物 | `osd_layout.vh up to date` |
| 19 场景 | **cases: 19, failed: 0 / RESULT: PASS** |
| 面板内容 | **RESULT: PASS**（normal + fault 两种模式，80 字符与模型一致） |
| 坐标对齐 | `ALIGN_ERRORS 0` |

## 场景

| 场景 | 验证点 |
|---|---|
| s1_normal | 10/15 拍两次测量，精确 |
| s2_skip | **审查复现**：A/B/C 只显示 C，报 C 的 10 拍 |
| s3_abort_skip | A/B 中止后只计 C |
| s4_repeat | 首次计入；第二次只报 AGE |
| s5_unmatched | 未匹配不入统计，bit0，随后恢复 |
| s6_overflow_recovery | 表满无效；`alarm_clr` 不恢复；`resync_req` 恢复 |
| s7_session_switch | 会话切换清旧记录，无误配 |
| s8_multi_pulse | 3.5 拍高电平=1 个事件 |
| s9_abort_then_display | 中止帧显示判未匹配 |
| s10_resync | 重同步后旧帧未匹配，新配对有效 |
| s11_mid_frame | 半帧启动仍配对 |
| s12_cross_clock | 24 ns vs 10 ns，误差 ≤ ±1 拍 |
| s13_incomplete | 未完成即显示：不计统计，bit0 |
| s14_done_after_display | 完成晚于显示：未匹配 |
| s15_fps_window | L1：窗口内采集/显示计数（无除法） |
| s16_abort_unknown | 未知中止：bit3 + 计数 |
| s17_recapture | 同键重采集：原地替换 + bit1 |
| s18_fid_wrap | 帧号回绕无新会话：清表 + bit3 |
| s19_too_fast_alarm_clr | 过密事件被丢弃，`alarm_clr` 后 bit2 不再复置 |

真值由测试台打印的**实际事件时刻**计算；同钟容差 0 拍，跨钟 ±1 拍。

## 自查修复记录（2026-10-20）

| # | 发现 | 修复 | 回归 |
|---|---|---|---|
| 1 | `latency_osd` 的 AGE 字段从未做 BCD 转换（`bcd_age` 恒 0） | `S_WR_LAT` 结束后先启动 AGE 转换再写字段 | `run_osd_sim` fault=0/1 均显示 `AGE 48.16MS` |
| 2 | `cap_too_fast` 为粘滞电平且跨域未同步；`alarm_clr` 清不掉 | 桥输出改为单拍脉冲；meter 内 2FF 同步 + 边沿检测 | `s19_too_fast_alarm_clr` |
| 3 | 关联失效时面板仍显示旧 LAT 数字 | 面板 `lat_ok = shown_lat_seen & shown_stats` | `run_osd_sim` fault=1 显示 `LAT ---.--MS` |
| 4 | 面板与调试值非同一快照（CAP 字段偶发差 1） | 每帧 `vs_fall` 原子快照 `shown_*`，格式化与 DBG 共用 | `run_osd_sim` 两种模式均 PASS |
| 5 | OSD 测试从未覆盖 AGE | 增加重复显示与故障模式 | `run_osd_sim`（2 模式） |

## 未验证（如实标记）

- TD 综合/布局布线/位流/时序：**未执行**（本环境无 TD）。
- 上板：**未执行**。
- 主线接入（真实事件、锁存身份、实测时钟、`CROSS_CYCLES` 标定）：**未完成**，见 `INTEGRATION.md`。
- 不得声称"进阶三已整机完成"。
