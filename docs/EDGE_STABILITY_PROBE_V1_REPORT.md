# EDGE_STABILITY_PROBE_V1：候选交付报告

角色MAIN；日期2026-10-18（Asia/Shanghai）。本轮交付用于实板定位的诊断固件，尚未在本机烧录，未证实真实抖动根因。完成candidate后等待用户反馈。

## 1. 实现与实验变量

- AWB之后、Edge输入之前注入固定数字RGB；真实AWB的valid、提前SOF、tlast原样保留。按实际有效拍推进坐标，每个SOF重置，提前SOF不消耗像素。图中有高/低对比阶跃、斜边、矩形、固定纹理；不使用时间或帧号生成像素。
- EDGE显示固定图经原Gaussian/Sobel/NMS/四跳后的结果；ORIGIN显示实时摄像头RGB。Edge引擎在ORIGIN后台仍处理固定图，面板CRC不是实时原图CRC。
- 增加行/帧拍数、行数、SOF间隔、行内气泡及首位置、非四拍对齐段、实际128bit打包字数、Edge二值CRC、累计坏帧及CRC改变、实际FIFO写满/读空sticky与armed状态。
- 以上可从DDR前诊断OSD面板实际读取，无需假定UART或逻辑分析接口。未完整测量显示W；FIFO未armed明确为未测。面板数据通常滞后两个采集帧，以相同历史序号原子发布。
- Sensor/BLC/AWB参数、原算法、ORIGIN、K3/K4、旧MODE/THRESHOLD、安路Logo/CNT、720p、PLL/SDC保持；只读FIFO观察和新面板接入最小集成范围，不改数据请求/传输语义、打包器或DDR调度，不修改队友目录。

精确定义、位图及信号接线见[设计说明](EDGE_STABILITY_PROBE_V1_DESIGN.md)。Edge/Original 25拍、OSD 2拍、打包1拍，总28拍不变；吞吐仍每拍4个RGB像素/两个独立Edge采样点。固定图未解决原640点水平内部采样限制。

## 2. 已验证与尚未证实

独立软件模型定义测试图、25个合法TH的CRC及白点数。新RTL完整720p六帧通过1382400有效拍/1036800打包字，覆盖实际isp_top的AWB后边界、真实packer、Original保真、两种SOF、帧内配置锁定和完整新旧OSD像素；另有小尺寸联合验证。

独立单元实际复现行内1+15分段导致打包288→287字、两次phase事件，并检查缺tlast、截断、CRC改变、FIFO实际观察接线和复位/启动屏蔽。序号缩减为16bit后补跑小尺寸联合及3bit参数13帧跨回绕单元。旧QUALITY旁路/分类/四层连接/按键/CDC/Sensor无重配置/字库回归通过。完整720p测试后只改诊断启动屏蔽与内部序号，分别局部回归；不冒称对最终版重新执行了完整PHY仿真。

这证明受测数字条件下固定输入与现有算法可以稳定确定，并证明监测器能够报出受控异常；不能证明真实摄像头确实存在气泡、AWB波动、打包丢字、RAM物理错误或CDC失败。尚无真实连续RGB或板上内部采样。完整记录见[验证及失败记录](EDGE_STABILITY_PROBE_V1_VERIFICATION.md)与[数字证据](edge_stability_probe_evidence/README.md)。

## 3. 完整构建与资源

| 项目 | 本轮最终路由 | QUALITY对照 |
|---|---:|---:|
| LUT6 | 15415（72.66%） | 16162 |
| FF | 16334（38.49%） | 15423 |
| Slice | 16872（79.52%） | 17894（84.34%） |
| ERAM20K | 47/108 | 47/108 |
| DSP | 9/40 | 9/40 |
| Setup WNS | +0.102ns | +0.009ns |
| Hold WNS | +0.020ns | +0.020ns |
| Setup/Hold TNS、违例端点 | 均0 | 均0 |
| STA coverage | 95.98% | 96.11% |

全设计净差：LUT −747、FF +911、Slice −1022，ERAM/DSP不增加。固定数字源可触发综合简化，整体重新映射亦改变资源；不能把资源下降宣传为正常实时RGB算法的优化成果。诊断没有新增像素流水级。

Synthesis → Physical Design → final Timing Check → bitgen全部实际完成。最差Setup仍在HDMI mixer，15级、75.002MHz；MIPI域+3.711ns，DDR user域+2.341ns。此前R0完整bit因Setup−0.051ns未签发，已独立归档和保留tag；最终仅缩减诊断序号后重新完整构建，未改HDMI/时钟/SDC。

主要风险：PHY-5060/PHY-5079仍存在（I²C/相机时钟混合扇出及局部时钟路由），无新增关键warning类型；两组Gray max_delay各18路径仍被clock_groups忽略。正裕量不等于长期硬件稳定，也不证明旧抖动已修复。约束修复须另做精确端点/例外范围、每位延迟与总线偏斜及完整STA/实板验证，本轮没有直接可用的已验证替代SDC。

