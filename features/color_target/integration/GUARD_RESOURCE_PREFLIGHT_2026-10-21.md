# guard 独立综合与接入参数预检

日期：2026-10-21。角色：TARGET。承接 d247788，9 个生产 RTL 与既有交付完全一致。
本轮增加独立测试架、综合/验证工具和证据；没有修改 MAIN、LATENCY、颜色门限或 support3 默认值。

## 1. 已补齐的事实

TD V6.2.168116，`ph1_35p.db / PH1P35MDG324 / speed 3`，单个**人工 10 ns** 时钟。
顶层 `guard_synth_top` 内含实际 `color_target_track_guard` 及其内部原 TRACK。
输入影子寄存器可加载全部输入，所有公开输出进入采样寄存器并可经选择器读出。
这样既保留结果/诊断路径，也为 guard 的组合输入/输出建立实验寄存边界。
串行加载和观测接口仅用于测量，不能复制到视频生产通路。

| 实验配置 | 顶层 LUT | 顶层 reg | gate Slice | ERAM/DSP | SWNS/HWNS ns | STA coverage |
|---|---:|---:|---:|---:|---:|---:|
| active64：TIME_W=64，COUNTER_W=16 | 1132 | 1471 | 1113 | 0/0 | +1.494/+0.502 | 73.51% |
| active32：仅作位宽敏感性对照 | 936 | 1247 | 927 | 0/0 | +1.644/+0.502 | 72.72% |
| disabled64：年龄均为0的负对照 | 10 | 7 | 7 | 0/0 | +8.578/+0.502 | 61.51% |

有效配置的实验年龄为 1000003/2000003 tick，ACQ/LOST=3/15；这些不是生产推荐值。
禁用配置下 TRACK 被优化掉，证实用默认 0 参数会严重低估有效配置资源。
active64/active32 的层级报告均保留 guard 与 TRACK；运行器会拒绝有效配置缺失 TRACK 的报告。

**表中资源包含测试架，不是 guard 的独占用量，更不是整机增量。**
TD 层级原生口径为 `logic lut / ripple / seq`：active64 的 guard（含 TRACK）为 244/341/581，
其中 TRACK 为 53/0/101；active32 分别为 204/241/485 与 54/0/101。
这些列不等于顶层 `#lut`，不能把 ripple 与 logic lut 随意相加，不能再次加上已包含的 TRACK。
active64 顶层与 guard 的 seq 差值为890，是这份优化后网表的测试架寄存器差值，不能据此按比例扣减 LUT。

active64 最差 setup 路径：`sample_reg[221]`（I_now_tick[1]）→ 时间倒退比较/准入 →
`u_guard/u_track/acq_cnt_reg[4]`，报告逻辑级数8，数据路径8.442 ns。
active32 最差路径改为 reliable_tick 到输出采样寄存器，位宽减少不保证真实布局布线同比改善。
若以实验100 MHz解释32位tick，约42.95秒就回绕；本guard会使该run失效，要求新session。
所以本轮**保留生产64位接口**，没有为节省资源改变时基或会话策略。

## 2. 证据边界与判断

- 报告为 `Confidence: Synthesized`，未布局布线；人工时钟不能转换为板上Fmax或真实时钟预算。
- 测试架外部加载/选择/复位没有板级输入输出时序约束，STA coverage不足100%；
  本轮未证明全部路径约束覆盖。实际 MAIN 时钟、CDC、复位释放和I/O必须另行分析。
- 每组有 `SYN-6021 CRITICAL-WARNING`：顶层逻辑端口没有引脚位置（有效配置77个，禁用47个）。
  没有开启 unconstr_io，没有生成bit。这是独立测试架，不是可以直接烧录的工程。
- 不与历史 RGB/text gate 数字或 MAIN routed Slice/LUT相加计算“整机还够多少”。
  MAIN新增台账、CDC、显示适配的资源与真实布线压力仍未知。
