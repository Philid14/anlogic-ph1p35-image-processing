# EDGE_STABILITY_PROBE_V1 设计与诊断边界

2026-10-18，MAIN，TEAM_PROTOCOL_V1。人类授权见本轮EDGE_STABILITY_PROBE_V1任务附件。

## 开工与范围

- 算法基线：QUALITY候选`b64daf39af09980621adb1138df1674a8501ea09`；其实际算法/约束文件不改。
- 诊断资料基线/分支起点：`8b3b9853cb900ca2305872b4ad9e129274efdbdf`，tag `edge-stability-diag-v1`。
- 新分支：`codex/main/edge-stability-probe-v1`。开工PR #3/#4/#6/#7均未合并；本轮Draft PR base选`codex/main/edge-stability-diag-v1`，保留依赖，不合并历史PR。
- 角色MAIN；允许范围为主工程的诊断选择、观察端口、DDR前OSD、独立测试和构建归档。不涉及队友独立模块/接口，没有通知其他聊天的授权，未对外发送协作消息。
- 开工跟踪文件干净，既有2026-10-05目录和额外原理图/摄像头资料保持未跟踪。所有代码/测试使用仓库相对路径。

## 实现选择

在相同时钟域插入无延迟固定RGB组合选择；原始RGB延迟路径、valid/user/last、既有25拍Edge、两拍OSD和一拍打包保持。
仅新增两个TD源码入口：`isp/probe_fixed_rgb.v`、`isp/probe_stream_monitor.v`，原61项变63项。算法Gaussian/Sobel/NMS/四跳源码逐字节不改。

正式Top显式`PROBE_ENABLE=1`；isp_top/edge_control_stream/OSD/video_in/video_out默认0可旁路。Top回退以重新烧录原QUALITY bit为准，不把新probe bit冒充原版本。

### 固定数字源

- 放在AWB之后、`edge_control_stream.u_edge.I_tdata`之前，Original寄存路径继续接真实AWB RGB。
- 仅RGB替换；实际摄像头产生的valid、提前SOF与tlast原样进入Edge，不生成独立时序，不添加像素/标记流水拍。
- `u`可无valid：每次u归零坐标；同拍valid消费第0拍，后续只在valid时推进；每320拍换行，每720行回绕。tlast独立监测，不拿未经验证tlast重建图像坐标。
- 低有效复位，帧内容不依赖帧号、CNT、时间、按键或真实RGB。正常完整帧中每个位置RGB完全一致；异常SOF或丢valid可使坐标重启/错位，属于被测故障，不能声称这种情况下物理位置还恒定。
- 每拍两个独立灰度采样，各复制为两个RGB888像素，lane0为[95:72]。RGB均为8bit灰度，不引入ROM、乘法器或整帧缓存。

1280×720定义（x为0..639的内部横采样，最终每点复制2像素；y为0..719）：

| 行区域 | 灰度定义（默认48） | 目的 |
|---|---|---|
|0..127|32≤y<96且64≤x<512为192|高对比直边/矩形|
|128..255|x≥320为64|低对比阶跃|
|256..383|x≥4×(y mod128)为128|斜线|
|384..511|x96..99/500..503及局部y16..19/108..111构成160灰度框|几何轮廓|
|512..639|x[3] XOR y[3]为1取96，否则48|固定细节纹理|
|640..719|x[5]为1取112，否则48|竖纹|

独立NumPy实现和全部合法TH10..250步进10的CRC/白点数：`tests/probe_reference.py`、`docs/edge_stability_probe_evidence/fixed_reference.json`。
`fixed_rgb.png`是数字源定义；`panel_reference.png`是实际字库的**软件预览**，数值不是实板测量，示例SOF间隔60不代表实际固定值。

## 真实数据观察位置

