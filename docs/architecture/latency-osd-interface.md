# 延迟测量与 OSD 显示：接口契约

更新：2026-10-16。范围：`work/rtl/latency/latency_meter.v`、`work/rtl/osd/text_overlay.v`、
`work/rtl/osd/latency_osd.v`、`work/rtl/osd/char_rom.v`（生成）与 `work/rtl/osd/osd_layout.vh`（生成）。
本文只描述这些模块自身的接口与语义；不涉及 MIPI/DDR/HDMI 厂商 IP 的配置。

## 1. 模块图

```text
sof_frame_src (clk_src) ─┐
                         ├─ latency_meter u_meter_frame ─> lat_f_ticks / lat_f_cycles / err
vs (clk) ────────────────┘

sof_pipe_src (clk_src) ──┐
                         ├─ latency_meter u_meter_pipe  ─> lat_p_ticks / lat_p_cycles / err
vs (clk) ────────────────┘

rgb_in / de / hs / vs ──> text_overlay ──> rgb_out / de_out / hs_out / vs_out（延迟 3 拍）
                              ▲
                              │ 字符写入（仅 de 为低时）
                       格式化 FSM（每帧一次）
```

## 2. latency_meter.v 接口

| 信号 | 方向 | 位宽 | 域 | 语义 |
|---|---|---|---|---|
| `clk_src` | in | 1 | 源 | 源事件所在时钟（如 ISP/摄像头域） |
| `rst_src_n` | in | 1 | 源 | 异步复位，低有效 |
| `src_token` | in | 1 | 源 | 每次有效沿表示一个被测量的源事件；高电平宽度任意，但必须能被 `clk_src` 采到 |
| `clk` | in | 1 | 目标 | 时间基与出队所在时钟（如 HDMI 像素域） |
| `rst_n` | in | 1 | 目标 | 异步复位，低有效 |
| `out_token` | in | 1 | 目标 | 目标事件（同一帧/同一行的出口） |
| `err_clr` | in | 1 | 目标 | 清除两个粘滞错误标志 |
| `lat_ticks` | out | 32 | 目标 | 延迟，单位 0.01 ms（10 µs），合法于 `out_token` 后第 2 拍 |
| `lat_cycles` | out | 32 | 目标 | 延迟，单位 `clk` 周期，同上；用于审计与更高分辨率 |
| `lat_valid` | out | 1 | 目标 | 完成第一次测量后为高 |
| `err_overflow` | out | 1 | 目标 | 队列满导致某个时间戳被丢弃（配对已错位，粘滞） |
| `err_underflow` | out | 1 | 目标 | 空队列收到目标事件（粘滞） |

时序语义：

- 源事件以「翻转 + 两级同步 + 边沿检测」跨域，源脉冲宽度和两域频率比不影响正确性。
- 时间戳在目标域内由两个自由计数器产生：`cyc_cnt`（每拍 +1）与 `tick_cnt`（平均每 10 µs +1）。
  两个采样都取自同一域，因此差值精确，不存在跨域计数器相减。
- 事件跨域给每个测量值带来 **0–4 个目标时钟周期的非负偏移**（2 级同步 + 边沿检测 + 采样不确定性，
  74.25 MHz 下约 54 ns）。跨域测量值不会小于物理延迟。
- 出队与压队在同一拍发生时：若队列满且同拍有出队，压队仍然接受，不丢时间戳。
- 组对关系是「到达顺序」。`err_overflow`/`err_underflow` 一旦置位，后续读数都不能采信，必须
  `err_clr` 或复位后重新建立配对。若源端帧率高于显示刷新率（或反之），必须让时间戳队列深度
  覆盖最大在飞事件数，否则视同溢出。

### 2.1 10 µs 刻度生成（不推断除法器）

```text
TICK_BASE      = CLK_HZ / 100000   （整数部分，调用方用常量算出）
TICK_REMAINDER = CLK_HZ % 100000
TICK_MOD       = 100000            （要求 TICK_REMAINDER < TICK_MOD）
平均周期 = TICK_BASE + TICK_REMAINDER/TICK_MOD   [cycles]
```

模块内部只做「比较 + 相减」的分数累加器，没有除法器、乘法器或厂商原语。74.25 MHz 对应
`TICK_BASE = 742`、`TICK_REMAINDER = 50000`，平均 742.5 拍一个刻度。

刻度分辨率 10 µs 相对于精确比值的量化误差不超过 ±1 个刻度（±0.01 ms）。需要更高分辨率时使用
`lat_cycles`，再由软件按 `CLK_HZ` 换算。

## 3. text_overlay.v 接口

| 信号 | 方向 | 位宽 | 语义 |
|---|---|---|---|
| `clk` / `rst_n` | in | 1 | 像素域时钟与异步复位 |
| `de` / `hs` / `vs` | in | 1 | 有效像素与行场同步（标准电平型，`vs` 至少一个行周期为高） |
| `rgb_in` | in | 24 | RGB888，高位在前 |
| `we` / `waddr` / `wdata` | in | 1 / `ADDR_W` / 8 | 字符 RAM 写口；**契约：只允许在 `de` 为低时写** |
| `dbg_raddr` / `dbg_rdata` | in/out | `ADDR_W` / 8 | 仅测试与调试用的异步读口 |
| `rgb_out` / `de_out` / `hs_out` / `vs_out` | out | 24 / 1 / 1 / 1 | 叠加结果与**同样延迟 3 拍**的控制信号 |

