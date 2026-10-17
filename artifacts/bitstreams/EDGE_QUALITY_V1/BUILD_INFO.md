# BUILD_INFO — EDGE_QUALITY_V1 candidate

| 项目 | 值 |
|---|---|
| Version / Role | EDGE_QUALITY_V1 / MAIN / TEAM_PROTOCOL_V1 |
| Git Branch | codex/main/edge-quality-v1 |
| Git Base / PR依赖 | 712fbb33cfc5ba8436b96306e1fe443553aa6591，edge-nms-v1-candidate；Draft PR base codex/main/edge-nms-v1，依赖未合并#4/#3 |
| Git Commit SHA（实际构建源码/配置） | 97858d51c7599a504a733b2302db797207c1ac0e |
| Git Tag（包含本bit的归档提交） | edge-quality-v1-candidate；git rev-parse edge-quality-v1-candidate^{commit} 唯一解析归档提交；RTL与构建提交一致 |
| Build Time | 日志td_20261017_223119.log、td_20261017_224134.log；bit生成于2026-10-17 22:46:26，TD本地时间 |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit路径 | D:\anlogic_formal_project\in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit |
| 归档bit路径 | D:\anlogic_formal_project\artifacts\bitstreams\EDGE_QUALITY_V1\camera_to_dsi_display.bit |
| Bit SHA-256 / 大小 | 629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5 / 1789539 bytes |
| Build Result | Synthesis → Physical Design → Timing Check → bitgen完整完成；最终日志无ERROR，两个进程退出0 |
| LUT6 | 16162/21216 (76.18%) |
| FF | 15423/42432 (36.35%) |
| Slice | 17894/21216 (84.34%) |
| RAM / ERAM20K | 47/108 (43.52%)；DRAM与四层实际映射见原始area |
| DSP | 9/40 (22.50%) |
| Setup WNS / TNS / 违例端点 | +0.009ns / 0 / 0 |
| Hold WNS / TNS / 违例端点 | +0.020ns / 0 / 0 |
| 新增关键warning | 无新增关键类型，既有PHY-5060, PHY-5079保留；不是无warning |
| Board Test Status | **待用户上板**；真实轮廓/杂边权衡和30分钟稳定性尚未验证 |

## 唯一变量与设计

正式Top QUALITY_ENABLE=1/QUALITY_HOPS=4，旧默认QUALITY_ENABLE=0恢复NMS。保留既有pair-gray/Gaussian/Sobel/NMS，仅把S5改为两位强弱分类，然后四级有界8邻接传播：weak=NMS保留且mag≥floor(TH/2)，A0=NMS保留且mag≥TH；A(k+1)=weak AND [Ak OR 8邻Ak]，最多4跳，不填零响应断口、不删除孤立强点、不等于完整Canny。

每跳三拍、两样本/拍；四拍成一存储字，row1 80×16bit、row2只存active为80×8bit，每跳1920bit，四跳逻辑7680bit，实际映射见area。Edge/Original/config25拍，OSD2+pack1共28拍，比NMS增加12接收周期。原图只增加等量寄存对齐、状态区外RGB逐字节不变；SOF提交帧配置，OSD仍在DDR前。中心约(x−14,y−7)，首14行/左28像素清黑，右/下不补点；完整帧230400拍/172800字。

Exposure1990 half-lines/VTS1000/HTS1600/Gain15.75×/DigitalGain/BLC15/AWB_V2/Gaussian/NMS、K3/K4/CDC/OSD/Logo/CNT、MIPI/DDR/HDMI/PLL/ADC/SDC冻结；195主工程+新增保护NMS文件、68参考、3原理图一致。61个实际TD输入与源码提交内容匹配（只归一Git文本换行）；13个NMS及以前旧bit和本轮R0检查点共14个bit字节相同，全部已有归档metadata/report未改。

## 路由资源对照

| 版本 | LUT6 | FF | Slice | ERAM20K | DSP | Setup/Hold(ns) |
|---|---:|---:|---:|---:|---:|---|
| EDGE_NMS_V1 |15206|15018|16598 (78.23%)|39|9|+0.101/+0.020|
| EDGE_QUALITY_V1 |16162|15423|17894 (84.34%)|47|9|+0.009/+0.020|

增量LUT6 +956、FF +405、Slice +1296、ERAM +8、DSP +0。这是全设计重映射/打包净值，不能当单模块成本；四层实际层级行及预算核对另见验证补录。STA覆盖96.11%，时钟/约束/异步分组未放宽，零违例不证明所有物理异步行为。

## 研究、验证与边界

研究提交46c8f18先于RTL；29合成场景×13方法×8门限3016项。没有本摄像头真实ORIGIN RGB，未把Edge拍屏当原图。四跳TH60合成平均召回67.28%→74.20%，平坦误检0.0043%→0.028%；TH40可能扩散噪声。不是全面占优或实板已改善。方向精化、孤点筛选收益不足未采用，8跳/完整传播资源代价较大；1280全采样留待真实帧收益验证。

实际分类241门限/2892采样、四层独立空间参考64/68/72/76/1280行宽共168500拍/1348000采样层检查、优化后RGB全链/OSD/实际打包/实际ISP完整720p通过。QUALITY关闭旧NMS全回归、按键/CDC/Sensor握手/decimal已在R0源码检查点通过；随后只改独立QUALITY缓存，旧默认路径完全相同，不把日志称为优化后重跑。初次分类测试夹具force表达式不持续更新而失败，改wire驱动后通过，未为此改算法RTL；原始失败输出保留。61f7ebe较宽地址回归主动中断后按最终源码统一重跑，日志明确保留。未模拟完整厂商MIPI/AWB/DDR/HDMI PHY，Sensor握手stub不能证明实板读回/ACK。

