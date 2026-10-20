# INTERFACE - latency_view（LATENCY）

- 协议：`TEAM_PROTOCOL_V1` §2.3、§4.1、§4.4
- 状态：**`接口草案`**（待 MAIN 确认事件映射、时基与 CDC 归属后冻结）
- 基线：`origin/main` `c42168e`；来源提交 `b43284c`
- 默认未接入主线，验证使用模拟事件

## 事件

| 信号 | 域 | 位宽 | 语义 |
|---|---|---|---|
| `cap_event` | `clk_cap` | 1 | 上升沿=一个事件；电平多拍只算 1 次 |
| `cap_kind` | `clk_cap` | 2 | 0=帧首有效像素，1=中止/覆盖，2=整帧完成 |
| `cap_sid`/`cap_fid` | `clk_cap` | 32/32 | 会话号/帧号 |
| `dsp_event` | `clk` | 1 | 该帧首个有效像素实际输出 |
| `dsp_sid`/`dsp_fid` | `clk` | 32/32 | **读出时锁存**并随像素路径携带（§4.4） |
| `alarm_clr` | `clk` | 1 | 只清告警位 |
| `resync_req` | `clk` | 1 | 清表并使统计失效，直到新的干净配对 |

`cap_kind=2` 必须在该帧最后一个有效像素之后；未收到完成事件的记录不得计入统计。
`dsp_*` 身份不得由输出侧现读"最新身份"。

## 输出

`lat_valid/lat_cycles/lat_ticks/lat_seen`（`lat_ticks` 单位 0.01 ms）、
`age_*`（重复显示图像年龄）、`stat_count/stat_sum_cycles`、
`cap_count/cap_done_count/cap_abort_count/dsp_count`、
`cap_fps/dsp_fps/fps_valid`（窗口= `FPS_WINDOW_TICKS` 个 0.01 ms 刻度，默认 1 s）、
`stats_valid`、`alarm[3:0]`：

| bit | 含义 |
|---|---|
| 0 | 未匹配，或帧未完成即显示 |
| 1 | 记录被覆盖（表满）或未知帧完成 |
| 2 | 事件过密（源 <2 拍或出队 <3 拍） |
| 3 | 会话切换、帧号回绕、未知帧中止 |

## 时基与精度

显示域 `cyc_cnt`（每拍）与 `tick_cnt`（平均 10 µs，分数累加器，无除法器）。参考频率由
`TICK_BASE/TICK_REMAINDER/TICK_MOD` 参数给出，须来自实测时钟。跨域事件在显示域出队打戳并加
`CROSS_CYCLES`（默认 3 拍）补偿。误差**有符号有界**：同钟 0 拍、跨钟约 ±1 拍；**不声明"读数不小于物理延迟"**。
74.25 MHz → `TICK_BASE=742, TICK_REMAINDER=50000`。

## 失效与恢复

| 场景 | 行为 | 告警 |
|---|---|---|
| 未完成即显示 | 不计统计、计未匹配 | bit0，`stats_valid=0` |
| 中止/覆盖后显示 | 不计统计 | bit0 |
| 同键重采集 | 原地替换 | bit1，`stats_valid=0` |
| 表满淘汰 pending | 轮转淘汰 | bit1，`stats_valid=0` |
| 未知完成/中止 | 计数 | bit1 / bit3 |
| 会话切换/帧号回绕 | 清空旧会话 | bit3，`stats_valid=0` |
| `alarm_clr` | 仅清告警，不恢复统计 | — |
| `resync_req` + 干净配对 | 统计重新有效 | — |

## 待 MAIN 确认

1. 四个事件的真实来源与时钟域；`frame_id` 递增点与回绕策略。
2. `cap_kind=2` 的生成点（DDR 写完还是 ISP 帧尾）。
3. 读出身份锁存实现位置。
4. 实测像素时钟与 `CROSS_CYCLES` 标定方法。
5. 面板位置/字号与共享 OSD 的协调。
