# BUILD_INFO — EDGE_MULTI_MODE_V1_R0

| 项目 | 实际值 |
|---|---|
| Version / Role | EDGE_MULTI_MODE_V1_R0 / MAIN |
| Branch | codex/main/edge-multi-mode-v1 |
| 实际TD输入源码commit | 0f36d0957c5c45d9e607573d7143ed6cdfd91fe2 |
| Git Tag | edge-multi-mode-v1-r0-build |
| 基线 / PR | EDGE_TEMPORAL_V1 b47105f；Draft PR 以 codex/main/edge-temporal-v1 为 base，不自动合并 |
| Build Time | 2026-10-18T23:33:38.969563+08:00 |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit | D:\anlogic_formal_project\in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit |
| 归档bit | artifacts/bitstreams/EDGE_MULTI_MODE_V1_R0/camera_to_dsi_display.bit |
| SHA-256 / bytes | 7D176CC317914C73872DB90D70B8892FB049192703E194805CD288353E52054F / 1789539 |
| Build Result | Synthesis → Physical Design → final Timing Check → bitgen；PASS |
| Release Decision | REJECTED: setup margin +0.002ns is insufficient for release; new gray LUT usage to be optimized and rebuilt |
| LUT6 | 17040 / 21216 |
| FF | 15801 / 42432 |
| Slice | 18483 / 21216 (87.12%) |
| ERAM20K / DSP | 75 / 108；9 / 40 |
| Setup WNS / Hold WNS | +0.002ns / +0.020ns |
| Setup TNS / Hold TNS | 0ps / 0ps |
| STA coverage | 96.22% |
| Critical warnings | ['PHY-5060', 'PHY-5079']；新增类型[]，原始上下文随附 |
| Board Test Status | REJECTED; not for board testing |

## 数据与配置

配置为18位`{mode[1:0],edge_threshold[7:0],binary_threshold[7:0]}`，复位`EDGE/080/130`。K3按`EDGE→ORIGIN→GRAY→BINARY→EDGE`循环；K4短按−10、长按+10，只修改当前模式阈值，10..250饱和。24 MHz源域与MIPI接收域继续使用整包保持+toggle/ack邮箱，不逐位跨域。

四个分支均从AWB后RGB888出发，使用同一27拍对齐窗口；Edge Gaussian/Sobel/NMS/四跳/单帧时间保持始终运行。ORIGIN保持原RGB，GRAY/BINARY按`Y=(77R+150G+29B+128)>>8`逐像素生成，末端选择后才进入原2拍OSD和1拍96→128打包。无新增整帧缓存、反压、中心偏移或DDR/HDMI结构变化。

## 验证与风险

逐像素模型覆盖黑/白/中性灰/红/绿/蓝、RGB随机值、T=10/130/250及Y=T边界；K3/K4与18位CDC原子包测试通过。混合9帧小尺寸流覆盖四模式、提前/同拍SOF、valid间隙、帧内请求变化和帧首/行尾；完整720p×2帧完成460800有效拍、345600打包字逐字节对照。与EDGE_TEMPORAL_V1相比，18个算法/ISP/DDR/HDMI/Logo/引脚/SDC文件SHA保持不变。

STA通过不等于长期硬件稳定；既有FIFO Gray指针覆盖缺口和PHY关键warning风险未修复。任何S计数增长均应阻断正式验收并先检查FIFO/DDR。实板四模式画质、模式/阈值一致性、30分钟与光照变化尚无证据。

回滚：烧录`artifacts/bitstreams/EDGE_TEMPORAL_V1/camera_to_dsi_display.bit`，SHA-256 `14A36D98BC0A1547F84588087D796C14098AD4441CB30B5878D8F81CBADC95C4`。
