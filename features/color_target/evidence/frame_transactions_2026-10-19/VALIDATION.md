# FRAME_TRANSACTIONS_V1 本轮验证记录

基线：本地`codex/target/track-guard-v1`，开工HEAD `8f49444460472e71b3242630a5d94ae2cd2e978d`。
当前新源码最初为工作区新增文件，报告记录其实际LF SHA；不能把开工HEAD误说成已包含新增工具。
本轮只改TARGET测试/模型/文档，四个受测生产RTL以及全部既有生产RTL均未改。

## 最终结果

| 检查 | 结果 | 证据 |
|---|---|---|
| 联合帧事务模型 | 33/33 | [model-04](model-04/summary.json) |
| 生产guard+track+box+text，测试架调度 | 14场景187检查，0失败 | [rtl-02](rtl-02/summary.json)及baseline/logs |
| 故意破坏的五个调度策略 | 2/3/2/2/1断言失败，全部抓住 | rtl-02各mutation目录；18个工具阶段均exit0 |
| 原契约模型 | 36/36，10类 | [existing-contract-01](existing-contract-01/summary.json) |
| STYLE实际构建源清单 | 66/66精确来源绑定 | [source-proof-02](source-proof-02/summary.json) |
| 修改约束命令的负例 | 预期拒绝，退出1 | [负例](source-proof-negative-witness.json)及原始console.log |

模型不模拟物理CDC/DDR；RTL测试架的原子搬运、显示调度与独立年龄为提案逻辑。
不能据此声称MAIN已实现、CDC已签核或生成了TARGET整机bit。实际使用ModelSim ASE10.3c、Python3.12.14。
没有执行Icarus，没有重跑整个MIPI/DDR/HDMI物理联合仿真或P&R，也没有新的上板结果。

## 实际命令

仓库根目录，以本机真实Python和ModelSim路径执行；每次out均新目录，原证据不覆盖。

```text
python -B -X utf8 -u features/color_target/run_frame_transactions.py --out <本轮输出>/model-04
python -B -X utf8 -u features/color_target/run_display_transactions.py --msim D:/altera/14.1/modelsim_ase/win32aloem --out <本轮输出>/rtl-02
python -B -X utf8 -u features/color_target/run_integration_contract.py --out <本轮输出>/existing-contract-01
python -B -X utf8 -u features/color_target/tools/audit_build_source_manifest.py --source-root <固定042345源目录> --manifest <STYLE/SOURCE_MANIFEST.json> --download-records <main-source-download.json> --byte-reference-root <原字节证据目录> --newline-search-limit 20 --out <本轮输出>/source-proof-02
```

原始大资料和下载快照位于仓库外：
`C:/Users/Kelinna/Documents/Codex/2026-10-16/AnlogicTrack2/outputs/frame-transactions-2026-10-19/`。
上一轮原始STYLE清单在相邻`full-reassessment-2026-10-19/remote-project/pr-12/selected/`下，未修改。

## 迭代与失败均保留

1. model-01的25例先检查槽位/发布/扫描；自审发现尚缺不可信元数据统计约束，model-02补至26。
2. model-03补准备时间与reset排空前置条件，共29例。它尚把既有测试中的选帧时刻当成实际输出。
3. 最终model-04把read selection/prefetch与actual HDMI first pixel分开，补取消预取、重复首事件和输出起点年龄重查，共33例。
   前三轮的source SHA与最终版本不同，保留为演进记录，不冒充最终源码覆盖。
4. rtl-01为180检查、四个负对照；最终rtl-02增加观察时钟停止、显示侧独立年龄及第五个负对照，187检查。
5. source-proof-01返回63/66，SDC混合换行已重现，但三个官方文件raw字节尚未匹配。随后从用户已有官方资料
   取得精确原字节，既匹配归档SHA，又与固定Git文件的LF内容相同，最终66/66。
6. 初版源下载严格大小检查拒绝11个contents返回正文被变换的非UTF8源；改用Git blobs精确字节并校验Git SHA。
   一个审计脚本在实际构建commit尚不存在，改为只取该commit存在的66输入和两个构建/归档脚本；没有混用后来的脚本。
7. 用测试副本将create_clock周期20.000改为21.000，允许混合换行检索仍拒绝；不是通过放宽空白/命令比较获得66/66。

上述模型/工具迭代没有修改guard、track、文字转换、support3或MAIN生产逻辑。
source-snapshot是最终受测工具和TARGET模块的明确LF快照；原始ModelSim日志保持字节不变。

## 仍开放

- LATENCY满队列丢事件告警与恢复、32/32接口及时基迁移，未修改其生产RTL。
- MAIN真实观察sideband、缓存代次/完整提交/取消/读租约、排空屏障与实际首像素身份，未实现。
- 物理CDC服务/reset、Gray max_delay覆盖、FIFO稳态、时钟实测与长期板测。
- 真实文字shadow/commit或充分blanking准备窗口、共享字库/Logo区域以及生产年龄值。
- 最新MAIN候选与TARGET/LATENCY合在一起后的资源/时序，没有新的物理证据。

SDC来源疑点已经关闭；它与尚未关闭的Gray约束覆盖问题必须分开。
