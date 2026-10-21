# STYLE_V2_TARGET_V1 集成工作记录

日期：2026-10-21。角色 MAIN。人类授权：本轮 MAIN_STYLE_V2_TARGET_INTEGRATION_PROMPT。

## 固定基线与范围

- MAIN：`89093f428878b918036c8a30a0d1afe7764946b8`，STYLE V2 PR #13，未合并。
- TARGET：`49641eefc8bab37de3cd1b9d7f95a0051a0f0d1e`，PR #2；2026-10-21 fetch 与 API 确认头相同。
- TARGET 九份生产 RTL：`e9958669a3ce04b544f012b29bf80a1f9025384f`，按交付 JSON 核验 blob 与 LF SHA256。
- 分支 `codex/main/style-v2-target-v1`，从固定 MAIN HEAD 新建。直接导入原目录，不合并队友分支、不复制算法。
- STYLE V2 用户反馈“效果不错，仍有提升空间”只作为定性意见；30分钟、零溢出、冷启动未据此认定通过。
- 不接入 LATENCY，不修改 Sensor/ISP 算法、按键、五模式、PLL/引脚/原 SDC，不覆盖既有归档。
- 开工 tracked clean；根录像、PDF、参考工程及未跟踪 `docs/PROGRESS_REPORT_2026-10-21.md` 为用户资料，排除本任务提交。

## 已核实的接口缺口

原 `video_in` 在提前 SOF 轮转写槽并设置读指针，没有完整提交和读租约。
`I_mipi_rx_error` 目前常零。相机 FIFO 每帧复位，复位源跨域；写突发/命令 FIFO 在途并不由该复位终结。
原 `video_out` 在 VSYNC 设地址、复位像素 FIFO，没有总读字数界限或在途返回排空屏障。
`mc_to_user_interface` 的 user ready 表示命令 FIFO 余量，实际 MC 接受点是 `O_mc_app_en` 与读/写命令。
这些是代码事实，不表示已证明实板正在持续丢帧。

观察点是 `isp_top.awb_O_tdata/valid`，CSI 域、96bit/4PPC。
AWB user 是提前通知；last 是 valid 下降沿，均不能直接作为 TARGET 同有效拍 SOF/EOL。
生产 TD 引用 `isp/csi_unpacket_2lane.v`，其没有 CRC/ECC 错误输出。不能将计数正确冒充已经验证 MIPI CRC。

## 设计检查点

1. 固定来源、复跑 TARGET 独立交接与工具失败注入，保存真实退出码。
2. 有界台账先独立 RTL 验证：真实写接受计数、取消/代次、读租约、排空屏障。
3. 最小多时钟固定标注，证明整包传输、像素身份、文字准备、首像素年龄和共同遮罩。
4. 实际 TARGET/guard 进入生产路径；启用64位时间与16位诊断，整体 SYN 资源预检。
5. 全尺寸像素/元数据/五模式回归，完整 TD 后才签发 bit、tag 与板测交接。

2026-10-21：初步生产接线已写入隔离分支，尚未通过整体验证，不可上板。
独立测试/新适配器检查点不得描述为整机完成。原 TARGET 配置模板保持 UNKNOWN/exit2，不改队友工具。
75 MHz HDMI、1650×750 时序不变；完整扫描 1,237,500 显示时钟、16.5ms（配置计算值，非实测）。
先核对真实 DDR 最坏服务和排空行为，不用无限等待或随意年龄值掩盖异常。

## 原有风险

STYLE V2：LUT6 17170、FF16814、Slice18140/21216、ERAM85/108、DSP21/40，WNS +0.100/+0.020ns。
两组 Gray max_delay 被全局异步时钟组忽略；FIFO 稳态、I²C 跨区 clock warning 未关闭。
新增 CDC 不能凭异步例外宣称覆盖，须另列握手保持、复位屏障、服务界和物理路径检查证据。

## 当前交付状态

研究/独立验证进行中；无本版本 bit、candidate tag 或上板结论。
回滚继续使用 `edge-style-fill-v2-candidate` 原归档，SHA256 见来源清单。

## 初步适配实现与资源预检边界

- `frame_transaction_ledger`：4个有界槽，32位代次，采集身份高水位；保留读租约与最新完整回退帧。
  172800个实际MC写接受、独立RAW/观察/打包检查通过后才完整提交。取消等待写流水排空。
- `frame_bundle_cdc`：单包邮箱，3级请求/应答同步及2拍总线稳定等待；源端锁住整包直到应答。
  源/目的任何单侧复位异步关闭双方，分别同步释放；这只取消元数据，不冒充外部DDR排空。
