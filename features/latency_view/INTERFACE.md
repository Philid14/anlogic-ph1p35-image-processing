# INTERFACE - latency_view（LATENCY）

- 协议：`TEAM_PROTOCOL_V1` §2.3、§4.1、§4.4
- 状态：**`负责人确认（语义）`**（MAIN 2026-10-21 回复）；真实端口/实测频率/误差标定仍待实现
- 基线：MAIN 2026-10-21 核对 `89093f4`；**远端 `origin/main` 当前仍为 `c42168e`**（本分支基于它，0 behind）；来源提交 `b43284c`
- MAIN 回复：采集起点/完成与中止/显示身份锁存/75 MHz/OSD 位置已确认（见下）
- 默认未接入主线，验证使用模拟事件

## 0. MAIN 2026-10-21 确认要点

- **采集起点**：MIPI 解码、RAW 解包后、该帧首个有效像素**进入 ISP 前**；时钟域 `S_csi_rx_clk`
  （与 ISP 处理时钟相同）；候选观察点 `uial2axis` 的 `S_axis_tvalid && S_axis_tuser`；
  由 MAIN 生成规范化事件与身份，不得用提前帧通知或 AWB 输出通知代替。
- **身份**：`session_id/frame_id` 各 32 位，由 MAIN 统一发行；每采集帧只分配一次；重启/回绕由 MAIN 管理。
- **完成事件（kind 2）**：帧完整性检查通过且对应 DDR 帧数据已完成用户接口有效写入、具备读出资格；
  ISP 帧尾不能单独作为完成事件。中止来源：采集异常、长度/打包异常、FIFO 丢数据、缓存覆盖、复位取消。
  当前工程无完整帧提交端口，由 MAIN 实现；DDR 域事件须由 MAIN 按完整身份原子跨域汇聚到 `clk_cap`，
  不能直接拼接异步脉冲，同时发生的事件需排队与溢出处理。`I_mipi_rx_error` 当前接常量 0，不可作为错误汇总。
- **显示身份**：MAIN 在 `video_out` 选帧并设置 DDR 起始地址时锁存身份/写入代次/有效状态；元数据随像素
  经过读预取、FIFO、拆包、显示流水线；`dsp_event` 对齐送入 HDMI 发送接口的该帧首个有效像素；
  禁止输出时读取槽位“最新身份”。以后增加 OSD 流水级也要计入终点对齐。
- **时钟**：当前配置的 HDMI 像素时钟是 **75 MHz**（PLL 界面请求 74.25 MHz，但生成文件标注 75 MHz、
  实现报告周期约 13.333 ns）→ `TICK_BASE=750, TICK_REMAINDER=0, TICK_MOD=100000`。
  这是配置频率、不是板上实测；不为计时模块修改主线 PLL。
- **排队延迟**：`CROSS_CYCLES=3` 仅为仿真占位；FIFO 排队造成的可变延迟不能用固定常数消除。
  本模块在 FIFO 写入时记录“是否已有待处理条目”（占用 >1），**排队样本直接判为无效**（不计统计、
  置 alarm[2]），从而把误差限定在“无排队时 ±1 拍”的适用条件内。
- **OSD 位置**：默认 `(24,24)` 会覆盖左上角 160×160 安路 Logo，改为 **`(24,192)`**、8×8 字体放大 2 倍、
  面板 256×128 像素，避开 Logo、右上状态与底部目标文字；最终位置/合成顺序/字库由 MAIN 落实，Logo 最高优先。

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
`age_*`（重复显示图像年龄）、`stat_count/stat_sum_cycles/stat_sum_ticks`（平均延迟 = sum/count，由读取方计算）、
`cap_count/cap_done_count/cap_abort_count/dsp_count`、
`cap_fps/dsp_fps/fps_valid`（窗口= `FPS_WINDOW_TICKS` 个 0.01 ms 刻度，默认 1 s）、
`stats_valid`、`alarm[3:0]`：

| bit | 含义 |
|---|---|
| 0 | 未匹配，或帧未完成即显示 |
| 1 | 记录被覆盖（表满）或未知帧完成 |
| 2 | 事件过密（源 <2 拍或出队 <3 拍）。`cap_too_fast` 为**翻转电平**，目标域 XOR 边沿检测，慢时钟也不会漏采 |
| 3 | 会话切换、帧号回绕、未知帧中止 |

## 时基与精度

显示域 `cyc_cnt`（每拍）与 `tick_cnt`（平均 10 µs，分数累加器，无除法器）。参考频率由
`TICK_BASE/TICK_REMAINDER/TICK_MOD` 参数给出，须来自实测时钟。跨域事件在显示域出队打戳并加
`CROSS_CYCLES`（默认 3 拍）补偿。误差**有符号有界**：同钟 0 拍、跨钟约 ±1 拍；**不声明"读数不小于物理延迟"**。
75 MHz → `TICK_BASE=750, TICK_REMAINDER=0`（配置频率，非实测）。

排队样本：FIFO 写入时若已有待处理条目（占用 >1），该样本不计统计并置 alarm[2]；
正常条件（1 事件/帧、读端每拍出队）下占用 ≤1，残差为 ±1 拍。

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
| `resync_req` + 干净配对 | 统计重新有效；count/sum/CNT 清零，AVG 从新窗口重算 | — |

## 面板（latency_osd）

8 行 × 16 字符：`LAT`（最近一次首次显示）、`AVG`（自 resync 以来平均，RTL 内 64 拍串行除法器计算）、
`AGE`（最近重复显示图像年龄）、`CAP fps` / `DSP fps`（窗口计数）、`FRM` + 告警半字节、
`CNT`（首次显示次数）、`ALM`（告警半字节 + 文字：UNMATCH / OVERWR / TOOFAST / SESSION / NONE）。
面板与调试输出共用 `vs_fall` 原子快照，`stats_valid=0` 时 LAT/AVG 显示 `---.--`。

## 待 MAIN 确认

1. 四个事件的真实来源与时钟域；`frame_id` 递增点与回绕策略。
2. `cap_kind=2` 的生成点（DDR 写完还是 ISP 帧尾）。
3. 读出身份锁存实现位置。
4. 实测像素时钟与 `CROSS_CYCLES` 标定方法。
5. 面板位置/字号与共享 OSD 的协调。
