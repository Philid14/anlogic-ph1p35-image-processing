# 2026-10-23 取消与恢复复核、调试工具交付

结论：**正常路径可以继续受控板测；异常恢复尚未收口。** 本轮定位了一处确定的恢复误取消，以及取消后物理写入未收口的风险。另在尚未集成的LATENCY中复现两类反例。没有为了得到PASS修改预期或生产RTL。

## 任务与版本

- 用户确认来源：在“故障验证→板测记录工具→回放配置适配→LATENCY复核”的建议后回复“可以”。
- 角色TARGET，继续已有 `codex/target/color-target-detect-v1`；本轮起点49641eef。
- MAIN固定为5cbb1de3814a842067ee1ffd41df3d75bbf0de26；实际TD输入/bit版本仍是原STYLE_V2_TARGET_V1归档，不是本次生成。
- LATENCY固定为87bb9a5375843c4f3e9696eb0dbd028f3e364f47；不在上述TARGET候选bit中。
- 允许范围：`features/color_target/` 的独立测试、工具和证据；不修改MAIN/LATENCY/生产TARGET RTL、sensor、阈值、约束、TD入口，不烧录、不合并、不发送队友消息。
- 本轮独立交付无新bit或tag。基线main仍为c42168e；未将MAIN候选合入TARGET工作分支。

## 1. 已有读租约时半帧停钟

### 输入与独立硬预期

实际frame_system、observer、ledger、guard、96→128打包、video_in/out、命令FIFO、官方软FIFO和VTC均来自固定MAIN源码。RAW与post-AWB为合成场景，DDR为有界存储/服务模型。背景改为空间变化的灰度，使数据偏移不会被均匀背景掩盖；红目标仍按原合成ROI产生。

故障前必须实际提交至少3帧且持有读租约，不能仅用仿真时间声称前置条件成立。source6第360行、部分MC写入后停CSI65ms，DDR/HDMI继续；恢复原输入35ms。

硬预期：中断身份不提交/不用于显示，写入不碰已租约槽，所有物理读持有租约，命令计数守恒；每个提交必须有172800次MC接受且全部字节符合独立场景；至少两个后续完整帧恢复提交，且有恢复帧进入HDMI元数据选择。

### 真实结果

`warm-01`：16865008项限定检查通过，6次总提交，其中2次为恢复提交；2次取消；停钟期间有680396次租约保护的实际MC读。模拟器Errors0/Warnings18，原文保留。

| 事件 | 实测 |
|---|---|
| 停钟 | 约53.006ms，source6，key1/4，slot0/gen3，已接受85920字，leases=4（二进制槽2），FIFO报告50 |
| 超时取消 | 约105.007ms，key1/4；CSI仍停住，pending写已排空 |
| 恢复输入 | 约118.006ms，active=0、pending=0，但camera_we=1 |
| 首次取消后写 | 约118.014ms，仍是key1/4对应槽/代次，offset85920；空间场景字节立即不匹配 |
| 新事务分配 | 约123.338183ms，ledger已分配key1/5、slot0/gen4，FIFO残留186字 |
| 同沿错误 | 日志current key仍1/4，timeout=1、terminal_bad=0、mc=0 |
| 新事务被取消 | 紧接下一DDR沿，约123.338198ms，key1/5，accepted=0 |
| 后续恢复 | source8/key1/6和source9/key1/7各172800字后提交，提交字节错误0；后者进入显示元数据 |

取消后 `write_active=0` 期间实际接受259440次MC写。本轮累计1386240个字节不匹配均发生在未提交事务的写入中，所有最终提交都通过字节硬预期。**这不是已提交画面损坏的证明，也不是取消行为已正确的证明。**

本轮没有检查最终HDMI每个像素、标注整扫描过期或真实PHY。显示元数据中usable标注存在，不等于已经验证故障期间最终可见文字/框的像素。65ms停钟没有覆盖当前100ms年龄策略的全部超时范围。

## 2. 问题、完整逻辑链及MAIN方案

### R1：新事务使用旧采集时间，恢复误取消（P2，确定缺陷）

源码：固定MAIN `target_frame_system.v:103-108、226-228、235、284-285`；`frame_transaction_ledger.v` 的allocate_now、error_now及active取消分支。

