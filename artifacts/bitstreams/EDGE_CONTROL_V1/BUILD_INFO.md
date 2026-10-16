# BUILD_INFO — EDGE_CONTROL_V1 candidate

| 项目 | 值 |
|---|---|
| Version / Git Branch | `EDGE_CONTROL_V1` / `main` |
| Git Commit SHA（实际构建源码/配置） | `dff499a75cf0a348aaf2167548b4fe34bf4a78a9` |
| Git Tag（归档candidate提交） | `edge-control-v1-candidate`；`git rev-parse edge-control-v1-candidate^{commit}` 得到包含本bit/报告的唯一提交SHA；RTL/配置与上列构建提交一致 |
| Build Time | 2026-10-10，Synthesis 23:00:26–23:04:16；Physical/Timing/bitgen 23:05:00–23:09:25，TD本地时间 |
| Device / Top / TD | `PH1P35MDG324` / `design_top_wrapper` / Tang Dynasty 6.2.168116 |
| 原始bit生成路径 | `D:\anlogic_formal_project\in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit` |
| 归档bit路径 | `D:\anlogic_formal_project\artifacts\bitstreams\EDGE_CONTROL_V1\camera_to_dsi_display.bit` |
| Bit SHA-256 / 大小 | `05E05B153800E38982D7D1C2981A347B3616EAFA6EABA91A43443468FAF5DCF6` / 1,789,539 bytes |
| Build Result | 完整Synthesis → Physical Design → Timing Check → bitgen完成；最终日志无ERROR，两个进程退出0 |
| LUT6 | 14,724 / 21,216（69.40%） |
| FF | 14,417 / 42,432（33.98%） |
| Slice | 16,473 / 21,216（77.64%） |
| RAM / ERAM | 39 ERAM20K / 108（36.11%）；全设计DRAM LUT552、shifter LUT160 |
| DSP | 9 / 40（22.50%） |
| Setup WNS / TNS / 违例端点 | +0.100 ns / 0.000 ns / 0 |
| Hold WNS / TNS / 违例端点 | +0.020 ns / 0.000 ns / 0 |
| 新的关键warning | 无新增关键类型；既有PHY-5060与PHY-5079保留，未宣称无warning |
| Board Test Status | **用户2026-10-16已上板观察**：ORIGIN彩色正常、亮度基本满意；EDGE弱光降阈值增加真实轮廓及雪花，增加照明减轻雪花，部分遮挡噪点有位置稳定性但波动，全遮光几乎全黑。未提供完整20次切换或30分钟长稳记录，不补造量化噪声/寄存器读回。原candidate tag不移动。 |

## 控制、冻结与实现

用户允许修改旧未使用的按键输入。用户原理图第3/8文件确认K3=KEY2/B9→I_button[0]，K4=KEY3/C7→I_button[1]，3.3V上拉、低有效；N2/J14是扩展GPIO。K3一次消抖按下切换一次；K4短按释放−10，长按约0.7秒+10一次且释放不减；10–250饱和，默认EDGE/080。两级输入同步，480000周期消抖/16800000周期长按，按24MHz名义约20ms/0.7s；冻结STA时钟为23.810MHz（约20.16ms/0.706s），未修改PLL或SDC。

解除Top的ae_set实例，S_ae_req固定0，S_ae固定1990，S_ag固定未使用值0，不可由按键触发曝光/增益写入。初始化表及其控制保持原样：Exposure1990 half-lines、VTS1000、HTS1600、Gain1f/3f=15.75×、Digital Gain、BLC15、AWB_V2全部参数、demosaic、MIPI、DDR配置、HDMI、PLL/SDC冻结。pin.adc只修改两键为纯INPUT/B9/C7并移除这两项无效DRIVESTRENGTH。

9bit请求{mode,threshold[7:0]}经过保持数据的req/ack邮箱，在AWB提前tuser锁存；边界同拍尚未到达的CDC配置顺延下一帧。配置随每拍流水，旧帧余拍不会取新配置。Sobel连续运行；阈值8bit随梯度到S4并零扩展为14bit比较，梯度不截断。Original RGB/valid/user/last与Edge各5级对齐；新增状态OSD再2级，真实96/128打包再1级，行尾补偿匹配打包。保持1280×720每帧172800个128bit字，提前SOF间距不变。

状态文字在DDR前变为本帧像素，不独立把未同步状态交给HDMI；DDR延迟/重复帧时文字随该帧。复用冻结16×16字库，2倍字体，X800、Y16/56，显示MODE及三位十进制THRESHOLD。原DDR后安路Logo/CNT保持，不重叠。Original原像素排列保持；Sobel仍640点采样/成对复制，前两行/首4像素清黑，核中心约(x−2,y−1)的既有偏移保留。

## 路由资源对照

| 版本 | LUT6 | FF | Slice | ERAM20K | DSP | Setup/Hold WNS(ns) |
|---|---:|---:|---:|---:|---:|---|
| GAIN_TEST_E | 13757 | 13625 | 15652 | 40 | 9 | 0.000 / +0.020 |
| EDGE_V1 | 14174 | 13656 | 16031 | 34 | 9 | +0.107 / +0.020 |
| EDGE_CONTROL_V1 | 14724 | 14417 | 16473 | 39 | 9 | +0.100 / +0.020 |

相对固定EDGE增加550 LUT6、761 FF、442 Slice、5 ERAM，DSP不变。工具恢复彩色数据通路/FIFO并重新优化，不能把总资源差简单全归因于按键模块。最差setup仍在HDMI_PIXEL_CLK；MIPI_RX_BYTE_CLK本域Setup WNS+2.402ns。STA覆盖96.14%，既有异步时钟分组及IP约束未改；不能将零违例解释成覆盖全部异步物理行为。

## 验证证据与失败记录

完整RTL检查点A–D通过：1293320有效96bit拍、969990打包字，含四完整720p帧；按键抖动/单事件/短长互斥/饱和，200快速CDC请求逐包原子性和顺序，50组按键序列后无Sensor写入（真实初始化表116次写入、I2C握手stub），0–255三位十进制、早SOF/同拍SOF、帧内请求/连续切换/截断帧恢复、逐像素Sobel/Original/字体及真实isp_top/打包器。详见docs/EDGE_CONTROL_V1_VERIFICATION.md。

190冻结主工程、68只读参考、3原理图指纹一致；全部58项实际TD输入与构建提交一致并记录SOURCE_MANIFEST。原始综合/物理日志与八项核心报告、最终时序摘要、RTL输出、额外CDC/冻结检查、模型字体预览均在build_evidence。完整多MB逐路径报告留TD Runs。

首轮22:57:22的read_adc失败（USR-8409，纯INPUT不支持DRIVESTRENGTH），未完成综合且未归档旧bit；修正后重新完整构建。本归档保留FAILED_read_adc日志供追溯。综合basic阶段负WNS并非最终路由结果；最终已修复到上述正WNS。

未模拟完整MIPI/AWB/DDR/HDMI PHY；Sensor验证只模拟I2C握手，不是实板寄存器读回。按用户原理图定义K3/K4，实际板丝印/版本仍需上板确认。现有DDR整体撕裂/溢出、Logo与HDMI长期稳定性等待实测；参考预览不是实拍。按docs/EDGE_CONTROL_V1_BOARD_TEST.md使用PROGRAM_SRAM，20次模式切换、固定场景80/60/40/20及100/120/160、弱光噪声与30分钟检查。候选完成即停止，等待反馈。
