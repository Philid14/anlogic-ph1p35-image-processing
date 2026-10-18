# BUILD_INFO — EDGE_TEMPORAL_RESEARCH_V1

| 项目 | 值 |
|---|---|
| Version / Role | EDGE_TEMPORAL_RESEARCH_V1 / MAIN；独立真实RGB采样诊断，不是时间滤波优化版本 |
| Branch | codex/main/edge-temporal-research-v1 |
| 实际构建源码Git Commit | 84299d42fb88842b837794bdf43b61a88f1e2049 |
| Git Tag（包含bit的归档提交） | edge-temporal-research-v1-candidate；git rev-parse tag^{commit}解析归档SHA |
| 基线 / PR依赖 | 7343cfe PROBE / QUALITY b64daf3；Draft base codex/main/edge-stability-probe-v1，依赖#8/#7/#6/#4/#3，不自动合并 |
| Build Time | 2026-10-18T17:00:46.831523+08:00 |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit路径 | D:\anlogic_formal_project\in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit |
| Bit Path | artifacts/bitstreams/EDGE_TEMPORAL_RESEARCH_V1/camera_to_dsi_display.bit |
| SHA-256 / bytes | 5D01156E08E69DDAA51AB41A3E3C2DFB1BC8B60436E97FBAE6555754AE6EB27D / 1789539 |
| Build Result | Synthesis → Physical Design → final Timing Check → bitgen全部完成；PASS |
| LUT6 | 17431 / 21216 (82.16%) |
| FF | 17913 / 42432 (42.22%) |
| Slice | 18267 / 21216 (86.10%) |
| RAM / ERAM20K | 88 / 108 |
| DSP | 11 / 40 |
| Setup WNS / TNS / 违例端点 | +0.019ns / 0ps / 0 |
| Hold WNS / TNS / 违例端点 | +0.020ns / 0ps / 0 |
| STA coverage | 95.84% |
| Critical warnings | ['PHY-5060', 'PHY-5079']；新增类型[]；原始上下文随附 |
| Board Test Status | 待用户上板及手机录像；本机没有采集到真实ROI数据，不冒称板测通过 |

## 诊断与冻结

Edge恢复真实AWB后RGB，原Gaussian/Sobel/NMS/四跳及Original/K3/K4/旧状态OSD/Logo/CNT不变；AWB仅加只读、对齐到乘法输出的原RGB/实际增益/上次完整统计端口，没有冻结或改动正式增益。Sensor Exposure1990 half-lines/VTS1000/HTS1600/Gain15.75×/BLC15、PLL/SDC、MIPI/DDR/HDMI传输不变。
600个SOF后冻结中心X576..703/Y344..375的8个连续采集帧，RGB888不降精度；实际R/B Q16增益、统计、两侧CRC、行帧/打包数量、FIFO历史状态、32bit MIPI周期时间戳随数据输出。采样与页缓存均现有MIPI时钟，不加视频反压或像素级延迟，总25+2+1=28拍。
通过101页带header/payload CRC的黑白8像素单元画面导出，不是假设已有UART/ILA。页面每60个采集SOF切换、循环，手机录像后离线无损解码；未验证真实手机可解码性。面板覆盖是诊断用途，旧固定PROBE面板在导出时隐藏，原状态/Logo/CNT仍保留。

## 验证、追溯与风险

65项TD实际输入与源码提交一致，构建前17份bit哈希不变。独立捕获/完整720p/实际ISP边界/按拍OSD、与旧AWB全输出并行对照、光学失真/负例、旧QUALITY/PROBE/按键/CDC/Sensor回归结果见docs/edge_temporal_evidence及研究报告。
本版本使用真实RGB路径，不能套用固定PROBE的资源节省。相对QUALITY净增LUT +1269、FF +2490、Slice +373、ERAM +41、DSP +2，其中包含采样诊断，不代表正式滤波器开销。
CRC可拒绝错误但不是纠错码；模糊/反光/滚动快门可导致缺页，只重录同一冻结burst补页，不拼接不同重置。ROI保留7内部横采样/7行halo后仅50×18点可用于完整四跳比较，8帧较短，需要多场景重复burst。AWB后图由真实pre RGB与实际gain位准确重建，并由实际post CRC校验，不声称采到Bayer RAW或完整全帧。
统计seq与采集seq独立，时间戳不是TEAM同帧端到端延迟接口。FIFO历史sticky已置位后无法数重复事件；数量异常、未armed、ROI内gain变化、CRC或新sticky变化必须先排查，不做算法排名。既有Gray max_delay覆盖风险未修复，实际Ignored见归档；STA通过不证明长期硬件稳定。
回滚重新PROGRAM_SRAM烧录EDGE_QUALITY_V1，SHA629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5；固定源对照使用EDGE_STABILITY_PROBE_V1，SHA7A78AFBC6126CDA8860E70241DA7AA934C68B0C98D1DB02E7FD2F7790A061980。
