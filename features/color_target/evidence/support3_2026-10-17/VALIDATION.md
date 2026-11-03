# 候选 A：4PPC 中心支持过滤独立验证

日期：2026-10-17。基线：`50417686154021d4c810db43571d40a6b38d8d4e`，
分支 `codex/target/color-target-detect-v1`。源码为本文件所在提交，RTL、测试台、模型及脚本的
LF 归一化 SHA-256 见 `source-sha256.json`，同时记录只读厂商模型的原始文件哈希。
接口、异常帧约束和读写调度证明见 [SUPPORT3.md](../../SUPPORT3.md)。

**独立原型通过；默认 ENABLE=0；未接入旧检测器或主工程，未布局布线、生成 bit 或上板。**
没有真实 RGB/噪声/光照数据，算法质量结论仍以研究报告的限制为准。

## 1. 最终功能验证

Python 3.13，ModelSim ASE（由 `--msim` 显式传入），不依赖额外 Python 包。
帧集合 oracle 枚举像素邻接，不复制 RTL RAM、流水线或调度器。
每个有效输出逐项检查 mask、原图坐标、SOF/EOL/EOF、session/frame；EOF 检查最终 abort。
TB 每拍检查未覆盖 ENABLE 参数的实例，确认发布默认是寄存一级旁路。

| 配置 | 输入时钟数 | 比对输出拍 | 比对像素 | 完整输出 EOF |
|---|---:|---:|---:|---:|
| 六种小尺寸，含 512 邻域×4 lane 对齐 | 223880 | 150136 | 600544 | 2192 |
| 1280×720 RTL | 6108022 | 4377438 | 17509752 | 18 |
| 1280×3 TD gate 网表 + 官方原语 | 28263 | 18078 | 72312 | 18 |

小尺寸为 4×1、4×2、8×1、8×3、12×7、32×9。统计为确定性结构回归，
包括异常帧和显式复位前的输出前缀，不是独立实拍样本或检测精度测量。
完整帧用例包括全 0/全 1、孤立末 lane、边界/跨 lane、对角线、2×2 噪团、随机密度、
随机 valid 间断、帧 ID 回绕、session 切换、完整帧 abort、错误身份/行尾/坐标和复位清尾。
协议错误必须置诊断粘滞位，错误完整帧 EOF 必须带 abort；正确下一帧不继承 abort。
截断帧仅经复位恢复；原型不承诺无需复位的重同步。

前两帧没有任何行/帧消隐，逐拍检查输出连续，没有边界气泡；每拍四个 lane 全部比对。
每个非复位丢弃帧的输出 EOF **恰好晚 WIDTH/4+2 拍**：1280 宽为 322 拍，
不依赖后续帧或未来 valid。输出行首/行尾零填充与集合模型一致。

原始统计与输出摘要：`rtl-small.json`、`rtl-1280x720.json`、`gate-1280x3.json`。
最终全尺寸输出摘要 SHA-256：
`613ba79ff48f2969a0bfad0be6989f3f8160d9fd61a6212c7ff1a4e0ee46397f`。
小尺寸日志/完整帧日志附于本目录；原语仿真的警告分类、通过行和完整 transcript 哈希
见 `gate-sim-summary.json`。完整 transcript 保存在本机本轮输出目录，未提交厂商模型或网表。

## 2. 厂商原语揭示并修复的问题

第一版同拍读写两行 RAM，依赖混合端口同址读旧值。RTL 仿真通过，但 TD 映射合并 RAM 后，
官方原语功能仿真在连续帧边界读到了新首行：1280×3 全 1 帧末行首拍期望 `1111`，
实得 `0111`（第 1923 时钟，输出第 1600 拍），左边缘被误删。

最终改为**输入写入延后一拍**，旧上行地址在覆盖前一拍读出；宽度为一拍时显式转发最新中心拍。
不再依赖混合端口读旧值。修正后同一拍为 `1111`，且全部 gate 用例与独立集合 oracle 一致。
小尺寸和 1280×720 在修正后完整重跑，输出摘要保持一致。

早期 gate 测试架另有一次过早读取观测选择器的问题：0.01 ns 未覆盖厂商 LUT/pad 传播延迟，
出现错误身份。已将三次公开端口探测分别等待 1 ns，均在下一时钟沿前完成；
之后才定位上述 RAM 错误。未修改厂商模型或网表来绕过检查。