1. ledger接受新begin后，active及allocated先变为1。
2. current_session/frame/capture_time在顶层看到registered allocated后才更新，晚一个DDR采样沿。
3. 这段间隔内write_active已经指向新事务，capture_timeout仍使用旧采集时间。
4. 旧事务因长时间停流已过55000tick，新分配事务于是立即满足超时。
5. ledger将该错误作用于新事务。事件日志同时记录“ledger分配1/5、timeout判据仍current1/4、无MC或坏terminal事件”，下一沿新事务取消，排除了仅凭时间推测根因。

**建议MAIN先设计原子事务上下文有效性。** 身份/时间/terminal状态必须属于同一个已分配FrameRef后才能参与超时与结束判定。最小候选是在上下文切换周期屏蔽旧判据，并对terminal同样验证上下文；最终实现由MAIN确认。不提高55000阈值掩盖问题。

不变量：`capture_timeout -> context_valid && context.FrameRef == active.FrameRef`。验证边界：首笔分配、取消后分配、同沿terminal/分配、真实已过期新帧、正常deadline均要检查，避免简单屏蔽吞掉真实超时。

### R2：取消后新写入及FIFO尾部未收口（P1待证风险）

源码：`target_frame_system.v:118、172-173、205-213` 的CSI许可及16个DDR周期flush；`video_in.v` 的FIFO占用触发突发及issued_words逻辑。

1. CSI停止，pack_open/pack_allow等CSI寄存器保持旧事务许可。
2. DDR超时取消并短暂flush。该flush持续约240ns，CSI在整个期间没有边沿。
3. flush结束，但CSI侧没有消费“该FrameRef已取消”的确认；恢复时旧帧尾部继续入FIFO并产生物理写入。
4. 被取消代次的259440次后续写、恢复时camera_we=1以及新分配时FIFO残留186字，均为本轮实测。
5. 本场景未写读租约，后继提交字节仍正确；但不能据此推广槽位复用、短空白/更不利服务情况下的安全性。

**不能只修R1就宣布恢复正确。** 本轮第一次新事务的误取消恰好又flush了一次残留FIFO。仅消除误取消后，残留186字是否会混入有效新事务，是必须验证的推论，尚未通过修改副本实验确认；本轮没有擅自改生产RTL验证它。

建议MAIN审核独立的取消闭环：DDR隔离被取消代次；停止为其发起新突发，允许已发命令排空；整包传递取消FrameRef；CSI丢弃旧尾部并确认；获得新的可信SOF/授权并清除残留后才释放隔离/复用槽位。CSI永久停住时HDMI应继续，控制链不能反压视频。不能只把16周期改成未经依据的长延时。

责任归属：MAIN持有CSI/DDR适配、槽位/租约和物理写权限；TARGET guard只能拒绝观测/隐藏标注，不能修复错误的DDR物理写入。

不变量：`新发写命令 -> 活动且未取消的写代次`；取消确认后不再产生该代次的新命令；槽位复用前旧来源和FIFO尾部均已隔离，读租约不被破坏。CSI停止、在途写、尾拍、同沿新SOF、取消消息晚到/重复及复位均需重测。

## 3. LATENCY 87bb9a5独立复核

旧V1审查台仍连接已删除的cap_too_fast，未连接新auth_sid/flush等端口；9项均设计加载失败，属于不兼容的测试证据，不是该提交9项功能失败。保留 `latency-87bb9a5-01`。

新增V2审查台只使用公开端口和独立字面预期。`latency-v2-01/02`两轮同样复现；第二轮添加实际payload日志确认旧事件身份。26项检查，23通过、3失败，对应下列两类问题。工具三阶段exit0、无Error，模拟器Warnings20；审查runner exit1正确表示需求反例，不把仿真进程成功当成全部通过。

### L1：目的域单侧复位重放旧事件（P1，针对模块声称的复位清空能力）

输入：事件sid1/fid1已入队，读取关闭；仅复位目的域，源域保持；恢复后等待40个目的周期再允许读。预期旧事件0次，随后新fid2应只新增1次。实际先收到fid1、再收到fid2，总次数2。

逻辑：`frame_event_bridge.v:172-176`将写指针同步器复位到0，而源写指针仍为1；`:205-209`的flush_active在同步器尚未恢复时看到“空”便提前结束；稍后真实写指针进入，旧事件重新成为evt_valid。等待普通消费者晚些开始读取不能解决此问题。

建议LATENCY/MAIN明确双侧复位与epoch握手，完成“同步指针已经有效”和“旧队列已隔离”的确认后再开放事件；resync必须同时关闭旧关联。固定等待若干拍不能替代可验证的reset契约。未修改LATENCY。

