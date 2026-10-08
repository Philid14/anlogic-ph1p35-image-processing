# BUILD_INFO — BLC_V1

BLC_V1 是 RAW10 黑电平扣除的**单变量实验**。AWB_V1、SC500CS 寄存器、曝光与增益、Gamma、CCM、MIPI、DDR、OSD、HDMI 均未修改。`BLACK_LEVEL_RAW10=15` 来源于工程自带但未接入的 `isp/BLC/BLC.v` 四路默认值，**不是 SC500CS 测量值或规格值**。2026-10-08 用户反馈本 bit 已上板，方向有正向效果，暂时冻结参数。

## 版本标识

| 项目 | 值 |
|---|---|
| Version | `BLC_V1` |
| Git Commit（本 bit 的源码提交） | `347dff76d67f8072fc3f0c7a4e78bd01bfae7dbc` |
| Git Tag | `blc-v1-candidate`（原候选归档）；`blc-v1`（上板结果记录提交） |
| Build Time | 2026-10-08 18:13–18:22（TD 本地时间） |
| Device | PH1P35MDG324（HX1P35A） |
| Top Module | `design_top_wrapper` |
| TD 版本 | Tang Dynasty 6.2.168116 |
| 原始 bit 生成路径 | `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display.bit` |
| 归档 bit 路径 | `artifacts/bitstreams/BLC_V1/camera_to_dsi_display.bit` |
| Bit 生成时间 | 2026-10-08 18:22:41 |
| Bit 大小 | 1,789,539 字节 |
| Bit SHA-256 | `2B9E427DEE8304106F5E75A686899D189E4B61EB3514A4AE33C51EA536FB133D` |

## 关键源码与哈希

| 文件 | SHA-256 |
|---|---|
| `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/isp_top.v` | `4F15F8588FA6AA7249CD01D470E943E18B761F95B356AC3F7698E8C01B054DD5` |
| `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/awb.v`（与 AWB_V1 相同） | `F952339EC4F19C61947B98C041CF9801021A6763B6CF103D32A46D89D6B47AD3` |

## 唯一主要变量

`isp_top.v` 在 demosaic 前对同拍四个 Bayer RAW10 像素分别做 `max(raw10 - 15, 0)`。减法为组合逻辑，沿用原有 valid、ready、frame 和 line 连接，未加入新流水级。相对于 AWB_V1，原偏置为 **0（旁路）**，实验偏置为 **15 RAW10 级**；该值须用遮光黑场上板测试验证。详见 `docs/IMAGE_TUNING_LOG.md`。

## 资源与时序（归档 `build_evidence/`）

| 指标 | BLC_V1 | AWB_V1 | 变化 |
|---|---:|---:|---:|
| LUT6 | 13,474 / 21,216（63.51%） | 13,561 | −87 |
| Slice FF | 13,627 / 42,432（32.11%） | 13,609 | +18 |
| Slices（route QoR） | 15,434（72.75%） | 15,688 | −254 |
| ERAM20K | 40 / 108 | 40 | 0 |
| DSP | 9 / 40 | 9 | 0 |
| Setup WNS（route） | +0.137 ns | +0.101 ns | +0.036 ns |
| Hold WNS（route） | +0.020 ns | +0.020 ns | 0 |
| Setup / Hold TNS | 0.000 ns / 0.000 ns | 0.000 ns / 0.000 ns | 0 |
| 违反约束端点 | 0 | 0 | 0 |

综合、Physical Design、Timing Check 与 bitgen 均成功。`final_timing.rpt` 于 18:22:32 生成；全局 Setup/Hold 时序均无违反。MIPI 时钟域最差 Setup slack +5.763 ns（AWB_V1 为 +6.934 ns），该域裕量有所下降，上板需重点观察视频连续性。

## 关键告警

`build_evidence/phy_td_20261008_181744.log` 有 `PHY-5060` ×2（I²C/camera clock 混合扇出）和 `PHY-5079` ×1（时钟本地布线），与 AWB_V1 相同；无新增关键告警或 Error。综合的 `SYN-5013` 提及 `u_isp_top/O_tready` 未驱动，顶层未连接该输出，亦为既有情况。

## Board Test Status

**用户反馈已上板（2026-10-08）**：相对先前版本，白色和绿色有一定改善；遮光时 HDMI 摄像头区域呈较好的黑色，无明显灰白 pedestal。白色仍偏青绿；红色、蓝色分别能识别为红/暖色和蓝色，但明显偏暗。较暗真实场景仍亮度不足、色彩弱。用户目前未观察到大面积黑位压死、HDMI/OSD 颜色异常、花屏或明显时序问题。没有提供 RAW 黑场数值、定量色卡数据或长时间运行记录，因此不能宣称黑电平 15 已校准或全部稳定性门槛通过。本版保留供 AWB_V2 对照，`BLACK_LEVEL_RAW10=15` 暂时冻结；低照度不足留待独立曝光/增益实验。

## 证据清单

| 文件 | 用途 |
|---|---|
| `build_evidence/syn_td_20261008_181338.log` | 完整综合日志 |
| `build_evidence/syn_gate.qor`、`camera_to_dsi_display_gate.area` | 综合 QoR / 面积 |
| `build_evidence/phy_td_20261008_181744.log` | Physical Design 与 bitgen 日志 |
| `build_evidence/phy_route.qor`、`camera_to_dsi_display_phy.area`、`camera_to_dsi_display_phy.ts` | 路由后资源与 Setup/Hold 指标 |
| `build_evidence/camera_to_dsi_display_exception.timing` | 时序例外检查 |

完整多兆字节 `final_timing.rpt` 保留在本地 TD `*_Runs/phy_1/`，依 `.gitignore` 不直接提交。
