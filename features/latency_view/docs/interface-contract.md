# 接口契约 - latency_view

## 1. 事件结构（待 MAIN 确认）

| 字段 | 建议位宽 | 含义 |
|---|---|---|
| `session_id` | 8 | 上电/重配置会话号，切换即视为旧记录失效 |
| `frame_id` | 16 | 会话内单调递增帧号（摄像头 SOF 递增） |
| `kind` | 1 | 0=采集完成帧，1=上游中止/覆盖 |

**待 MAIN 确认**：字段位宽、`session_id` 的建立与切换规则、`frame_id` 是否由 MIPI 解码侧递增、
事件所在时钟域（本模块假设采集事件在 MIPI 解码域、显示事件在 HDMI 像素域）。以上未经确认前，
本模块只以**模拟事件**验证，不修改 DDR 调度、时钟或顶层接线。

## 2. 测量定义

- 起点：MIPI 解码后该帧**首个有效像素**（`cap_event` 的上升沿，采集域）。
- 终点：同一帧首个有效像素**实际送至 HDMI**（`dsp_event` 的上升沿，显示域）。
- 只有**完整帧的首次显示**进入主统计（`lat_cycles`/`lat_ticks`/`stat_count`/`stat_sum_cycles`）。
- 重复显示只更新 `age_cycles`（图像年龄），不计入统计。

## 3. 端口（latency_meter.v）

采集域：`clk_cap, rst_cap_n, cap_event, cap_kind, cap_sid, cap_fid → cap_too_fast`。
显示域：`clk, rst_n, dsp_event, dsp_sid, dsp_fid, alarm_clr, resync_req`。
输出：`lat_valid`(1 拍脉冲)/`lat_cycles`/`lat_ticks`/`lat_seen`(电平)、
`age_valid`/`age_cycles`/`age_seen`、`stats_valid`、`alarm[3:0]`、`stat_count`、
`stat_sum_cycles`、`unmatched_count`、`repeat_count`、`entry_count`、`evt_gap_alarm`。

参数：`CROSS_CYCLES`（跨域+出队延迟补偿，默认 3）、`TICK_CROSS`（刻度补偿，默认 0）、
`ENTRY_LOG2`（关联表深度 2^n，默认 8）、`MIN_GAP_SRC/DST`（最小事件间隔）。

## 4. 时间戳与精度（修正 b43284c 的错误声明）

- 捕获时间戳在**显示域**出队时打上，随后加 `CROSS_CYCLES` 补偿 CDC/出队延迟。
- 误差是**有符号且有界**的：同钟为 0 拍；跨钟约 ±1 个显示时钟周期（CDC 相位）。
- **不再声明“读数不小于物理延迟”**；测试报告用独立记录的事件时刻给出实测误差。

## 5. CDC 归属与最小间隔

- 采集事件→显示域：`frame_event_bridge` 的 gray 指针 async FIFO（深度 16）。
- 最小间隔：源域 ≥ `MIN_GAP_SRC`(=2) 采 clock；显示域相邻出队 ≥ `MIN_GAP_DST`(=3) 拍。
  更近的源事件被丢弃并置 `cap_too_fast`；跨域后仍过近置 `evt_gap_alarm`（均粘滞）。
- 采集时钟与显示时钟的同相/异相均支持；同钟为逐拍精确。

## 6. 尚未完成（如实标记）

- `latency_osd.v`（原格式化顶层）**未迁入**：需按上表确认后的接口重新接线（本目录只提供
  测量器 + 叠加器 + 生成的字形/布局资源）。
- TD 综合、时序、位流、上板：**未执行**。
