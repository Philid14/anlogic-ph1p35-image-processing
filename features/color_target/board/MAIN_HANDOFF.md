# TARGET 接入与上板交接入口

日期：2026-10-20。用户确认本轮“先上传 TARGET，由 MAIN 队友接入”。
本交付只修改 `features/color_target/`，沿原 PR #2 更新；不合并 main，不修改 MAIN/LATENCY。
**独立模块可供审查接入；尚无包含 TARGET 的整机 bit，当前不能用旧视频 bit 验收目标框。**

## 1. 版本与队友新增内容

2026-10-20续跑后再次同步核验的远端版本如下；这是一份固定快照，后续以 MAIN 选定的最新 SHA 为准。

| 工程线 | 分支与 HEAD | 与 TARGET 的关系 |
|---|---|---|
| main | `c42168e26026425660f2a6f51eec76b04c85eea0` | 尚未接入 TARGET |
| 最新 STYLE V2，PR #13 | `codex/main/edge-style-fill-v2` / `89093f428878b918036c8a30a0d1afe7764946b8` | 实际构建源 `694559fd76676093e134229d435161ecb44ab00c`；66项输入不含 TARGET/LATENCY |
| STYLE V1，PR #12 | `codex/main/edge-style-fill-v1` / `532d3c62bbc8d0c60d5def5e5233b035f2a9699b` | 实际构建源 `042345cb0e92a1cc5ea0a74fed1be352cf338f2c`；V2的回退候选 |
| 四模式，PR #11 | `codex/main/edge-multi-mode-v1` / `22690856d9a0c079485bedd916d9c8f7f116157b` | 实际构建源 `4ea67f194941c6717fc1d28889c687a4fb78533f`；可作为独立回退候选 |
| LATENCY，PR #5 | `codex/latency/same-frame-association-v2` / `531ef616dd53efa200e16b3839319f18b4c48d72` | 上次成功fetch的快照；32/32身份/完整事件/统计清零已推进，本包不改其源码；[独立复审与未决项](../integration/LATENCY_REVIEW_531ef61.md) |
| TARGET，PR #2 | `codex/target/color-target-detect-v1` | 包含 `8f49444` guard、`e995866`联合验证及本轮工具/交接修订；完整最新 SHA 见 PR |

2026-10-20后续复审：新fetch因网络失败，不能保证此表是此刻远端最新状态。
对固定531ef61已完成8项独立接口场景，2项控制通过、6项场景的7条安全要求失败；
重点是FIFO满时静默丢失、偶数次错误toggle抵消，以及恢复/权威会话/单侧reset/排空边界。
这是新增审查证据，不覆盖原handoff16，也没有修改任何生产RTL。
MAIN接LATENCY前须处理或明确这些依赖；TARGET guard不会自动保护LATENCY的独立事件入口。

V1→V2实际构建源的主工程差异已核对：仅 `isp/style_fill_96.v` 改动，AWB前后观察边界、
其余ISP、DDR/HDMI、TD与SDC不变。V2保留5拍局部STYLE、27拍分支对齐；TARGET仍观察风格化前彩色流，
不能从V2中性保护或描边后的像素调颜色阈值。V2 bit SHA实核对为
`CFB7435648ED50310F053AFE138702F2094B0061B6A7DD68B3B064B6B3D88F51`，1789539字节，仍不含TARGET。

不把另一工程线的顶层或 bit 混入。MAIN 根据实际风险、资源和板测选择STYLE V2或四模式等基线，
本包不替MAIN变更基线。这些候选都有完整历史构建，但不是接入TARGET后的资源/时序结果。
STYLE V2的ERAM85/108、Slice18140/21216，四模式ERAM75/108、Slice18319/21216；
不能只看单个资源数字决定整机能否容纳TARGET。既有FIFO/Gray约束风险仍需处理；
V2还记录既有I²C时钟缓存跨区的物理warning，MAIN指南要求至少3次冷启动检查，不把STA通过当作已验收。

## 2. 建议首接路径及明确依赖

建议第一轮采用严格光栅流封装、默认红色、`FILTER_ENABLE=0`，不改变生产颜色阈值。
下面是供 MAIN 核对的显式依赖，**不是已加入 TD 的清单，也不是新增接线授权**：

| 阶段 | 引用原文件（均位于 `features/color_target/rtl/`） |
|---|---|
| 颜色分类和固定光栅统计 | `color_classify.v`、`color_target_detect_stream.v`、`color_target_support3.v`、`color_target_mask_stats.v` |
| 观测准入与跟踪 | `color_target_track_guard.v`、`color_target_track.v`（后者由 guard 内部实例化） |
| 显示覆盖请求 | `color_target_overlay.v`、`color_target_text_overlay.v` |

`color_target_detect.v` 保留为旧路径/回归，不与流封装重复发布同一观测。
`model/`、`tb/`、`evidence/`、Python runner 都不是主工程综合输入；不能复制测试架的调度任务当作 CDC。
MAIN 直接引用上述已审查路径，避免另存一份生产 RTL。9个生产 RTL 的固定源版本为 `e995866`；
其精确 Git blob 和 LF 哈希见 [交付清单](TARGET_DELIVERY.json)，本轮只改工具与文档。

必须落实的连接顺序：

1. 在风格化前的彩色观察点扇出 RGB888/96bit/4PPC；lane0=`[95:72]`，每 lane=`{R,G,B}`。
   x0/y、SOF/EOL/EOF、32/32位 session/frame 必须与同拍 RGB 对齐；不能直接接 AWB 提前 user。
