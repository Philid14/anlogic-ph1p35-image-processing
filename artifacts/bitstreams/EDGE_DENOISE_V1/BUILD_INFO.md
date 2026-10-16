# BUILD_INFO — EDGE_DENOISE_V1 candidate

| 项目 | 值 |
|---|---|
| Version / Role | EDGE_DENOISE_V1 / MAIN，TEAM_PROTOCOL_V1 |
| Base SHA | c42168e26026425660f2a6f51eec76b04c85eea0；原算法对照edge-control-v1-candidate |
| Git Branch | codex/main/edge-denoise-v1 |
| Git Commit SHA（实际构建源码/配置） | b78dd6b43730c69896bf99753c6b961c3f44a9ae |
| Git Tag（包含本归档的candidate提交） | edge-denoise-v1-candidate；git rev-parse edge-denoise-v1-candidate^{commit} 得到归档提交SHA；RTL/配置与构建提交相同 |
| Build Time | 2026-10-16，日志td_20261016_212319.log、td_20261016_212757.log；bit生成于2026-10-16 21:32:42，TD本地时间 |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty 6.2.168116 |
| 原始bit生成路径 | D:\anlogic_formal_project\in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit |
| 归档bit路径 | D:\anlogic_formal_project\artifacts\bitstreams\EDGE_DENOISE_V1\camera_to_dsi_display.bit |
| Bit SHA-256 / 大小 | 224D4BE2F53B807137E19D095DCF6132BAA9CFC023C3C59BCE17ABDE3332B84A / 1789539 bytes |
| Build Result | 完整Synthesis → Physical Design → Timing Check → bitgen完成，最终日志无ERROR，两个进程退出0 |
| LUT6 | 15163 / 21216（71.47%） |
| FF | 14667 / 42432（34.57%） |
| Slice | 16859 / 21216（79.46%） |
| RAM / ERAM | 39 ERAM20K / 108（36.11%）；分布式RAM/移位资源见phy.area |
| DSP | 9 / 40（22.50%） |
| Setup WNS / TNS / 违例端点 | +0.112ns / 0 / 0 |
| Hold WNS / TNS / 违例端点 | +0.020ns / 0 / 0 |
| 新的关键warning | 无新增关键类型，既有PHY-5060, PHY-5079保留；不是无warning |
| Board Test Status | **待用户上板**；未验证真实噪声收益或30分钟稳定性 |

## 修改范围与整数实现

唯一主要变量为EDGE分支新增Gaussian；DENOISE_ENABLE=1实际Top开启，=0编译恢复旧Sobel，两者均经过RTL逐拍验证。新增gaussian_pair_3x3.v；修改edge_detect_96前端与边界、edge_control_stream延迟适配、isp_top/Top参数和AL新增输入。194冻结主工程、68只读参考、3原理图保持SHA一致，全部59个实际TD输入与构建提交匹配（Git文本换行归一），旧归档bit全部与origin/main字节一致。

Sensor Exposure1990 half-lines、VTS1000、HTS1600、Gain1f/3f=15.75×、Digital Gain、BLC15、AWB_V2、demosaic、MIPI、DDR、HDMI、PLL、ADC/SDC、按键/CDC/OSD内容及位置均不变。ORIGIN仍取原AWB RGB，只增加4拍寄存对齐，状态区外逐字节保持。未实现AE/Gray/Binary/Median硬件或队友功能。

保持gray=floor(R/4)+floor(G/2)+floor(B/4)和像素对floor平均；每拍两个8bit采样。Gaussian完整[1,2,1;2,4,2;1,2,1]/16，六个10bit水平和、两个12bit纵向和，最终仅一次floor，输出8bit，无通用乘除法或DSP。Gaussian新增320×16bit×2=10240bit两历史行；Sobel原两行另10240bit，总4行20480bit（5×5依赖）。同步old-data读/写、下一拍复制已寄存历史，无行内降速或额外气泡。

