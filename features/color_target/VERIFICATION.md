# TARGET 验证入口（2026-10-18）

当前交付是独立模块、A1 修复和集成审查资料。MAIN 尚未接入 TARGET；本轮没有新整机 P&R、bit 或板测结论。
`FILTER_ENABLE=0`，生产颜色门限不变。A2 身份/年龄仍是提案，不能把模型通过写成生产问题已解决。

## 1. 先判断要验证什么

| 层次 | 现在能做的工作 | 通过标准 / 证据边界 |
|---|---|---|
| 工具与独立功能 | 下述统一入口，保留命令/退出码/日志/源码哈希 | 子进程成功、完成标记和结构化报告均满足；不代表主线完成 |
| 当前缺陷 | TRACK 特征测试 | 复现 9 个采样及 6 个 OPEN_GAP；结果吻合只说明问题可复现 |
| 拟议系统契约 | 36 条独立故障轨迹 | 输入、硬预期、不变量、失败条件见 JSON 与 [故障矩阵](integration/FAULT_MATRIX.md)；不证明真实 CDC/DDR |
| 现有完整视频 | EDGE_CONTROL_V1 基线实板观察 | [观察指南](board/OBSERVATION_GUIDE.md)、[回报模板](board/REPORT_TEMPLATE.md)；该 bit 不含 TARGET |
| TARGET 整机 | 待 MAIN 获批接入后执行 | 契约冻结→真实顶层仿真→P&R→归档 bit→板测；现在为 OPEN / NOT_RUN |

`run_verification.py` 是已有自检的调度入口，不替代各测试的独立预期。
输出 `summary.json`、`REPORT.md`、各子进程原始 `.log` 和已有 runner 的结构化结果。
它同时保留两个结论：`checks_status` 与 `integration_ready=false`。
**退出码 0 只表示所选独立检查完成；TRACK 特征吻合仍显示 MATCHED / OPEN。**
非零退出、FAIL/Error 标记、缺少完成标记、结构化计数不全、超时或执行期间源码变化均失败。
超时保存已捕获输出，不生成虚假的 PASS。每次必须使用新输出目录；拒绝覆盖旧证据。
这里的退出码指 Python 子检查。既有 simlib 的 simulate 尚未逐层传播 vsim/vvp 非零退出码；
当前另以完成标记、错误文本及数据比较把关，不能据此声称已记录每一个仿真器进程退出码。

## 2. 可复制命令

从仓库根目录运行。使用真实 Python 3；ModelSim 通过参数或 `COLOR_TARGET_MSIM` 指定，
也支持已配置的 Icarus。路径示例需替换成本机实际值，不改变机器配置或 TD 工程。

```powershell
$targetPython = '<真实 python.exe>'
$targetMsim = '<ModelSim 的 win32aloem 目录>'
$targetRun = Join-Path $env:TEMP ('target-verify-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))

# 模型和数据契约，无需仿真器：3 项
& $targetPython -B -X utf8 -u features/color_target/run_verification.py --profile models --out ($targetRun + '-models')

# A1、TRACK 问题复现、动态文字和原链路：7 项
& $targetPython -B -X utf8 -u features/color_target/run_verification.py --profile quick --sim modelsim --msim $targetMsim --out ($targetRun + '-quick')

# 以上加全分类、720p 检测、框、既有 TRACK、真实字库、六尺寸双模式 RGB：13 项
& $targetPython -B -X utf8 -u features/color_target/run_verification.py --profile full --sim modelsim --msim $targetMsim --out ($targetRun + '-full')

# 验证入口本身：非零退出、无完成标记、FAIL+完成、超时及 OPEN 记账
& $targetPython -B -X utf8 -u features/color_target/tb/test_verification_runner.py
```

不要仅截取终端最后一行。交付 `REPORT.md`、`summary.json` 和相关失败日志；源码工作区不干净时，
必须同时保留其中的文件哈希和状态，HEAD 单独不能代表实际受测文件。
`--timeout-sec` 是单个子检查的上限，默认 1800 秒；调整它不能把已失败的检查改记通过。
全量流程不重复单独 support3 官方原语网表及 PNG 渲染；修改这些路径时，另按
[SUPPORT3.md](SUPPORT3.md) 和下表补跑，不能用全量入口声称覆盖所有工具。

## 3. 独立预期与必要回归

