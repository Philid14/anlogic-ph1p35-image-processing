# 整合交付验证（2026-10-18）

用户授权：“你把目前做的工作整合优化一下，然后进行上传，更新验证方法”。
交付沿原 TARGET 分支 / PR #2；不合并 MAIN，不扩展生产改动权限。
本记录是提交前的真实验证快照，实际上传 SHA 以 Git/PR head 为准。

## 1. 基线与实际变更

- 原远端 `codex/target/color-target-detect-v1`：b4565a152458d251d694d850a48058a325d66bfb。
- 已有本地 A1：1e541f193c14d9cf98f767a62f6a16782612ea4c；审计：d905cdcf49105c7d4cca707026949dde1a66f17f。
- 整合前 C 在隔离审计分支 d905cdc/clean，D 规范检出与 PR #2 在 b4565a1/clean；远端 OPEN、保留 Philid14 请求、无 auto-merge/review。
- A1 两个生产 RTL 和两个模型的变更原样保留；本轮未继续修改 RTL、模型、阈值或 MAIN，support3 仍关闭。
- 新增 `run_verification.py` 和失败注入自检；统一 INTEGRATION/INTERFACE/README/DEMO_STEPS/TASK/REPLAY_MAIN_CHECKLIST，新增 VERIFICATION 与 board 指南/模板。
- 纠正早 SOF、EOF 拍号、边界寄存器不能建立同帧关联、TRACK 状态不能证明新鲜、单邮箱服务能力和 gate/routed 资源混用。固定 RED 文字模板单独列为非红显示限制。
- 原 [PROJECT_REVIEW 基线](PROJECT_REVIEW_BASELINE.md) 按原字节归档，SHA 与旧 baseline.json 一致。它描述 b4565a1 的历史状态；其中 A1 未修、未上传等句子不代表当前交付。当前审计见 `../../integration/ENGINEERING_AUDIT.md`，当前入口见 `../../VERIFICATION.md`。
- 既有 evidence 目录及失败对照未覆盖。历史 audit-final-sha256 绑定旧文档快照，新交付使用本目录新 manifest。

## 2. 执行与结果

Python 3.12.14；ModelSim ASE 10.3c（原始 transcript 版本行；位于本机 Quartus 14.1 安装目录），实际入口见 [完整 argv / Python版本 / 源码哈希](full/summary.json)。
从仓库根目录执行：

```text
python -B -X utf8 -u features/color_target/tb/test_verification_runner.py
python -B -X utf8 -u features/color_target/run_verification.py --profile full --sim modelsim --msim <本机win32aloem> --out <新的full-01目录>
python -B -X utf8 -u features/color_target/tools/audit_integration_sources.py --out <新的source-audit目录>
```

| 检查 | 结果与独立含义 |
|---|---|
| 验证入口失败注入 | 修正前 5/6、exit1：Windows CRLF 导致正常 DONE 被误拒绝；保留 before.log。仅规范化解析视图，原始输出不改。修正后 6/6、exit0；涵盖子进程失败、缺完成、FAIL+完成、超时及 OPEN 记账 |
| 全量调度 | 13 项完成、各 child exit0；12 CHECK 通过，1 CHARACTERIZATION 匹配且 OPEN；source_unchanged_during_run=true；integration_ready=false |
| A1 RTL / 两模型 | 各12/12；RTL四结果路径×五帧=240包；未变更原独立字面 gold |
| 拟议系统契约 | 36/36、10类故障；含三个撕裂 bundle 拒绝；仅模型提案 |
| TRACK 当前特征 | 9采样吻合，6 OPEN_GAP 保留；不是生产需求通过 |
| 数据 / 分类 | 17数据检查；40/40配置、39079像素、8/8等价性 |
| 原检测 / 原链 / 几何 | 25/25含720p、396拍、10/10+5/5 |
| 原 TRACK / 文字 | 21/21；动态7962拍；真实字库28/28、307078像素 |
| RGB | 六尺寸×两模式12轮；2013324输入时钟、7760408接收像素、179结果、178跟踪、39928查询、87旧RTL对照、5取消 |
| 静态及源一致性 | 21文件/58TD入口，缺失0、TARGET0；MAIN历史输入58/58相同；A1受测源10/10仍匹配旧 manifest |

13项概要见 [REPORT.md](full/REPORT.md)，详细数据见各子目录与 .log。
RGB 179/178 是复位在结果发布后、TRACK 消费前取消一次，不是未解释漏包。
生成图像和大体积仿真临时输入留在原运行目录，可按确定性命令重建；逐帧 JSON/CSV 和哈希已归档。
本次未重复独立 support3 官方原语网表或 PNG 渲染，引用其历史指定版本证据。
完整测试结束后仅补充文字类别限制等说明；生产 RTL、模型、测试及入口源码未变。
新增入口记录的是 Python 子检查退出码。既有 simlib.py 的 simulate 尚未将 vsim/vvp 非零退出逐层返回；
本次还依靠完成标记、错误文本和精确结果比较判定。底层各进程退出码的统一传播仍有改进空间。
A1 transcript 中未接 O_protocol_error 的告警保留；该测试核查类别结果，不声称覆盖该诊断口。

## 3. 问题、严重程度与未关闭项

| 项目 | 状态 / 严重程度 | 原因与下一步 |
|---|---|---|
| A1 分类与标签 | 已修并复验 / 原P2 | 非法配置回退红时标签也为0；独立负对照已在旧证据保留 |
| TRACK 身份/年龄 | OPEN / 集成前P1 | 重复与乱序可确认，invalid/silence不超时，新旧session权威缺失；先批准A2责任方案，再做生产适配 |
| MAIN规范化/错误/DDR/CDC/显示整组 | OPEN / 集成前P1 | 早user不可直接当SOF、错误口接0、缺frame_key/generation闭环；负责人确认草案后实施并做真实多时钟验证 |
| 非红文字模板 | 已知限制 / P2 | 当前字符固定RED，无类别输入；当前红色演示不受影响，非红显示需批准适配 |
| 相机语义/门限 | PENDING / 需求与数据缺口 | 等待实拍；单/多目标、最小尺寸、延迟/历史年龄、恢复、真实预算待决策 |
| TARGET整机P&R/bit/板测 | NOT_RUN | 独立功能通过不建立相机→HDMI证据；先做现有视频基线板测与契约审阅 |

没有把已知问题复现记成问题解决，没有为了 PASS 删除失败日志。

## 4. 资源、时序和实板边界

本轮没有运行 TD 综合或 P&R，没有生成新 bit/tag，也没有执行下载。
历史独立 RGB gate 架与文字 gate 均有工具/源码版本边界，不能相加作整机增量；
历史 MAIN routed dff499a 未含 TARGET。完整口径见 VERIFICATION.md §5。
归档 EDGE_CONTROL_V1 bit 的实际 SHA256 再核对为
`05E05B153800E38982D7D1C2981A347B3616EAFA6EABA91A43443468FAF5DCF6`；这只是文件身份，不是新板测。

下一步由负责人审查最新提交，按 board 指南收集现有视频基线的真实运动/冻结/撕裂/模式/明暗/长测记录；
再批准 A2 和 MAIN 适配责任，完成身份闭环与真实顶层证据。不要先加候选分离或 CNN。
