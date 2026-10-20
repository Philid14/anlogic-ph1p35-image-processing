# LATENCY 531ef61 与 TARGET 接入边界复审

日期：2026-10-20。TARGET 分支基线 `a715061`，LATENCY 固定为
`531ef616dd53efa200e16b3839319f18b4c48d72`，MAIN/STYLE V2 分别为 `c42168e` / `89093f4`。
本轮原生 Git fetch 网络尝试失败；收口时改用 GitHub API 读取远端 HEAD，确认上述三个分支均未变化，
回执见 `evidence/latency_handoff_2026-10-20/remote-verified.json`。不将API核验写作原生fetch成功。
未修改 MAIN、LATENCY 或 TARGET 生产 RTL。结果是独立接口审查，不是整机接入、物理 CDC 或板测。

## 1. 新版确实推进的部分

与旧 `9e598f03` 比较，源码已采用默认 32/32 位 session/frame，新增 kind=2 完成事件；
首次显示要求记录已完成，重复显示单独输出 AGE。resync 清 count/sum，面板增加 AVG/CNT/ALM。
本轮实际 RTL 控制场景验证了：完整帧首次显示计一次、重复显示不加 count；
resync 清 count/sum 并使统计无效，新干净配对可开启新统计窗口。
这些已推进项不再作为旧版缺陷继续报告。

队友文档所述 20 场景、720p 面板和平均值回归是其已有记录，本轮未重跑；
本轮不验证字体、AVG 除法或真实计时误差。源文件行号均指上述固定提交。

## 2. 定向输入、独立预期和结果

时钟夹具：源 10ns、目的 14ns；暂停时停在目的时钟低电平。均不代表实板时钟。
8 场景、31 检查，所有前提检查成立；2 控制场景满足要求，6 场景共 7 项安全要求失败。
24 次 vlib/vlog/vsim 全部退出 0。运行器最终退出 **1**，`evidence_valid=true`、
`requirements_satisfied=false`、`integration_ready=false`。成功形成反例不等于功能 PASS。

| 项目 | 明确输入与独立预期 / 失败条件 | 实际结果与意义 |
|---|---|---|
| 正常与重复 | 同键 start→complete→display→display；count=1、repeat=1、alarm=0 | 通过 |
| 统计重同步 | 一次有效统计后 resync；count/sum=0、stats=0；新键干净配对后 count=1、stats=1 | 通过 |
| FIFO 满 | 桥接收端 ready=0，源送 20 个间隔 5 源拍的事件；再每 7 目的拍取一个。每个事件应交付或产生可见 loss | 前 16 个顺序正确，4 个消失，两端告警均 0；失败 |
| 偶数次错误 | 目的停钟，源先送一次合法事件，再在两拍间隔送两次过密事件；恢复后必须看到错误 | 源公开 toggle 确实变化两次并回到 0，只有 1 个合法事件到达；目的 alarm[2] 始终 0；失败 |
| 表溢出恢复 | 同 session 连续 9 个未完成 start 填满 8 项表，溢出后清告警，再完成/显示第 9 帧；按建议安全策略需 resync 才能恢复 | 清告警本身不恢复，但新配对直接令 stats=1、count=1；两项失败。**恢复策略须确认** |
| 旧会话回返 | session1 干净配对→session2 干净配对→迟到 session1 的 start/complete/display；旧数据不能成为换回会话的权威 | 第三次仍产生新有效延迟；失败。需外部权威会话准入 |
| 目的单侧复位 | 桥已交付 fid11、源保持运行；只复位目的读侧，再稀疏出队；旧包不能再次算新事件 | 同一 fid11 再次交付，总数从 1 变 2；失败。需双端复位/epoch 屏障 |
| resync 在途 | 目的停钟时排入旧 start/complete；恢复首沿 resync 清表；旧包不得被当成新 epoch 观测 | 队列随后交付旧包，显示仍被计入，count=1；失败。清关联表不等于排空桥 |

完整输入是 `tb/tb_latency_handoff_review.v`，预期是字面计数和公开输出，没有使用 LATENCY 模型或内部表状态作真值。
31 检查含场景前提。运行器要求固定检查名、唯一完成标记、计数一致、工具成功；
前提失败、编译失败、缺检查、工具中止均不能充当缺陷复现。证据解析器另有 4 项失败注入测试。

## 3. 严重程度、源码逻辑链与责任