Gaussian4拍+Sobel5拍=9拍；Original/config和valid/user/last同9拍；OSD2拍，真实96→128打包再1拍，总12拍，比旧版增加4个接收时钟周期。阈值8bit随Gaussian同延迟，再随Sobel到S4并零扩展14bit比较；模式/阈值仍在AWB提前SOF提交并随像素携带。K3切换，K4短按−10/长按约0.7s+10一次，10–250饱和，默认EDGE/080。

因果核中心约原(x−4,y−2)，首4行/首8原像素清黑；右/下不补额外像素。数组不复位，以SOF、行水平进位清理和边界屏蔽拒绝旧帧残留。总分辨率1280×720，每完整帧230400输入拍/172800个128bit DDR字。状态OSD在DDR前随帧缓存，旧DDR后安路Logo/CNT不变，不以此证明DDR整机没有撕裂或溢出。

## 资源对照（路由后）

| 版本 | LUT6 | FF | Slice | ERAM20K | DSP | Setup/Hold(ns) |
|---|---:|---:|---:|---:|---:|---|
| EDGE_CONTROL_V1 | 14724 | 14417 | 16473 | 39 | 9 | +0.100 / +0.020 |
| EDGE_DENOISE_V1 | 15163 | 14667 | 16859 | 39 | 9 | +0.112 / +0.020 |

增量：LUT6 +439、FF +250、Slice +386、ERAM +0、DSP +0。实现预算先于RTL保存，Median未综合，不编造准确资源。STA覆盖96.16%，约束与既有异步分组未改；零违例不代表所有物理异步行为受STA覆盖。

全设计DRAM LUT808（原552，+256），shifter LUT168（原160），F7MUX64（原32）。Gaussian层级路由logic LUT258/FF250/DRAM LUT256/F7MUX32/ERAM0/DSP0。新增两个RAM的SYN-5041说明block提示被AUTO覆盖，与旧Sobel同类型；无新增锁存/多驱动告警。最差setup仍在HDMI_PIXEL_CLK：u_hdmi_mixer/mult0_syn_59.clk→u_hdmi_mixer/O_hdmi_data_reg[10]_syn_2.imf，slack0.112ns，数据路径12.925ns；MIPI_RX_BYTE_CLK本域Setup WNS+4.366ns。关键路径摘录见worst_setup_path.txt。

## 模型、RTL和上板边界

研究先行提交a3796fe，合成13场景×3算法×13阈值=507行CSV；原Sobel70组整数模型等价比较。无真实摄像头RAW/RGB帧，不能声称真实图像降噪成功。Gaussian对合成随机/固定噪声有合理收益，但细线召回下降，椒盐不如Median；详情见docs/EDGE_DENOISE_RESEARCH.md。

联合RTL全通过：1764876有效拍/1323657打包字，含四完整720pGaussian/Origin帧、两种编译参数、提前/同拍SOF、坏行尾/截断恢复、阈值切换、颜色排列/OSD/实际ISP接线。独立Gaussian1282拍覆盖完整8bit输入。旧control完整旁路回归另1293320拍/969990字，含按键/CDC/无Sensor后续写入测试（I2C握手stub）。raw输出保留；fullcase旧打印标签4+recovery实际只有4帧，源码仅修正标签，不改变激励/比较/RTL。

证据build_evidence含综合/物理日志与8项核心报告、STA摘要、SOURCE_MANIFEST、旧bit指纹、最终检查和RTL原始输出。完整多MB逐路径时序报告留忽略的TD Runs。未模拟完整MIPI/AWB/DDR/HDMI PHY，没有实板寄存器读回或长稳测量。

按docs/EDGE_DENOISE_V1_BOARD_TEST.md用旧/新bit同机位/照明扫描阈值，比较雪花与真实轮廓/细线，测试遮挡/运动、至少20次切换及30分钟稳定性。任务分支/PR等Philid14审查，不自动合并，不移动旧tag或覆盖旧bit。候选完成即停止。