- 当前测量没有给出必须改写guard生产RTL的证据。先保留现有实现，集成后再据真实关键路径优化。

## 3. 配置声明预检

`tools/check_target_config.py`检查显式JSON声明和9个TARGET生产源的交付哈希。
输入模板 `TARGET_CONFIG_PENDING.json` 保留生产年龄、tick频率、最迟显示起点和扫描预算为null。
这些值必须根据实际时基/缓存/显示约束决定，工具不替负责人填默认值。

检查包括：当前64位/16位接口、11/10位坐标、1280×720 RGB888/4PPC、MSB_FIRST、
support3关闭、严格同帧策略、ACQ/LOST的1..255范围、非零且可表示的年龄、正频率/扫描上界、
未知字段和重复键、布尔/浮点/字符串冒充整数，以及源文件是否仍匹配交付。
年龄预算用Python整数求和，超出两种年龄上界时给WARN，要求隐藏完整标注；不自动增大年龄。
这是保守声明的比较，不能预测实际选中帧何时显示。

| 退出码 | 含义 |
|---:|---|
| 0 | 配置声明完整、合法且TARGET源匹配；不认证真实接线 |
| 1 | 配置非法、重复键或源不匹配 |
| 2 | 存在未决值，或要求尚未验证的 integration 门 |

`--gate integration`不会因为所有声明合法而通过；当前始终保持 `integration_verified=false`。
工具**不解析/展开MAIN**，不证明实例实参、实际tick频率、帧身份、CDC、DDR租约或公共mask正确。
后续必须把声明与真实展开参数核对，并验证框/十字/文字/count/state由同一个观测一次提交。
尤其文字 `I_show=0` 仍有暗色覆盖，不能用它替代最终整组 `overlay_valid` 门控。
现有 [帧事务联动](FRAME_TRANSACTIONS_V1.md) 的14场景/5负对照是可复用测试依据，尚非真实MAIN适配器证明。

## 4. 可复现命令

从仓库根目录执行。工具路径均显式传入，输出必须为新目录。

```text
python -B -X utf8 -u features/color_target/run_guard_synthesis.py --td <TD/bin/td_commands_prompt.exe> --out <新综合目录>
python -B -X utf8 -u features/color_target/run_guard_fixture.py --sim modelsim --msim <win32aloem> --out <新测试架目录>
python -B -X utf8 features/color_target/tb/test_guard_engineering.py
python -B -X utf8 features/color_target/tools/check_target_config.py --config features/color_target/integration/TARGET_CONFIG_PENDING.json --out <新预检目录>
```

最后一条**应退出2**；复制模板并填入获确认的实际值后再运行，不能填实验值来消除UNKNOWN。
综合运行器退出0只表示三组测量证据完整；每组 `experimental_gate_timing_met` 单列，负slack不会伪装为时序通过。

最终：3组综合证据完整；新测试架6项公开输出硬检查通过；15个软件测试方法通过；
7个真实CLI场景退出码符合预期。既有818项guard契约及handoff16未因生产RTL不变而重复执行，旧证据保留。
失败尝试、源哈希、原始日志及报告见 [验证记录](../evidence/guard_engineering_2026-10-21/VALIDATION.md)。

## 5. 下一关

本轮提交前Git同步发现LATENCY从531ef61更新到d47b883，包含接口/排队变更；
旧531ef61审查仍保留，新版独立可靠性复核列为下一项，不先宣称旧问题仍在或已经修复。

MAIN确认基线、真实时基/年龄/扫描预算，核对实际参数并实现帧台账与可靠整包传递；
TARGET再针对真实适配器验证同帧整组显示、晚到/丢失、槽复用、显示重复/跳帧和停钟失效。
之后由MAIN完成整机P&R、版本绑定的新bit，再按现有TARGET板测模板验证。
没有新bit、没有TARGET实板结论；最小目标/多同色目标策略继续等实拍，当前不增加CCL/CNN。