1. AWB后、注入前：真实iv/iu/il。计原始每行/帧96bit有效拍、SOF间隔、气泡和非四拍对齐valid段。
2. 原Edge输出、状态及诊断OSD之前：实际二值输出和自身valid/user；每拍左右两独立二值采样各1bit做CRC32，统计有效拍数和相同相邻TH下的CRC变化。
3. 原打包器输出：实际128bit valid/user，计整帧字数。**不修改打包器，不修补缺失片段。**
4. video_in相机域FIFO：新增只读full_flag连线，对armed且非FIFO reset期间的valid&&full锁存写满事件。
5. video_out HDMI域FIFO：原empty_flag与实际FIFO read enable；先观察到连续三个完整172800字的采集帧，再跨域同步ready、再等两次输出vsync后，非FIFO reset期间读空锁存。不得把摄像头启动前的显示空帧或消隐empty当读空故障。
6. HDMI域独立、单调的armed/sticky经两个目的触发器到MIPI域；不是传输多位帧身份/计数总线，不承担帧匹配。原DDR/FIFO读写逻辑完全不变。

计数CRC只旁观，不施加ready反压，不改变像素数量。FIFO full/empty取自当前实际IP端口，不假设UART、网口或板载ILA已经可用。
新观察端口使原先未使用的full标志参与实现，资源/路由可能变化；需本轮实际TD结果，不能套用旧版。

## 实际视频语义

- 正常每行320个96bit拍，720个tlast，每帧230400拍；每帧172800个128bit字。
- AWB的O_tuser是原始提前通知，和首valid不必重合；独立行缓存读出产生连续行。SOF到首valid按MIPI周期计，允许0（同拍），不随意设非法阈值。
- 行长度在实际tlast结算，包含同拍valid。也接受紧随末valid的invalid tlast；同拍或后跟形式都不会将正常行间消隐记为行内气泡。
- 气泡定义：上一拍valid、本拍invalid，前/本拍均无tlast，当前累计行有效拍严格在1..319之间。
- phase事件：一个连续valid段结束时长度mod4非0。一次气泡可结束两个非对齐段，所以气泡1次并不保证phase只计1次。例如一行16拍分为1+15，phase计2而pack少1字。
- 每个观察级在各自SOF结算前帧；原始SOF再将已完成且序号一致的三组影子寄存器原子发布。正常约滞后两个采集帧；不是正在显示视频帧的性能统计，不冒充LATENCY的同帧身份接口。
- 面板再在该帧状态OSD的SOF锁存，避免帧中改变显示。开始无完整采样、级间序号不齐时显示W，低位valid=0，保留旧数值为无效，不报告“正常0”。

## HDMI可实际读取的面板

DDR前X16..527、Y352..671，16字符×10行，32×32字符（复用既有16×16字库2倍），黄色字/深灰底。原MODE/THRESHOLD区、Logo/CNT位置不动。
所有数字**十六进制**。OSD随缓存像素一起显示，无新增显示侧宽总线CDC；不是读出帧身份确认。SEQ用于确认历史样本持续更新，不能当摄像头到HDMI延迟。
`PROBE FIXED V1`是固定Edge实验固件标识；实际显示源以原MODE文字为准。MODE=ORIGIN时仍显示实时摄像头，CRC始终观察并行运行的固定Edge分支，**不是ORIGIN真实RGB的校验**，不能据此证明Sensor像素逐帧一致。

| 行 | 字段 | 正常预期/解释 |
|---|---|---|
|PROBE FIXED V1 V/W|版本、固定源及测量有效|W等待/采样不齐，V为完整历史样本可读；ORIGIN仍真实彩色|
|SEQ|32bit历史采集序号|应持续变化；不要求与显示CNT相同|
|IN|32bit零扩展帧拍数|00038400 =230400|
|PACK|32bit零扩展打包字数|0002A300 =172800|
|CRC|32bit算法二值平面校验|TH80:6B6DB7D0；TH60:2B018224；TH40:417312EE|
|LINE|高16位tlast行数、低16位最后一行有效拍数|02D00140 =720行/320拍|
|GAP|高16位SOF至首valid周期、低16位该帧气泡次数|高位实测，不预填；低位正常0|
|ERR|高16位行长度错误次数、低16位phase异常段次数|完整正常数据应0|
|COUNT|高16位累计坏帧、低16位相邻同TH CRC变化次数|65535饱和；坏帧=输入/行/Edge拍数/打包数量异常|
|FLAG|高8位sticky事件、接着20位首气泡坐标、低4位有效性/arming|无气泡位置FFFFF为N/A；不能误读为坐标或错误|

FLAG位图（计数清零需重新PROGRAM_SRAM或真实系统复位，不修改K3/K4）：

