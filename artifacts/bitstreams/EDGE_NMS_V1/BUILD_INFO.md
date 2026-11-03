# BUILD_INFO — EDGE_NMS_V1 candidate

| 项目 | 值 |
|---|---|
| Version / Role | EDGE_NMS_V1 / MAIN，TEAM_PROTOCOL_V1 |
| Git Branch | codex/main/edge-nms-v1 |
| Git Base | 08ea909febf2dd0952e7221a0ce2bf34b24e3b44，edge-denoise-v1-candidate；PR依赖codex/main/edge-denoise-v1，PR #3未合并 |
| Git Commit SHA（实际构建源码/配置） | 8ae2fd6c38416095e1232783a0e63b2eb2d1e9f3 |
| Git Tag（包含本bit的归档提交） | edge-nms-v1-candidate；git rev-parse edge-nms-v1-candidate^{commit} 唯一恢复归档提交；RTL与构建提交一致 |
| Build Time | 日志td_20261016_232120.log、td_20261016_232756.log；bit生成于2026-10-16 23:34:38，TD本地时间 |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit路径 | D:\anlogic_formal_project\in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit |
| 归档bit路径 | D:\anlogic_formal_project\artifacts\bitstreams\EDGE_NMS_V1\camera_to_dsi_display.bit |
| Bit SHA-256 / 大小 | 734F5D97C429D086FBE8518514B8547CF0C2FBC485B44D35BD218F0F7FA2A448 / 1789539 bytes |
| Build Result | Synthesis → Physical Design → Timing Check → bitgen完整完成；最终日志无ERROR，两个进程退出0 |
| LUT6 | 15206/21216 (71.67%) |
| FF | 15018/42432 (35.39%) |
| Slice | 16598/21216 (78.23%) |
| RAM / ERAM20K | 39/108 (36.11%)；DRAM/移位资源与NMS层级见原始报告 |
| DSP | 9/40 (22.50%) |
| Setup WNS / TNS / 违例端点 | +0.101ns / 0 / 0 |
| Hold WNS / TNS / 违例端点 | +0.020ns / 0 / 0 |
| 新增关键warning | 无新增关键类型，既有PHY-5060, PHY-5079保留；其他warning见原始日志 |
| Board Test Status | **待用户上板**，不能声称真实夜间细化收益或30分钟稳定性已验证 |

## 唯一变量与冻结

本轮只加二值化前NMS：DENOISE_ENABLE=1/NMS_ENABLE=1；NMS_ENABLE=0完整回归恢复旧降噪。Sensor Exposure1990 half-lines、VTS1000、HTS1600、Gain1f/3f=15.75×、Digital Gain、BLC15、AWB_V2、Gaussian及舍入、demosaic/MIPI/DDR/HDMI/PLL/ADC/SDC、按键/CDC、OSD内容/位置与Logo/CNT均冻结。195主工程、68只读参考、3原理图SHA一致；全部60项实际TD输入与源码提交匹配（仅归一Git文本换行）；12个旧归档bit字节一致。

方向在S4与14bit幅值同拍由S3的13bit Gx/Gy形成：2|Gy|≤|Gx|为W/E，否则2|Gx|≤|Gy|为N/S，其余同号NE/SW、异号NW/SE（Gy正向上）。斜率边界1/2、2，与理想角度边界偏差4.065度。中心严格大于W/SW/N/NW侧且大于等于E/NE/S/SE侧；平台按确定性一侧选择，反号不改变轴。

NMS两样本/拍，N1捕获、N2旧数据行读、N3真实中心/方向邻居选择、N4抑制；原S5单阈值保留在后。row1 320×32bit含上一行方向/幅值，row2 320×28bit仅幅值，共19200bit（17920幅值+1280方向），AUTO推断，不能预设ERAM。无额外有效行气泡。调试端口仅仿真观察，正式Top不连接并可优化掉。

Edge/Original/config同13拍，OSD2+真实96/128打包1，总16拍，比旧版增加4个接收周期。配置仍在AWB提前SOF锁存并随每拍携带，旧帧不取新配置；tlast仍行尾并按打包补1拍。核中心约(x−6原像素,y−3行)，首6行/左12像素清黑，右/下不补额外样本。每完整帧230400输入拍/172800个128bit字。Original只做对齐，状态区外RGB不变；状态在DDR前随帧缓存。

## 路由资源对照

| 版本 | LUT6 | FF | Slice | ERAM20K | DSP | Setup/Hold(ns) |
|---|---:|---:|---:|---:|---:|---|
| EDGE_DENOISE_V1 | 15163 | 14667 | 16859 | 39 | 9 | +0.112 / +0.020 |
| EDGE_NMS_V1 | 15206 | 15018 | 16598 | 39 | 9 | +0.101 / +0.020 |

增量LUT6 +43、FF +351、Slice -261、ERAM +0、DSP +0；完整预算先于RTL保存在研究文档。STA覆盖96.37%；保留既有异步分组，零违例不等于所有异步物理行为都被STA证明。关键路径、RAM映射及warning解释见验证补录与原始报告。

## 软件、RTL与上板边界

研究提交7620c16先于RTL，19梯度场/133二值输出复现旧整数模型，四算法×19场景×6阈值共456项合成对照。无真实ORIGIN RGB输入；手机拍Edge照片不是原输入，采集操作说明在研究文档。NMS细化阶跃/模糊边，真实纹理仍多；软件完整8邻接滞后和一跳近似不同（弱链27点vs2点），两者都不在本bit。