## 4. 最少上板步骤

1. 先用旧QUALITY bit、相同TH80录制10–30秒，保存真实Edge抖动对照。
2. PROGRAM_SRAM烧录本轮candidate，等待面板V、SEQ推进、FLAG低三位均1。记录九行数值并拍摄10–30秒，排除动态CNT/SEQ区域。
3. 保持TH80，正常期望IN=`00038400`、PACK=`0002A300`、LINE=`02D00140`、CRC=`6B6DB7D0`、ERR/COUNT为0；两FIFO都armed且没有事件时FLAG=`00FFFFF7`。GAP高16位取实测SOF间隔，不预填；低16位为气泡数，应为0。
4. 移动/遮挡摄像头，固定EDGE图及CRC不应随物体变化。K3切ORIGIN确认实时彩色，再切回EDGE；K4仍短按减10、长按加10。TH60参考CRC=`2B018224`，TH40=`417312EE`。门限切换后的正常CRC变化不计为闪烁。
5. 将面板、固定图是否抖、ORIGIN/Logo/CNT、触发动作及运行时间反馈。异常时记录后回滚QUALITY。

V不是“系统健康”的缩写，只代表三组历史测量序号一致；须结合FLAG/计数/CRC。面板本身经过DDR/HDMI，若W、停更或撕裂，不能使用最后一组值证明正常。完整步骤、屏蔽区域、十六进制位定义及反馈模板见[实板操作](EDGE_STABILITY_PROBE_V1_BOARD_TEST.md)。

## 5. 如何判读、下一步查哪里

| 结果 | 下一步优先调查 |
|---|---|
| 固定图稳定、CRC匹配；旧实时QUALITY仍抖 | 优先采真实RGB/AWB增益/ROI逐帧变化，量化阈值、NMS峰位和强锚敏感性；不能仅据此断言AWB就是根因 |
| 固定图抖且CRC变化，输入/pack计数亦异常 | 保留首气泡位置与phase/行帧错误，复现真实控制触发条件，先做最小链路修复方案 |
| 固定图抖且CRC变化，控制数量正常 | 优先Edge状态、行缓存/RAM复位与映射、物理时序；需要错误触发采样或合法独立控制进一步隔离 |
| CRC稳定匹配但显示抖 | 优先CRC之后的RGB复制位、OSD、打包内容、DDR/HDMI；CRC不是完整DDR读回校验 |
| armed后FIFO sticky发生 | 确认真正read_en&&empty/write_valid&&full及发生时刻，分辨启动/稳态/重置，不把普通empty当故障 |
| 稳定但CRC不匹配 | 先查bit/TH/稳定帧/数量，仍不符则不能因肉眼稳定就判算法正确 |

CRC只取每拍两个二值代表位，可能碰撞或漏掉复制RGB位错误；新诊断还改变物理布局。旧QUALITY与probe应交替验证，避免把探针影响当成已证明的旧版故障。

下一阶段必须由这些板上证据决定：输入侧研究、链路最小修复或缓存/时序定位。本轮没有开发时间滤波、时域滞回、NMS升级或更多连接跳数。

## 6. 版本与回滚

- Version：`EDGE_STABILITY_PROBE_V1`。
- Branch：`codex/main/edge-stability-probe-v1`；base `8b3b9853cb900ca2305872b4ad9e129274efdbdf`（PR #7），QUALITY归档基线b64daf3。
- 实际构建源码：`131afb0a745c62f119e1ae2f869788f45944f4a2`；63项TD输入SHA清单随bit归档。candidate tag落在包含最终bit和文档的归档commit；两者通过BUILD_INFO关联，不混淆源码/归档SHA。
- Candidate tag：`edge-stability-probe-v1-candidate`，通过`git rev-parse edge-stability-probe-v1-candidate^{commit}`解析归档commit。
- Bit：`artifacts/bitstreams/EDGE_STABILITY_PROBE_V1/camera_to_dsi_display.bit`，1789539 bytes。
- SHA-256：`7A78AFBC6126CDA8860E70241DA7AA934C68B0C98D1DB02E7FD2F7790A061980`。
- [BUILD_INFO](../artifacts/bitstreams/EDGE_STABILITY_PROBE_V1/BUILD_INFO.md)及其build_evidence包含最终原始日志/资源/时序、所有输入与构建前16份bit不变清单；没有覆盖任何历史归档。
- PR采用独立Draft并以仍未合并的`codex/main/edge-stability-diag-v1`为base，依赖#7→#6→#4→#3；不合并、不配置auto-merge。实际URL/推送状态以最终交付消息为准，未成功前不预称已上传。
- 回滚：重新PROGRAM_SRAM烧录原`artifacts/bitstreams/EDGE_QUALITY_V1/camera_to_dsi_display.bit`，SHA `629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5`。不移动旧tag，不替换归档。

真实上板结果：**待用户验证**。等待Philid14审查最新提交，停止于本轮诊断candidate。