几何：像素坐标由 `de` 自行计数（不依赖上游导出 `x/y`）。字符单元 8×8 像素，按 `2**SCALE_LOG2`
整数缩放；面板覆盖 `X0..X0+COLS*8*2**SL`、`Y0..Y0+ROWS*8*2**SL`。范围内的像素：
字符位为 1 时输出前景色；否则若 `PANEL_EN=1`，输出「背景」（`BG_DIM=1` 时为视频亮度减半，
即各通道右移 1 位；否则为纯色 `BG_RGB`）。范围外像素原样通过。

固定延迟：**3 拍**。数据、`de`、`hs`、`vs` 走同深度延迟线，下游不会看到错拍。这是纯行速率流水线，
没有帧缓存、不访问 DDR，但必须在端到端预算中计入这 3 拍。

帧边界规则：字符 RAM 只在 `de` 为低时写入，因此一个显示帧内不会混入两版文字。`latency_osd.v`
的格式化状态机在等待 `de` 为低时会停住，不满足条件就不写。

## 4. latency_osd.v 接口（本交付的顶层）

| 信号 | 方向 | 说明 |
|---|---|---|
| `clk_src` / `rst_src_n` | in | 源事件域（两个测量共用） |
| `sof_frame_src` | in | LAT-F 的源事件（如摄像头帧起始） |
| `sof_pipe_src` | in | LAT-P 的源事件（被测量流水段的起始，例如 DDR 读出后的帧起始） |
| `clk` / `rst_n` / `de` / `hs` / `vs` / `rgb_in` | in | 显示侧视频流 |
| `err_clr` | in | 清粘滞错误位 |
| `rgb_out` / `de_out` / `hs_out` / `vs_out` | out | 叠加后的视频（+3 拍） |
| `dbg_raddr` / `dbg_rdata` | in/out | 字符 RAM 读口（48 字节） |
| `dbg_lat_frame_ticks/cycles`、`dbg_lat_pipe_ticks/cycles` | out | 观测用测量值 |
| `dbg_err` | out | 4 位粘滞错误半字节（与屏幕上的 E? 一致） |

显示内容（16×3 字符，布局见 `osd_layout.vh`）：

```text
LAT-F DDD.DD MS      帧延迟：sof_frame_src → vs
LAT-P DDD.DD MS      流水线延迟：sof_pipe_src → vs
FRM ########  E#     帧计数（BCD，含前导零）与粘滞错误半字节
```

数值格式：0.01 ms 单位，三位整数两位小数，前导零显示为空格，超过 999.99 ms 饱和并置错误位 2。

错误半字节（`err_clr` 或复位前一直保持）：

| 位 | 含义 |
|---|---|
| 0 | 时间戳队列溢出：配对丢失，读数作废 |
| 1 | 空队列收到目标事件（例如上电后第一帧还没有时间戳） |
| 2 | 至少一个读数饱和在 999.99 ms |

错误半字节为 0 时显示 `E0`。上电后第一帧必然出现一次 `E1`（还没有时间戳），由系统在第一次
有效测量后拉高一次 `err_clr` 清除；测试台 `tb_latency_osd.v` 演示了这段时序。

## 5. 无除法、无乘法的实现

| 需求 | 做法 |
|---|---|
| 10 µs 刻度 | 比较 + 相减的分数累加器（见 2.1） |
| 0.01 ms 十进制数字 | 17 位 double-dabble（每帧 17 拍，在行消隐期内完成） |
| 帧计数 | BCD 纹波计数器（每位比较 + 条件加一） |
| 字符位图 | 生成式 `char_rom`（64 位常量 + 变量部分选择），95×8 位只读查表 |
| 面板背景减半 | 各通道右移 1 位 |
| 字符单元定位 | 移位与位选（`SCALE_LOG2` 为整数幂） |

`latency_osd.v` 与 `latency_meter.v` 内没有 `/`、`%`、`*` 运算；`osd_layout.vh` 与 `char_rom.v`
中的常量乘法只用于常量折叠。

## 6. 未验证与风险

- `unknown`：TD 综合后的 LUT/寄存器/ERAM 占用、Fmax 与 WNS。需要 TD 6.2.1 对
  `latency_osd` 单模块做一次独立综合，入口为 `scripts/build-latency.py`（本次未执行）。
- `unknown`：在上板工程中的插入点。LAT-F 的 `sof_frame_src` 需要接到摄像头/ISP 侧的帧起始，
  LAT-P 的 `sof_pipe_src` 需要接到被测量流水段的帧起始；这两点必须在 Goal 2 接口审计后确认。
- `inferred`：若显示通路经过 DDR 帧缓存，LAT-F 至少为 1 帧（30 fps 下约 33.3 ms），
  不可能达到 `<2 ms`；`<2 ms` 只能由 **不经过 DDR 的流式段**（用 LAT-P 测量）满足。
  该结论必须用真实工程与实测确认，不能仅凭本模块的仿真。
