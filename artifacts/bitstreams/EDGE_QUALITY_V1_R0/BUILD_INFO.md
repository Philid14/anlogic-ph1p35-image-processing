# BUILD_INFO — EDGE_QUALITY_V1_R0 工程检查点（未选为上板candidate）

| 项目 | 值 |
|---|---|
| Version / Role | EDGE_QUALITY_V1_R0 / MAIN / TEAM_PROTOCOL_V1 |
| Git Branch | codex/main/edge-quality-v1 |
| Git Base / PR依赖 | 712fbb33cfc5ba8436b96306e1fe443553aa6591，edge-nms-v1-candidate；Draft PR base codex/main/edge-nms-v1，依赖未合并#4/#3 |
| Git Commit SHA（实际构建源码/配置） | acf7d444f19ae0dbb8a36a854edc7627f7f8b2ec |
| Git Tag（包含本bit的归档提交） | edge-quality-v1-r0-build；git rev-parse edge-quality-v1-r0-build^{commit} 唯一解析归档提交；RTL与构建提交一致 |
| Build Time | 日志td_20261017_220454.log、td_20261017_220918.log；bit生成于2026-10-17 22:14:41，TD本地时间 |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit路径 | D:\anlogic_formal_project\in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit |
| 归档bit路径 | D:\anlogic_formal_project\artifacts\bitstreams\EDGE_QUALITY_V1_R0\camera_to_dsi_display.bit |
| Bit SHA-256 / 大小 | 27FDB0B07DD1AE9196164D209DA54CF48E3867BD6F9357549AEE3100ECD0126B / 1789539 bytes |
| Build Result | Synthesis → Physical Design → Timing Check → bitgen完整完成；最终日志无ERROR，两个进程退出0 |
| LUT6 | 16888/21216 (79.60%) |
| FF | 15402/42432 (36.30%) |
| Slice | 18263/21216 (86.08%) |
| RAM / ERAM20K | 39/108 (36.11%)；DRAM与四层实际映射见原始area |
| DSP | 9/40 (22.50%) |
| Setup WNS / TNS / 违例端点 | +0.102ns / 0 / 0 |
| Hold WNS / TNS / 违例端点 | +0.020ns / 0 / 0 |
| 新增关键warning | 无新增关键类型，既有PHY-5060, PHY-5079保留；不是无warning |
| Board Test Status | **未上板，不推荐烧录**；时序通过但资源超出本轮目标，保存用于追溯，继续等价缓存优化 |

## 唯一变量与设计

正式Top QUALITY_ENABLE=1/QUALITY_HOPS=4，旧默认QUALITY_ENABLE=0恢复NMS。保留既有pair-gray/Gaussian/Sobel/NMS，仅把S5改为两位强弱分类，然后四级有界8邻接传播：weak=NMS保留且mag≥floor(TH/2)，A0=NMS保留且mag≥TH；A(k+1)=weak AND [Ak OR 8邻Ak]，最多4跳，不填零响应断口、不删除孤立强点、不等于完整Canny。

每跳三拍、两样本/拍；每跳两行320×4bit×2=2560bit，四跳逻辑10240bit，实际映射见area。Edge/Original/config25拍，OSD2+pack1共28拍，比NMS增加12接收周期。原图只增加等量寄存对齐、状态区外RGB逐字节不变；SOF提交帧配置，OSD仍在DDR前。中心约(x−14,y−7)，首14行/左28像素清黑，右/下不补点；完整帧230400拍/172800字。

Exposure1990 half-lines/VTS1000/HTS1600/Gain15.75×/DigitalGain/BLC15/AWB_V2/Gaussian/NMS、K3/K4/CDC/OSD/Logo/CNT、MIPI/DDR/HDMI/PLL/ADC/SDC冻结；195主工程+新增保护NMS文件、68参考、3原理图一致。61个实际TD输入与源码提交内容匹配（只归一Git文本换行）；全部13旧bit与基线逐字节相同，旧归档metadata/report未改。

## 路由资源对照

| 版本 | LUT6 | FF | Slice | ERAM20K | DSP | Setup/Hold(ns) |
|---|---:|---:|---:|---:|---:|---|
| EDGE_NMS_V1 |15206|15018|16598 (78.23%)|39|9|+0.101/+0.020|
| EDGE_QUALITY_V1_R0 |16888|15402|18263 (86.08%)|39|9|+0.102/+0.020|

增量LUT6 +1682、FF +384、Slice +1665、ERAM +0、DSP +0。这是全设计重映射/打包净值，不能当单模块成本；四层实际层级行及预算核对另见验证补录。STA覆盖96.21%，时钟/约束/异步分组未放宽，零违例不证明所有物理异步行为。

## 研究、验证与边界

研究提交46c8f18先于RTL；29合成场景×13方法×8门限3016项。没有本摄像头真实ORIGIN RGB，未把Edge拍屏当原图。四跳TH60合成平均召回67.28%→74.20%，平坦误检0.0043%→0.028%；TH40可能扩散噪声。不是全面占优或实板已改善。方向精化、孤点筛选收益不足未采用，8跳/完整传播资源代价较大；1280全采样留待真实帧收益验证。

实际分类241门限/2892采样、四层独立空间参考6916拍/55328采样层检查、RGB全链/OSD/实际打包/实际ISP完整720p、QUALITY关闭旧NMS全回归、按键/CDC/Sensor握手/decimal回归通过。初次分类测试夹具force表达式不持续更新而失败，改wire驱动后通过，未为此改算法RTL；原始失败输出保留。未模拟完整厂商MIPI/AWB/DDR/HDMI PHY，Sensor握手stub不能证明实板读回/ACK。

SOURCE_MANIFEST、旧bit指纹、FINAL_CHECKS、raw研究/RTL/控制结果、综合/物理全日志、完整final_timing.rpt、area/qor/ts/exception和实际settings均归档。设计/选择、验证/失败、上板步骤见docs/EDGE_QUALITY_*。按同机位/灯光/手机设置同时比较相同TH及相近轮廓完整度，20次切换/30分钟。等待Philid14最新提交审查及用户实板反馈，不自动合并或继续下一版。

## R0 资源未达目标与保留决定

首轮完整构建时序通过，但Slice18263/21216=86.08%，较NMS16598增加1665（+7.85个百分点），超过研究前约85%/增量1400Slice目标；LUT6+1682也高于预估1200。四层窄行缓存实际512 DRAM LUT，高于估算256。该bit只是工程检查点，不作为最终candidate，不推荐上板比较，Board Test未进行。

后续仅将相邻两拍标签合并为8bit存储字，将行RAM深度320→160，保持每拍两采样吞吐、三拍/跳、四跳算法与对外时序完全相同；通过同步旧数据读和成对写入减少窄RAM映射开销。需要重新RTL验证和完整TD，不把R0资源当优化后结果。本bit/报告/tag保留，不移动tag、不覆盖文件。