2. MAIN 独立确认采集完整/取消和 DDR 写入完整提交。TARGET 的检测完成不能替代 DDR 完成；
   缺失 EOF 不会自动形成可信取消。V1 无 lane_valid，不支持非完整4像素尾拍。
3. 流封装 `O_result_ready` 是结果发布脉冲，不是反压 ready。旁路结果在输入 EOF 采样沿后的第1拍发布，
   同步下游下一沿消费；CDC、guard、文字准备和显示排队耗时分别记入实际时钟域。
4. MAIN 将完整/取消结局与检测结果关联后送 guard。需要可信 session 控制、capture_tick、持续推进的 now_tick。
   两个年龄参数默认0会禁用准入，必须依据真实时钟/延迟显式确认，不能照抄测试夹具常数。
5. guard 的 observation key 与 positive box key 含义不同；HOLD保留旧框来源。
   `O_observation_usable` 不是最终显示使能，不能直接连接覆盖模块。
6. 结果跨域整包传输；按显示所选 `{session,frame,slot,generation}` 匹配，取得读租约。
   检测先于 DDR 完成时可暂存，但只有完整提交的像素帧可显示，租约期间不得覆盖该槽。
7. 文字输入、框、十字、count、state 来自同一观测，在显示边界一次提交并全扫描保持。
   文字稳定输入最多140显示拍可见；现有文字无观测ID/完成端口，MAIN必须证明准备窗口或另设计明确commit适配。
8. 最终共同 mask 应覆盖框、十字、文字和文字底色。文字 `I_show=0` 仍会请求暗色文字，**不能用它代替隐藏整组**。
   Logo/主线状态优先级保持；字库接入与共享区域由 MAIN 分配。
9. 显示侧在实际 HDMI 首像素处重查整扫描年龄；观察时钟停止后仍能独立失效。
   元数据不可信时隐藏整组标注，视频继续。DDR选帧/预取不是HDMI实际首像素，不能提前计时或统计首次显示。
10. reset/session切换须先终结旧DDR、FIFO、预取和扫描事务；清身份表不等于在途I/O排空。

详细端口与责任：[guard接口](../integration/TRACK_GUARD_INTERFACE.md)、
[帧事务方案](../integration/FRAME_TRANSACTIONS_V1.md)、
[MAIN契约](../integration/MAIN_CONTRACT_DRAFT.md)。
LATENCY接入前的问题输入见 [LATENCY可靠性需求](../integration/LATENCY_RELIABILITY_REQUEST.md)，本轮未向其他任务发送消息。

## 3. MAIN 接入前可立即复现的验证

从仓库根目录运行，输出目录必须全新；工具安装路径由本机显式传入，不修改 PATH 或 TD。

```powershell
$targetPython = '<python.exe>'
$targetMsim = '<ModelSim win32aloem目录>'
$targetRun = '<新的输出目录>'
& $targetPython -B -X utf8 features/color_target/tb/test_simlib_failures.py
& $targetPython -B -X utf8 features/color_target/tb/test_verification_runner.py
& $targetPython -B -X utf8 -u features/color_target/run_verification.py --profile handoff --sim modelsim --msim $targetMsim --out $targetRun
```

`handoff` 保留原13项含义，增加33项帧事务模型、9配置818项guard硬检查和14场景187项显示联动硬检查，
同时执行5个错误调度负对照。总计16个顶层任务；旧track特征测试应为 MATCHED / OPEN，不能把它标为已修复。
新profile目前限定ModelSim；Icarus失败注入属于工具模拟测试，不代表实际Icarus RTL仿真通过。
公共simlib逐个校验vlib/vlog/vsim或iverilog/vvp退出码与错误标记；原始工具日志保存在各任务 `*-tool-stages/`。
guard/display独立runner另有自己的逐阶段原始日志。入口总退出0仍表示独立检查完成，`integration_ready=false`。

本轮实际命令、源哈希、结果、失败尝试和日志索引见
[本次上传验证记录](../evidence/upload_2026-10-20/VALIDATION.md)。
旧证据保持原样，不用本轮工具修复反向重写历史PASS/OPEN结论。

## 4. 进入上板的交付门

MAIN完成接线后，先复用故障矩阵验证真实适配器，再跑实际多时钟顶层。
须有实际综合、P&R、Timing Check、bitgen，以及绑定全部输入的 BUILD_INFO/源码清单。
归档新bit到 MAIN 统一版本目录并签发新candidate tag；不得移动旧tag或复用旧bit冒充新TARGET。

实际 SOURCE_MANIFEST 必须包含本轮选用的TARGET模块及MAIN新适配器；
报告资源/Setup WNS/Hold WNS/未约束及Ignored路径、时钟、工具版本和仍在的warning。
本交付未重新综合guard，也没有整机增量资源或整机时序结论。

上板按 [TARGET验收方法](TARGET_ACCEPTANCE.md) 和 [TARGET回报模板](TARGET_REPORT_TEMPLATE.md)。
原 [EDGE_CONTROL观察指南](OBSERVATION_GUIDE.md) 保留为历史版本专用，不适用于STYLE五模式按键。
最新视频基线请从 MAIN 所选提交的 `docs/*BOARD_TEST.md` 读取，不能混用不同版本的K3/K4语义。

尚需MAIN/人类确认：基线、生产年龄与时基、CDC容量/失效恢复、字库/显示区域、完整/取消依据及排空屏障。
最小目标尺寸、同色干扰选择与颜色门限继续等待实拍；不在本轮增加CCL/CNN或开启support3。
