# BUILD_INFO — EDGE_TEMPORAL_V1_R0

| 项目 | 实际值 |
|---|---|
| Version / Role | EDGE_TEMPORAL_V1_R0 / MAIN |
| Branch | codex/main/edge-temporal-v1 |
| 实际TD输入源码commit | ab9081f906739090f431ae8f0dc7ede9e682eb64 |
| PHY恢复脚本commit | 95b4afce4baa1df376bc174c0f6a1a0ca029d8aa；仅修正面积行匹配，64项TD输入逐字节匹配原综合，无重新综合 |
| Git Tag | not issued；解析tag^{commit}恢复包含bit的归档提交 |
| 基线 / PR | QUALITY b64daf39af09980621adb1138df1674a8501ea09；Draft #10→#6→#4→#3，均不自动合并 |
| Build Time | 2026-10-18T22:08:14.705603+08:00 |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit | D:\anlogic_formal_project\in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit |
| 归档bit | artifacts/bitstreams/EDGE_TEMPORAL_V1_R0/camera_to_dsi_display.bit |
| SHA-256 / bytes | F9AD71C7D33453461C1B47C56770EDD77B75838DBCB7A74E686AEEEF27C0A989 / 1789539 |
| Build Result | Synthesis → Physical Design → final Timing Check → bitgen；PASS |
| Release Decision | REJECTED: Balanced duplicate/missing EOL can incorrectly qualify previous-frame history; strict sequence guard required |
| LUT6 | 15490 / 21216 |
| FF | 15659 / 42432 |
| Slice | 16440 / 21216 (77.49%) |
| ERAM20K / DSP | 75 / 108；9 / 40 |
| Setup WNS / Hold WNS | +0.104ns / +0.020ns |
| Setup TNS / Hold TNS | 0ps / 0ps |
| STA coverage | 96.29% |
| Critical warnings | ['PHY-5060', 'PHY-5079']；新增类型[]，原始上下文随附 |
| Board Test Status | REJECTED；不用于上板验收 |

## 算法与预算

E_t=Q_t OR (Q_(t-1) AND 当前同坐标未抑制Sobel幅值>=floor(TH/2))。历史只保存原始QUALITY边缘，最多一帧、非递归，当前边缘不删除。原先Gaussian/Sobel/NMS/四跳不改；新增4级支持位中心搬运及1位/内部点历史缓存，未继承ROI大缓存/编码页面。

相比QUALITY路由净增{'lut': -672, 'ff': 236, 'slice': -1454, 'eram': 28, 'dsp': 0}；包含只读FIFO计数及第三行OSD的成本，不把净增量当单独算法模块成本。新增2寄存周期，Edge/Original27+OSD2+pack1=30；无整帧等待和新增空间偏移。慢速运动可能短暂增厚/双线，既有真实ROI无可靠轮廓真值，模型收益不冒充板上收益。

Sensor Exposure1990 half-lines/VTS1000/HTS1600/Gain15.75×、BLC15/AWB_V2/Original颜色、K3/K4/Logo/CNT/视频规格/MIPI/DDR/HDMI控制与PLL/SDC保持；64项TD输入和旧bit均已校验。只有已有OSD扩展B/S历史计数行；FIFO控制不改。

## 验证与风险

完整720p×10采集帧2,304,000有效拍/1,728,000打包字逐字节对照通过；Original、帧内配置锁存、提前/同拍SOF、全生产历史地址及中心搬运覆盖。单元另测复位、短帧、缺EOL、超长帧、TH变更、支持撤销与非递归释放；旧QUALITY/NMS小尺寸及所有link尾数/1280宽地址回归通过。FIFO计数启动/稳态/重复/饱和/复位与实际OSD字形打包独立验证。

综合已成功；驱动首次因查找实例面积行的辅助脚本错误停在综合之后，修正后验证全部TD输入不变及综合DB哈希，只恢复PHY，没有借此重编多个算法候选。原失败驱动日志保留。

STA通过不证明长期硬件稳定；既有FIFO Gray max_delay受clock groups覆盖的风险未修复、全局约束未改。S计数若增加，作为正式验收阻断项先查FIFO/DDR，不能用本算法掩盖。详见docs/EDGE_TEMPORAL_V1_DESIGN.md及最终报告/BOARD_TEST。

回滚：重新PROGRAM_SRAM烧录artifacts/bitstreams/EDGE_QUALITY_V1/camera_to_dsi_display.bit，SHA629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5；默认TEMPORAL_ENABLE=0也可恢复旧算法。候选未自动合并，不继续下一版本。
