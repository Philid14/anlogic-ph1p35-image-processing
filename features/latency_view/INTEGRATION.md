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

## 待确认（阻塞接入）

事件来源/时钟域、完成事件生成点、身份锁存位置、实测时钟与 `CROSS_CYCLES` 标定、面板位置。
确认后由 MAIN 接线、构建、上板；本模块不自行合并或改主线。