原语网表为 **1280×3**，使用与正式宽度相同的行 RAM 地址范围，缩短高度用于验证同址读写、
尾部调度、异常帧及复位。没有 SDF，不是 1280×720 网表时序仿真或实板证据。
网表使用未连接原语默认端口，ModelSim 报 142 次 3017、2805 次 3722；
另有 29 次 3016 连接类型兼容警告，对应官方模型的 tri0/tri1 类型输入（d/ce/dia）。
保持厂商模型与导出网表原样，未屏蔽警告；本次是 **0 errors、2976 warnings** 的功能比对通过，
不报告为零警告。统计见摘要，后续整机集成仍需复核对应工具/模型版本。

## 3. TD 综合与资源

TD **V6.2.168116**；`ph1_35p.db`、PH1P35MDG324、speed 3；
`analyze → elaborate → read_sdc → optimize_rtl → optimize_gate`，脚本为 `tools/synth_support3.tcl`。
以下两组均是 **1280×720**，保留所有输出可观测的同一 3:1 选择器测试架。

| 测试架 | LUT | 寄存器 | ERAM20K | DSP |
|---|---:|---:|---:|---:|
| 默认旁路 | 32 | 94 | 0 | 0 |
| 启用中心支持，最终修正 | 335 | 465 | 1 | 0 |
| 测试架总量差 | +303 | +371 | +1 | 0 |

报告为工具 `#lut/#reg` 总量，不混用 hierarchy 的 `logic lut` 列。
两行逻辑位存储 2560 bit 被合并为一个物理 ERAM20K；物理占用不是仅 320 byte。
初版为 322 LUT/444 reg；最终修正增加 13 LUT/21 reg，消除了已证实的读写冲突。

完整模块有 191 个内部逻辑 I/O，超过封装的 160；未修改芯片或关闭检查。
测试架用选择器将所有输出分三组观测，总 I/O=130，选择器计入上述数字。
它只用于资源/功能检查，不是板卡接线建议。

10 ns 合成时钟约束下，最终 gate 报告 SWNS=3.813 ns、HWNS=0.292 ns；
见 `enabled-gate-timing.txt`。这是 **gate 估计**，没有实际布线、主工程路径和完整 I/O 时序约束，
不能当成真实 Fmax、板卡 setup/hold WNS 或整机 100 MHz 承诺。
存在已知 **SYN-6021 CRITICAL-WARNING：130 个 I/O 均未绑定位置**。
未使用 `unconstr_io` 或生成 bit；最终 setup/hold、主工程余量和实板稳定性均未测。

## 4. 自检负对照与复现

仅在输出目录生成故障变体，未修改交付 RTL；三种都必须以非零退出：

- 阈值 3→2：4×1 的全 1 帧错误保留边缘，期望 `0110`，实际 `1111`。
- 末行读请求误用当前输入 session：连续帧 session 混入，被身份比对抓住。
- 禁止 EOF 自动结算：缺少输出 EOF/像素，在复位前完整性检查失败。

断言记录见 `negative-controls.json`。

```text
python features/color_target/run_color_target_support3.py --out <out>/small.json
python features/color_target/run_color_target_support3.py --geometry 1280x720 --out <out>/full.json
```

两条均按机器配置增加 `--sim modelsim --msim <ModelSim/win32aloem>`。
原语检查先在空目录运行 TD 脚本（`COLOR_SUPPORT_TEST_HEIGHT=3`），再运行：

```text
python features/color_target/run_color_target_support3.py --geometry 1280x3 --gate-netlist <support3_gate.v> --td-sim-dir <TD/sim_release> --out <out>/gate.json
```

本机完整过程日志：`AnlogicTrack2/outputs/support3-2026-10-17/`（位于本任务工作区外层）。
最终通过文件前缀为 `fixed-quick`、`fixed-full`、`gate-short/fixed-result`；
`sim.log/sim-retry.log` 是保留的早期失败，不能作为最终通过报告。

下一阶段：保持旁路，收集/确认最小目标与噪声保留集；B 的弱桥归属、碎片重组仍是研究问题。
MAIN 的接入、异常帧适配、预算、CDC、显示帧匹配与上板验证尚未完成。