SOURCE_MANIFEST、旧bit指纹、FINAL_CHECKS、raw研究/RTL/控制结果、综合/物理全日志、完整final_timing.rpt、area/qor/ts/exception和实际settings均归档。设计/选择、验证/失败、上板步骤见docs/EDGE_QUALITY_*。按同机位/灯光/手机设置同时比较相同TH及相近轮廓完整度，20次切换/30分钟。等待Philid14最新提交审查及用户实板反馈，不自动合并或继续下一版。

## 最终TD结果补录（2026-10-17）

实际构建源码`97858d51c7599a504a733b2302db797207c1ac0e`，研究检查点46c8f18；最终综合日志td_20261017_223119.log，物理/最终时序/bitgen日志td_20261017_224134.log。两个进程退出0、无ERROR、无新增声明顺序警告。源码提交后只修改文档，不修改硬件输入。

| 路由后 | EDGE_NMS_V1 | EDGE_QUALITY_V1 | 增量 |
|---|---:|---:|---:|
| LUT6 |15206|16162|+956|
| FF |15018|15423|+405|
| Slice |16598 (78.23%)|17894 (84.34%)|+1296|
| ERAM20K |39|47|+8|
| DSP |9|9|+0|
| Setup WNS(ns) |+0.101|+0.009| |
| Hold WNS(ns) |+0.020|+0.020| |

全设计DRAM LUT 1256（旧1256，增量+0），shifter LUT 176（旧168），F7MUX 112（旧112）。四个连接层级合计逻辑LUT 232、ripple 0、FF 390、ERAM 8、DSP 0、DRAM LUT 0、shifter 0、F7MUX 0。完整层级行保留：

```text
|        g_quality$g_hop[0]$u_link                                |edge_link_pair_3x3                             |60        |0       |94      |2       |0       |0        |0           |0       |0       |0       |0       |
|        g_quality$g_hop[1]$u_link                                |edge_link_pair_3x3                             |59        |0       |103     |2       |0       |0        |0           |0       |0       |0       |0       |
|        g_quality$g_hop[2]$u_link                                |edge_link_pair_3x3                             |58        |0       |98      |2       |0       |0        |0           |0       |0       |0       |0       |
|        g_quality$g_hop[3]$u_link                                |edge_link_pair_3x3                             |55        |0       |95      |2       |0       |0        |0           |0       |0       |0       |0       |
```

R0完整两位标签数组10240bit、四层512 DRAM LUT；最终四拍打包、顶行只存active，逻辑容量7680bit、地址明确7位。实际RAM LUT必须按报告判断。R0路由LUT6 16888/FF15402/Slice18263(86.08%)，最终相对R0分别-726/+21/-369，四层DRAM变化-512。全设计增量还包括Original/配置12拍对齐及工具重映射，不能仅用四个模块的FF/LUT解释总增量。实现前预算保留在研究文档，不事后改成实测值。

最差Setup在HDMI_PIXEL_CLK，Begin `u_hdmi_mixer/mult0_syn_59.clk (rising edge triggered by clock HDMI_PIXEL_CLK  { rise@0.000000ns  fall@6.666000ns  period=13.333000 })`，End `u_hdmi_mixer/O_hdmi_data_reg[15]_syn_2.id (rising edge triggered by clock HDMI_PIXEL_CLK  { rise@0.000000ns  fall@6.666000ns  period=13.333000 })`，Data Path Delay 12.952ns (cell 5.592ns (43%), net 7.360ns (57%))。Setup/Hold TNS0、违例端点0，STA覆盖96.11%；完整final_timing.rpt已归档，可核对所有时钟域。SDC/PLL/异步分组保持。既有PHY-5060混合扇出、PHY-5079局部时钟路由、旧RAM_STYLE AUTO和厂商加密DDR latch warning仍保留，无新增关键类型，不声称零warning。

bit SHA256 `629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5`。全部61实际TD输入与实际源码提交匹配（仅Git文本换行归一）；13个NMS及以前旧bit和本轮R0共14个bit字节一致，全部历史BUILD_INFO/报告未改。SOURCE_MANIFEST、PREVIOUS_BITS_UNCHANGED、FINAL_CHECKS、实际settings、完整flow/STA及RTL原始输出随bit归档。R0时序通过但资源未达目标，bit/报告/tag完整保留；此前分类夹具失败及主动中断回归的原始输出明确标记并保留。用户Edge照片仅保存文件指纹/类型记录，不将其当RGB研究输入。

最终candidate仅等待人类审查和实板验收，实际连续性/噪声折中未确认。合成对照支持受限收益：TH60召回提高、误检也提高；TH40可能沿噪声扩散，不能只宣传优点。公平测试需同门限及相近完整度两种口径，并核对原图/按键/OSD/视频长稳。停止本轮，不自动扩展下一版本。

### 最终预算与时序裕量判断

最终相对NMS LUT6+956、FF+405、Slice+1296，满足实现前约1200/1800/1400增量预算及约85%Slice目标。ERAM增加8块（39→47/108），以空余块RAM换取Slice资源；7680bit是逻辑数据容量，不能用它掩盖实际占用8个ERAM20K块。剩余3322Slice、61ERAM块，不能保证未来任意算法都能放入。

Setup最差+0.009ns比NMS+0.101ns更紧，路径仍是冻结HDMI mixer；MIPI_RX_BYTE_CLK本域Setup+3.353ns。slow/fast setup/hold均检查通过、无端点违例，但不能把9ps余量描述为宽裕或把STA通过当作长期上板稳定。未为提高数字而修改冻结HDMI/PLL/SDC、降低视频规格或忽略违例。该限制列入候选审查和实板验收，先完成当前候选，不自行进入另一版HDMI优化。