新RTL独立检查Gx/Gy、幅值、方向及NMS中心/两邻居/keep，再比最终RGB/OSD/打包和实际ISP。原始full输出保留，含四完整720p帧、旁路、阈值/模式边界、高频请求、坏行尾与截断恢复；另有旧降噪完整回归和按键/CDC/Sensor/decimal单元。I2C握手stub不代表实板寄存器读回，未模拟厂商MIPI/AWB/DDR/HDMI PHY。

正式构建60项源码清单、旧bit完整性、RTL原始输出、综合/物理日志和8项核心报告、STA摘要在build_evidence。完整多MB逐路径报告留忽略的TD Runs。详细数据流见docs/EDGE_NMS_V1_DESIGN.md，验证与失败记录见docs/EDGE_NMS_V1_VERIFICATION.md。

使用docs/EDGE_NMS_V1_BOARD_TEST.md同场景比较旧/新bit的020/040/060/080，重点轮廓厚度与断裂、双边、真实织物纹理、斜线和最小2像素复制宽；至少20次切换及30分钟稳定性。本候选已在任务分支集成和构建，未合并main/PR #3，等待Philid14对最新提交审查和用户上板，不自动进入双阈值硬件。

## 最终TD构建补录（2026-10-16）

实际源码/配置提交 `8ae2fd6c38416095e1232783a0e63b2eb2d1e9f3`，研究提交7620c16、完整RTL测试检查点5e4c3d9和声明清理后small回归的证据均保留。最终综合日志td_20261016_232120.log，完整物理/时序/bitgen日志td_20261016_232756.log，最终两进程退出0、无ERROR、无HDL-5373。

| 路由后 | EDGE_DENOISE_V1 | EDGE_NMS_V1 | 增量 |
|---|---:|---:|---:|
| LUT6 |15163|15206|+43|
| FF |14667|15018|+351|
| Slice |16859 (79.46%)|16598 (78.23%)|-261|
| ERAM20K |39|39|+0|
| DSP |9|9|+0|
| Setup WNS(ns) |+0.112|+0.101| |
| Hold WNS(ns) |+0.020|+0.020| |

全设计DRAM LUT 1256（旧808，增量+448），shifter LUT 168（旧168），F7MUX 112（旧64）。实际NMS层级行（顺序logic LUT/ripple/seq/ERAM/DSP/DRAM/shifter/F7MUX等，详见area表头）：

```text
|        g_nms$u_nms                                              |nms_gradient_pair_3x3                          |283       |0       |325     |0       |0       |448      |0           |48      |0       |0       |0       |
```

两行逻辑容量19200bit保留14bit幅值和中心2bit方向；实际AUTO映射以该层级行及报告为准，不把逻辑bit数直接当ERAM数量。新RAM无强制block提示；既有Gaussian/Sobel/FIFO的SYN-5041仍在，未通过修改其RTL消除。关键warning类型仍为PHY-5060/PHY-5079，无新增关键类型；不是无warning。Setup/Hold TNS与违例端点均0；STA覆盖96.37%，未放宽SDC、PLL或异步分组。

归档bit SHA256 `734F5D97C429D086FBE8518514B8547CF0C2FBC485B44D35BD218F0F7FA2A448`；全部60个实际TD源码/IP/约束输入与构建提交内容匹配（只归一Git文本换行），195冻结主工程/68参考/3原理图一致；12个旧归档bit与基线08ea909逐字节相同。SOURCE_MANIFEST、PREVIOUS_BITS_UNCHANGED、FINAL_CHECKS、完整flow日志、核心area/qor/ts/exception及测试原始输出随bit归档。完整逐路径报告在忽略的Runs，摘要和关键路径另存build_evidence。

本轮没有功能性RTL失败或失败bit；首轮仅综合完成并发现3条声明顺序warning，无物理构建/bit。清理后重新完整构建，首轮日志/area保留。candidate尚未真实上板：MIPI采集、连续HDMI、细化收益、20次切换和30分钟稳定性均不能用离线仿真替代。完成candidate后停止，等待人类审查与实板反馈。

### 路径、预算与warning说明

最差setup仍在HDMI_PIXEL_CLK：u_hdmi_mixer/mult0_syn_59.clk → u_hdmi_mixer/O_hdmi_data_reg[17]_syn_2.ib，数据路径12.838ns、slack+0.101ns；MIPI_RX_BYTE_CLK本域Setup WNS+4.154ns。约束/时钟均未修改。PHY-5060涉及既有I2C scl_clk和O_cam_24m混合扇出，PHY-5079涉及既有局部时钟路由；DDR加密厂商IP中既有HDL-5369 latch warning与基线同位置，未引入NMS锁存或多驱动告警。

最终Slice78.23%低于约85%目标；全设计LUT6+43、FF+351、Slice−261是本次完整工具重映射/打包后的净变化，不代表NMS本身不花资源或占负资源。新增NMS层级实际283逻辑LUT、325FF、448 DRAM LUT、48F7MUX、0ERAM/0DSP；含方向量化、对齐及其他全设计映射变化后的净值须与该局部成本分开解释。Gaussian源码冻结但工具层级映射可变化，未为满足预算修改冻结模块。