| 位 | 含义 |
|---:|---|
|31|armed后HDMI FIFO读空事件|
|30|armed后相机输入FIFO写满事件|
|29|Edge输出帧拍数异常|
|28|出现非四拍对齐连续valid段|
|27|打包帧字数异常|
|26|出现行内valid气泡|
|25|输入帧拍数/行数/行长度异常|
|24|曾出现相邻同TH、完整Edge帧CRC不同|
|23:14|该历史帧首气泡行号（按tlast计数）|
|13:4|首气泡前已收集的行内拍数（不是原图像素坐标）|
|3|保留0|
|2|HDMI FIFO observer已armed（三完整采集帧+同步ready后两次输出vsync）|
|1|相机FIFO observer已armed（一次相机SOF后）|
|0|历史三组测量序号一致、可读|

两FIFO都armed且数据完整、无事件时FLAG=00FFFFF7。未armed字段属于未测，即使sticky=0也不认定正常。
FIFO/CRC变化累计位是截至发布时的全局历史；IN/PACK/CRC/LINE/GAP/ERR/首气泡是SEQ标识的历史帧。COUNT为累计值，不按单帧清零。
长度/帧拍计数饱和（输入/Edge/pack19bit，行/行长10bit），事件计数16bit饱和；过长帧仍能判不等于正常值，不冒充无限精度。

## 能定位什么，不能定位什么

- 固定源且相同TH时，CRC应匹配软件参考并保持；若CRC变化而控制正常，Edge状态/映射/物理实现优先。若控制异常，先定位控制，不将CRC变化归因算法。
- CRC稳定且等于参考、画面仍变：算法之后的打包/DDR/HDMI优先；PACK/phase/FIFO可进一步区分，但本轮没有打包内容或DDR读回CRC。
- CRC仅覆盖二值平面每拍两代表位，存在CRC碰撞、未覆盖颜色复制位/传输位错误；相同CRC不是逐像素一致的数学证明。面板自身也经过DDR/HDMI，若不可读/停更/撕裂，不能拿最后一组数证明链路正常。
- 真正可读：以上面板、两FIFO sticky及armed、CRC参考。RTL内部live计数虽可仿真查看，未另提供导出通道。
- 本轮未实现：pre/post-AWB实际RGB导出、真实gain轨迹或冻结开关、整帧抓图、DDR写/读session/frame身份、丢帧精确统计、端到端延迟、完整物理MIPI/DDR验证。
- SEQ停滞可发现“看不到新诊断样本”，不能单凭SEQ跳变给出丢帧数；输出刷新/重复缓存帧与采集率不同。

## 约束覆盖专项结论与独立修复范围

本轮保持PLL、SDC、IP FIFO Tcl逐字节不改。w128_d512_fifo.tcl按min(clkw,clkr)-0.3ns设Gray source→sync_r1 max_delay；QUALITY归档的两组各18条实际被clock_groups覆盖，风险未消失。
新候选必须读取自己的exception报告复核，不因STA通过报告CDC已修复。
后续独立约束修复需要：定位实际实例/方向；核对Gray编码寄存与同步级；在安路工具支持下收窄跨域例外，避免将需要检查的Gray数据路径整体false-path，同时保留其他异步路径合理例外；确认max_delay实际执行而非Ignored，并检查每位延迟/总线偏斜、完整全设计STA和硬件长稳。
这可能涉及重构MIPI↔DDR clock_groups/精确端点例外，不能只追加同一条max_delay（仍可能被覆盖）。本轮没有验证过可直接采用的替代SDC，不把建议称为完成修复。

## 验证及构建

复现入口：`python -X utf8 tests/run_edge_stability_probe.py --full`、`python -X utf8 tests/probe_reference.py`。环境同既有requirements-edge-quality.txt。
独立软件图、金标准CRC/OSD字库像素、真实packer和isp_top边界注入；异常mon/FIFO单元；关闭probe的旧QUALITY/NMS旁路及按键/CDC/初始化/十进制回归。物理IP测试范围见最终VERIFICATION及归档。
完整TD结果、实际源commit、资源、WNS、warnings、bit SHA及归档路径以最终BUILD_INFO为准；本设计文档不预填待测数值。
