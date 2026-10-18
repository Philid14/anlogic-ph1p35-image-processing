# BUILD_INFO — EDGE_STABILITY_PROBE_V1

| 项目 | 值 |
|---|---|
| Version / Role / Branch | EDGE_STABILITY_PROBE_V1 / MAIN / codex/main/edge-stability-probe-v1 |
| Git Commit SHA（实际构建源码/配置） | 131afb0a745c62f119e1ae2f869788f45944f4a2 |
| Git Tag（归档commit） | edge-stability-probe-v1-candidate；通过git rev-parse tag^{commit}唯一恢复包含bit的提交 |
| 基线 / PR依赖 | 8b3b985诊断 / b64daf3 QUALITY；Draft base codex/main/edge-stability-diag-v1，依赖#7/#6/#4/#3，未合并 |
| Build Time | 2026-10-18T12:15:26.948789+08:00；日志td_20261018_120716.log / td_20261018_121137.log |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit路径 | D:\anlogic_formal_project\in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit |
| 归档bit路径 | D:\anlogic_formal_project\artifacts\bitstreams\EDGE_STABILITY_PROBE_V1\camera_to_dsi_display.bit |
| Bit SHA-256 / 大小 | 7A78AFBC6126CDA8860E70241DA7AA934C68B0C98D1DB02E7FD2F7790A061980 / 1789539 bytes |
| Build Result | Synthesis → Physical Design → final Timing Check → bitgen全部完成；时序判定PASS |
| LUT6 | 15415 / 21216 (72.66%) |
| FF | 16334 / 42432 (38.49%) |
| Slice | 16872 / 21216 (79.52%) |
| RAM / ERAM20K | 47 / 108 |
| DSP | 9 / 40 |
| Setup WNS / TNS / 违例端点 | +0.102ns / 0ps / 0 |
| Hold WNS / TNS / 违例端点 | +0.020ns / 0ps / 0 |
| STA coverage | 95.98%；Routed最终报告 |
| Critical warnings | PHY-5060, PHY-5079；新增类型[]，原始上下文见CRITICAL_WARNINGS.txt；不等于无warning |
| Board Test Status | 待用户PROGRAM_SRAM、拍照反馈；未在本机烧录或量到实板数值 |

## 唯一实验目的与冻结

只增加固定EDGE RGB源和旁路观察诊断。ORIGIN仍为真实摄像头RGB，AWB后的真实valid/提前SOF/tlast原样保留。
Sensor初始化/Exposure1990 half-lines/VTS1000/HTS1600/Gain15.75×/BLC15/AWB_V2、Gaussian/Sobel/NMS/四跳、K3/K4/CDC、原状态OSD/安路Logo/CNT、MIPI/DDR/HDMI正式数据处理、PLL/SDC均冻结。
增加FIFO事件只读输出、两级独立单调旗标CDC、DDR前诊断面板；不修打包器、不修Gray约束、不开发时间滤波。63项实际入口与构建提交一致，构建前16份bit和既有归档不变。

## 实际可观察与局限

诊断面板显示历史SEQ、IN/PACK、算法二值CRC、行数/最后行拍数、SOF间隔/气泡、行/非对齐段错误、累计坏帧/CRC变化、sticky事件/首气泡位置及FIFO armed/样本valid。
无完整测量为W；两FIFO未armed为未测；面板数值十六进制。CRC在OSD前只覆盖两个独立二值采样位，可能碰撞/漏掉复制RGB位错误，不替代完整DDR读回或精确帧身份。
TH80参考CRC6B6DB7D0，TH60=2B018224，TH40=417312EE。软件参考不是板测值。
Edge/Original25拍、OSD2、pack1，总28拍不变；正常每帧230400拍/172800字。

## 验证与风险

新完整RTL6帧720p为1382400有效拍/1036800字；256×160六帧61440拍/46080字；独立异常监测/FIFO事件与关闭probe旧路径/按键/CDC/Sensor/decimal回归通过。实际厂商PHY和真实Sensor控制未模拟；源域观察和CRC不证明物理CDC长期可靠。
首次CLI反斜杠路径在真正综合前失败，守卫拒绝并保留；其后完整重跑。监测单元phase期望修正等记录见VERIFICATION。
当前全设计净增量：LUT6 -747、FF +911、Slice -1022、ERAM +0、DSP +0。全设计重映射值，单模块见area层级。
时序结果不证明实板无抖动；Gray约束覆盖仍需看本轮exception/ignored报告，未通过放宽SDC消除违例。
操作、位定义、判读和回滚见docs/EDGE_STABILITY_PROBE_V1_*。旧QUALITY bit SHA629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5。
等待人类Philid14审查最新归档提交和上板反馈，不自动合并或继续下一版本。