### L2：8位丢失计数整圈回绕隐去丢失（P2边界/服务契约风险）

输入：已完成启动的目的时钟停止；源每5周期发一次合法脉冲，共272次。16条入队，256条丢失。目的时钟恢复、读仍关闭；预期至少可见一次丢失指示。实际lost_count=0、lost_event脉冲0；随后只交付16条。

源码`:131-132`的8位err_bin/Gray计数256后回0；`:192-195`只比较本次同步值和seen_err，两者均0，无法知道中间丢失。两次丢失计数和20次满队列事件的会计检查均通过，说明这不是输出未接线或检测器始终无效。

这是长时间不服务目的域的边界探测，不等于正常逐帧流量下丢失统计均错误。建议明确最大无服务间隔/事件量，并在超过时保持可见的失效状态或要求epoch恢复；“每一次丢失必可见”的声明不能不带这个界限。单纯加宽只推迟回绕，仍需服务/复位契约。

当前TARGET候选没有接LATENCY；上述问题阻止对LATENCY异常恢复的全面验收，不据此虚构当前TARGET bit已有相同接线。

## 4. 板测工具与实拍准备

- `tools/check_board_run.py`：版本/实际bit SHA核对，明确OSD字段、同boot计数增量、16位饱和、复位/下降/缺测、文件证据哈希和观察项。永远NOT_CERTIFIED，不推导精确延迟或零丢帧；重复/跳过显示帧号本身不判异常。18项独立软件检查通过。
- `tools/prepare_candidate_replay.py`：沿用原清单/标注/指标，绑定实际MAIN配置及全部9份本地RTL（逐文件集合/哈希核验，显式区分原字节与统一CRLF转换）；拒绝错误tap或尺寸，不缩放标注、不给未知标注补“无目标”。5项软件检查通过，并实际执行1280x720合成输入CLI。没有使用真实相机素材或运行新的检测质量评估。
- 特别发现并明示：旧RGB回放含legacy tracker，不是当前guard时序验证。预检profile固定记录 `integrated_guard_temporal_replay_verified=false`。后续需显式控制/时间/取消/结果/显示事件，不能按想当然的帧率制造时间戳。
- 使用方法见[记录工具说明](../board/RECORD_CHECKER.md)。本轮空白记录CLI退出2（INCOMPLETE），真实候选bit哈希匹配也不能把没有观察的记录变成通过。

## 5. 可复现入口、证据与限制

以下均从仓库根目录执行。Git对象需已fetch，输出目录必须新建。先导出原始Git blob，避免CRLF转换或修改队友checkout：

```powershell
python -B features/color_target/tools/export_pinned_main.py --out <固定快照目录>
python -B features/color_target/tools/run_cancel_recovery_review.py --source <固定快照目录>/source --snapshot-manifest <固定快照目录>/snapshot-manifest.json --msim <ModelSim安装目录> --out <新测试目录>
python -B features/color_target/tools/run_latency_review_v2.py --msim <ModelSim安装目录> --out <新测试目录>
python -B -m unittest discover -s features/color_target/tb -p test_board_run_checks.py -v
python -B -m unittest discover -s features/color_target/tb -p test_candidate_replay_preflight.py -v
```

`evidence/cancel_recovery_2026-10-23/`保存summary、来源/哈希、原始日志zip。warm-01的events.txt是事务事件表；原始上一轮active-input-stop证据保留本机原目录，没有覆盖。
首次软件自检受限于Windows TemporaryDirectory权限，未执行到功能检查；正常本机环境最终18+5项全部通过。ModelSim同样使用正常本机环境，不安装/替换工具。原始zip内保留此前3项回放输入检查日志，最终补充日志还包括缺失/篡改RTL的拒绝检查。

本轮对原452份MAIN快照逐字节复核未变。导出器另从Git重建44份所需输入并逐blob验证；这44份是**所选数字测试输入**，不是完整TD工程交付。没有新综合/整机P&R/bit或板测，不能把本次检查数描述为实板稳定性证明。原MAIN资源/时序仍只适用于原route：Slice94.04%、ERAM91.67%、Setup/Hold WNS +0.165/+0.020ns。

剩余人工决策：MAIN确认取消/隔离/重启契约与具体生产改动；异常恢复允许丢多少帧/多长时间；LATENCY单侧复位与长时间停目的时钟是否作为支持场景，以及失效后强制resync机制。下一步先审查R1+R2组合方案，不能仅消除误取消而遗漏残留FIFO。
