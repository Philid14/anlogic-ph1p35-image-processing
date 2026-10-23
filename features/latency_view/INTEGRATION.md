# INTEGRATION - 交给 MAIN 的接线清单

## 需 MAIN 提供

| 端口 | 建议来源 | 备注 |
|---|---|---|
| `clk_cap/rst_cap_n` | MIPI 解码/ISP | 与 `cap_event` 同域 |
| `cap_event/cap_kind/cap_sid/cap_fid` | 首有效像素(0)、帧尾(2)、中止(1) | 上升沿有效 |
| `clk/rst_n` | HDMI 像素时钟 | 与 `dsp_event` 同域 |
| `dsp_event/dsp_sid/dsp_fid` | HDMI 首有效像素 + **读出锁存身份** | 不得现读最新身份 |
| `alarm_clr/resync_req` | 按键或控制寄存器 | 语义见 INTERFACE §失效与恢复 |

## 需 MAIN 写入的参数

`TICK_BASE/TICK_REMAINDER/TICK_MOD`（按实测像素时钟）、`FPS_WINDOW_TICKS`（默认 10 000 000 = 1 s）、
`CROSS_CYCLES`（默认 3，现场标定）、`X0/Y0/SCALE_LOG2/PANEL_EN/BG_DIM/FG_RGB/BG_RGB`。

## 约束

- 旁路观察，不对采集链路反压；不修改 DDR 调度、缓存槽号、PLL、引脚约束。
- `text_overlay` 给 `rgb/de/hs/vs` 增加 **3 拍固定延迟**，串入 HDMI 前必须计入时序与约束。
- 面板位置需与共享 OSD 协调。

## MAIN 已确认（2026-10-21）

- 采集起点：MIPI 解码/RAW 解包后、进入 ISP 前的首个有效像素；时钟域 `S_csi_rx_clk`；
  候选点 `uial2axis` 的 `S_axis_tvalid && S_axis_tuser`。
- 完成/中止由 MAIN 产生：kind 2 = 完整性检查通过 + DDR 用户接口有效写入完成（具备读出资格）；
  ISP 帧尾不足以判定完成；DDR 域事件由 MAIN 原子跨域汇聚到 `clk_cap`，并处理同拍排队与溢出。
  `I_mipi_rx_error` 目前接 0，不能作为错误汇总。
- 显示身份：MAIN 在 `video_out` 选帧设地址时锁存身份/代次/有效，随像素路径传递；`dsp_event` 对齐
  HDMI 首有效像素；禁止输出时现读最新身份。
- 时钟：按当前配置使用 75 MHz（750/0/100000）；这是配置值，不是板上实测。
- OSD：面板位置 `(24,192)`，8×8 字体 2 倍，256×128 像素；Logo 最高保护优先级。

## MAIN 需要额外提供的控制

- `auth_sid[31:0]` / `auth_sid_vld`：MAIN 的权威会话号；模块只接受该 sid 的采集事件。
- 复位/epoch 屏障：目的端单侧复位后桥会自动排空，但 MAIN 仍应优先采用双端复位；
  恢复统计必须显式 `resync_req`（会 flush 桥内在途事件）。
- 任何丢失（满队列/过密）都会置 `fatal`，MAIN 需在处理后给出 `resync_req`。

## 仍待实现（阻塞接入）

1. MAIN 生成四个真实事件端口并接入 `latency_osd`（当前工程尚无完整帧提交端口）。
2. 板上实测像素时钟（当前 75 MHz 为配置推导值）。
3. `CROSS_CYCLES` 现场标定（用独立记录的双端时间戳；无排队条件下目标 ±1 拍）。
4. 面板最终位置/合成顺序与共享 OSD 的协调由 MAIN 落实。