**P1：桥满时静默丢失。** `frame_event_bridge.v:93–113` 用 `~full` 阻止写入，
但 `cap_too_fast` 仅由 `:73–74` 的间隔条件翻转。合法间隔且 full 时，事件既不入队也不报错。
缺失 start/done/abort 使关联台账不完整，不能依据“未显示该帧”豁免事件守恒要求。
本测试使用桥的合法停收接口；meter 当前 ready 常 1，**不能据此说正常视频帧率下已发生丢包**。
LATENCY 可增加可靠 loss 状态；MAIN 必须另证明服务/停钟边界与失效恢复。

**P1：无应答 toggle 无法保证连续错误可见。** `frame_event_bridge.v:74` 每次错误取反，
`latency_meter.v:284–290` 用同步后的 XOR 检测。两次取反若都落在目的采样间隔内，
目的只看到未改变的电平；“慢目的时钟也不会漏采”的接口说明缺少成立条件。
不能用加一级同步器修复偶数次抵消。应由 LATENCY 选择保持至应答的粘滞失效、握手或
有界计数方案，并定义清除与恢复屏障；任何方案都不能反压视频。

**P1 接入策略待冻结：异常后的自动恢复。** `latency_meter.v:392–395` 在表满/同键重采集时
置 stats=0，但 `:415–424` 的 commit_lat 直接置 1，没有“等待 resync”的锁存状态。
队友原 s6 证明了“alarm_clr 本身不恢复”，没有证明“之后的配对也不能绕过 resync”。
本轮要求来自 TARGET 既有安全恢复提案，不擅自将它当成 LATENCY 已冻结承诺。
MAIN/LATENCY 应确认是可自动恢复的局部未匹配，还是破坏关联可信度的全局故障；
建议 loss/overflow/reset/timebase 故障必须显式 resync，普通未匹配可独立定义。

**P1 接入依赖：权威会话与排空。** `latency_meter.v:280–281,361–376` 将任意不同 sid 的
start 视为切换；模块没有外部授权会话端口。`frame_event_bridge.v:117–143` 单独清目的读指针，
源写指针和内存仍在；已退休数据可重放。`latency_meter.v:346–359` 的 resync 只清关联表，
没有清除桥内在途事件。这三项是未经外部协议包围的组件行为，不冒称已实现 MAIN 出现故障。
MAIN 必须过滤非当前权威 sid，并在旧 DDR/FIFO/预取/扫描已终结的屏障后恢复；
TARGET guard 的会话权限不自动保护另一个 LATENCY 入口。

## 4. 本轮收口与下一步

旧版[修复输入](LATENCY_RELIABILITY_REQUEST.md)保留为历史，当前判断以本页固定版本复审为准。
不把这些用例混入原 handoff16 的 PASS 数；原16项回归和其历史证据不变。

推荐分成两个可并行交付的里程碑：MAIN先确认共同会话、完整/取消、排空、TARGET结果CDC与独立可信时基，
先做固定标注→实际TARGET的最小闭环，再进行真实多时钟顶层/P&R/新bit/板测。
LATENCY同时由维护者收口可靠loss与恢复语义，真实适配器通过本页故障注入后再进入该闭环。
这是接入建议，尚未实施或改变MAIN构建配置；TARGET不能直接借用当前有缺口的桥或把meter内部计数当可信跨域时基。
允许首个TARGET候选暂不启用LATENCY功能，有利于分别归因；不因LATENCY未验收而把独立TARGET工作全部停住。
队友可直接对新 SHA 重跑本 runner，相关要求失败数应下降；修复后的其他旧回归也需由维护者保持。
MAIN 仍由队友接入，本轮不改其生产文件、不私发消息或评论、不增复杂算法或修改颜色阈值。

复现命令（仓库根目录，输出目录必须新建）：

```powershell
python -B -X utf8 features/color_target/tb/test_latency_review_evidence.py
python -B -X utf8 -u features/color_target/run_latency_handoff_review.py --revision 531ef616dd53efa200e16b3839319f18b4c48d72 --msim <ModelSim目录> --out <全新输出目录>
```

退出 0：全部要求满足；1：有效证据中存在功能要求失败；2：工具/检查不完整，证据无效。
证据见 [VALIDATION](../evidence/latency_handoff_2026-10-20/VALIDATION.md)。
资源/时序边界：本轮仅 ModelSim 独立仿真，无综合、P&R、Fmax、bit 或板测结论。
原视频候选依然不含 TARGET/LATENCY，不能用于验收本页关联功能。