| 事项 | 独立预期 / 命令 | 最近已确认的范围 |
|---|---|---|
| A1 类别一致性 | `run_target_class_contract.py --out <新目录>`；12 项字面 gold，不从生产模型生成 | 4 公开结果路径×5 帧；修复前 5/12，修复后 12/12；仅 42 包 class 字段改变 |
| A1 两个模型 | 上一命令加 `--models-only` | 与同一外部 gold 比较 12/12；不能拿模型自己作标签真值 |
| 分类 | `run_color_classify.py` | 31 条手算锁定、40/40 参数组合、39079 像素、8/8 等价性 |
| 旧检测 / 旧链 | `run_color_target.py --full`；`run_color_target_chain.py` | 25/25 含 EOF 关闭硬预期；396 拍逐拍时序 |
| 框 / TRACK 既有行为 | `run_color_target_overlay.py`；`run_color_target_track.py` | 10/10+5/5；21/21 只覆盖原功能，不能关闭身份/年龄缺口 |
| 字段原子更新 / 字形 | `run_color_target_text_updates.py`；`run_color_target_text_overlay.py` | 7962 拍；真实字库 28/28、307078 像素；不保证整显示帧原子提交 |
| RGB 回放 / 数据 | `run_color_target_replay.py --full --out <新目录>`；`run_replay_data_checks.py` | 12 轮、7760408 像素、179 结果、178 跟踪、39928 显示查询、87 旧 RTL 对照、5 取消；17 数据检查 |
| TRACK 缺口 | `run_track_admission_audit.py --out <新目录>` | 重复、乱序、无效列、沉默、新 session 无效、旧 session 回返六缺口；生产 RTL 未改 |
| 系统提案 | `run_integration_contract.py --out <新目录>` | 36 轨迹、10 故障类别、3 撕裂 bundle 负对照；数值是夹具，非生产阈值 |
| 静态源审计 | `tools/audit_integration_sources.py --out <新目录>`（位于功能目录） | 21 文件；58/58 历史 MAIN 输入一致；当前 TD 中 TARGET 0 项；符号搜索范围有限 |
| 渲染 / 独立过滤原语 | `render_color_target_frames.py --out <新目录>`；见 SUPPORT3 | 历史合成渲染 768000 像素；过滤独立原语证据有单独源码版本 |

除不需仿真器的脚本外，以上仿真命令可追加 `--sim modelsim --msim <目录>`。
保留历史失败对照：[A1 记录](evidence/integration_audit_2026-10-18/A1_VALIDATION.md)、
[EOF 修复](evidence/eof_close_2026-10-18/VALIDATION.md)、
[文字修复](evidence/text_atomic_2026-10-17/VALIDATION.md)、
[RGB 资源迭代](evidence/replay_2026-10-17/VALIDATION.md)。
原始目录与哈希不覆盖。历史 `audit-final-sha256.json` 绑定 d905cdc 阶段文档快照；
后续入口文档修订应以新提交和新运行哈希为准，不能将旧文档哈希当作当前版本哈希。

## 4. 进入整机验证前的判定

必须先确认 [MAIN 契约草案](integration/MAIN_CONTRACT_DRAFT.md) 与
[A2 责任提案](integration/TRACK_ADMISSION_PROPOSAL.md)。重点是：

1. 规范化 SOF/EOL/EOF、坐标与 RGB 同拍。AWB user 是提前通知，不能直接连 SOF；掉拍、尾拍不足 4 像素须有独立错误依据和取消动作。
2. 唯一 `{session_id,frame_id}` 与 DDR 槽代次贯穿采集、完成、选帧、读预取到 HDMI。只加显示边界寄存器不能建立帧关联。
3. CDC 整包、容量、最坏停顿与双端复位屏障有证明；不能因平均每帧一次就断言单邮箱足够。
4. 框/十字/文字/count/state 一次提交，扫描期间稳定；文字内部 70 拍发布不代表已与外框同帧。
5. 重复、无效、有效无目标、超时分别处理；HOLD 需要真实观测身份和年龄。`TRACK` 状态单独不能证明当前观测新鲜。
6. 单目标/全部同色区域、最小目标、允许延迟、历史最大年龄、恢复策略和真实时钟资源预算由负责人确认；等待实拍再定颜色策略。

十类故障逐项都须有输入、硬预期、不变量与失败条件，执行顺序为
模型→适配器 RTL→真实顶层与多时钟仿真→静态 CDC/约束→P&R→实板。
同域主机回放无法替代后续各层。

## 5. 资源与板测证据分开引用

独立 RGB gate 架旁路 918 LUT/579 reg/0 ERAM/0 DSP，过滤 1224/950/1/0，
人工 10 ns，SWNS/HWNS 分别 1.170/0.502 和 1.140/0.292 ns；包含影子寄存器/观测选择器，
74 个未绑定 I/O，源版本 5565545。文字 gate 282 LUT/194 reg 源版本 172815e。
它们不能相加当整机增量，也不是 A1 后重新实现或布线后 Fmax。

历史 MAIN EDGE_CONTROL_V1 的完整 P&R 对应 dff499a，SWNS/HWNS 0.100/0.020 ns，
STA 覆盖率 96.14%，未包含 TARGET，板测仍待记录。LUT6 14724/21216、FF 14417、
Slice 16473/21216、ERAM 39/108、DSP 9/40 是 routed 口径；不要混用 gate LUT 口径计算余量。

目前适合做现有视频基线板测，同时继续完成接入契约。观察真实物体移动、模式/文字一致性、
冻结/旧帧/撕裂、明暗恢复和长时间运行。CNT 是 HDMI 侧事件计数，递增不能证明相机更新。
按 [模板](board/REPORT_TEMPLATE.md) 回报版本、操作、视频时间点、复现次数/分母和恢复方式。
无统计仪器时写“未观察到异常”，丢帧/溢出/精确同帧或延迟仍填“未测”。