- `target_observer_adapter`：实际RAW首个valid发行key/time，彩色流提前user只武装，SOF/EOL/EOF与有效4PPC同拍。
- `target_frame_system`：新DDR路径采用原两只安路128bit FIFO；读/写限定172800字，保留240字突发与原仲裁。
  分开计命令发出和MC实际接受、未返回读请求；复位屏障在扫描结束、命令/读返回排空后才刷新FIFO并换session。
- `mipi_packet_monitor`：仅被动检查RAW10的WC1600、物理HS包803个16bit拍；不宣称检查了CRC/ECC。
- `target_display_commit`：真实输出首有效像素检查FrameRef/box key及整扫描年龄；最多140拍字形转换前预留142拍。
  所有正常图文一次锁存；错帧、缺结果、时基不可信、超龄整组隐藏。正常显示统一增加1拍，DE/HS/VS/RGB等长。
- 共用mixer字库；保留Logo/状态/CNT区域，TARGET文字(24,640)，诊断两行(24,680)/(24,696)，未来LATENCY(24,192)不占用。
  诊断第一行完整S/F/G及slot、D整帧丢弃/C取消/Q恢复计数；第二行D/R/W/I/V/C/S/T/O为guard的九类16位饱和计数。
  `!`表示元数据链路不可信，数字是最后一组显示选择快照。诊断行与正常标注分开标识，不把历史快照当作当前可靠检测。

### 时基和初版年龄预算

公共64位master由75MHz HDMI每75拍递增，标称1MHz，经整包邮箱传播CSI/DDR；采集首像素取CSI最新快照。
时间量化与CDC延迟待物理检查，不能称微秒级实测精度。结果停止时master继续运行，显示域独立判龄。
两个guard年龄显式100000 tick=标称100ms，TIME_W64/COUNTER_W16，ACQ/LOST3/15，过滤旁路。
这是最多约6个显示刷新周期的首版失效策略，不是测得的最优跟踪年龄。
写事务55ms看门狗，完整后结果最多等待5ms；完整像素可先显示，缺少匹配结果时隐藏标注。
新的完整帧在下一16.5ms刷新选择；标注首像素硬门为age<=83499，加完整扫描16501共100000 tick。
晚结果/重复显示只可在此门内附着，显示重复不刷新capture_time。100ms之外整组隐藏，不能靠新到达包延寿。
正常消隐期从VSYNC下降到首像素约19行，约31350显示拍，实际多时钟回归仍须核实prepare窗口。

当前新增适配器的独立检查通过不关闭整体DDR/CDC/复位、完整720p与STA门；启用结构先SYN测资源。

## 首次实际综合资源门

实际源码 `a12057b644f20163203f8472e29d7a0b9a4efa7f`，81个实际TD输入，61个既有冻结输入逐项一致。
`syn_preflight_02`完整SYN、fresh gate DB及流程完成标记通过：gate #lut27595、reg23891、
Slice估算23153/21216(109.13%)，ERAM85/108、DSP21/40。
它不是路由资源，未执行P&R/bitgen，不能套用旧版WNS。
层级原生口径：台账logic921/ripple82/seq1596；显示邮箱seq997；整个TARGET采集侧seq6351。
先做单一资源优化：台账时间/标注payload去掉复位，保留清零的complete/annotation_valid/lease位，
将只有一个同步读取端口的payload数组请求映射到ERAM。保持64位时基、16位诊断、槽身份和所有保护。
这是用尚有余量的ERAM减少宽元数据FF/选择逻辑，不改变STYLE、颜色阈值或时序约束。
台账41项同一功能检查再次通过；须以第二次真实综合确认推断效果，不能预报节省量。

`syn_preflight_01`是工具调用失败：Windows反斜杠脚本路径被TD解释为转义，进程退出0但未运行流程。
已保留原始输出并修正为POSIX路径；构建运行器现在还要求显式流程完成标记和新生成数据库，不能只凭退出0。

## 本轮收口状态

第二组整体SYN为gate估算22754 Slice、89 ERAM、21 DSP；随后真实布局打包为21825 Slice，
被PHY-9053容量门拒绝，超过21216上限609。route/bitgen未执行，未创建candidate tag，也没有新上板bit。
实际整体FIFO/HDMI联合回归未完成；不将独立组件检查或固定TARGET回归换算为整机通过。
本轮以资源门失败的WIP检查点收口。最终结论、原始证据和最小后续方案见
`docs/STYLE_V2_TARGET_V1_RESOURCE_REPORT.md`，不继续本轮算法或STYLE画质开发。
