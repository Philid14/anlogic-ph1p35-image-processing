# BUILD_INFO — AWB_V2 candidate

AWB_V2 是在已上板保留的 BLC_V1 上进行的**单变量实验**：仅改变实际编译 `user_source/hdl_source/awb.v` 的 Gray World 统计样本选择。BLC `BLACK_LEVEL_RAW10=15`、SC500CS 寄存器、曝光/增益、MIPI、Demosaic、DDR、OSD、HDMI、Gamma、CCM 均保持 BLC_V1 状态。本 bit 尚未上板，画质和长期稳定性均待实测。

## 版本标识

| 项目 | 值 |
|---|---|
| Version | `AWB_V2` candidate |
| Git Commit（本 bit 的源码提交） | `529e5245e386e1f459a4074d01275326571a3d4b` |
| Git Tag | `awb-v2-candidate`（指向包含本 bit 与 BUILD_INFO 的归档提交） |
| Build Time | 2026-10-08 22:35–22:43（综合 22:35–22:39，Physical Design 22:39–22:43，TD 本地时间） |
| Device | PH1P35MDG324（HX1P35A） |
| Top Module | `design_top_wrapper` |
| TD 版本 | Tang Dynasty 6.2.168116 |
| 原始 bit 生成路径 | `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display.bit` |
| 归档 bit 路径 | `artifacts/bitstreams/AWB_V2/camera_to_dsi_display.bit` |
| Bit 生成时间 | 2026-10-08 22:43:49 |
| Bit 大小 | 1,789,539 字节 |
| Bit SHA-256 | `D6AA67BB303D661E9ABEADCDE456AB27F6828CA948D89029F89F23028D5AA111` |

## 关键源码与哈希

| 文件 | SHA-256 |
|---|---|
| `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/awb.v` | `5DB871953306D5EDB4F2D9B17E1EC18F0A6D32DE052192F77FDF999ECC336FF0` |
| `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/isp/isp_top.v`（BLC 不变） | `4F15F8588FA6AA7249CD01D470E943E18B761F95B356AC3F7698E8C01B054DD5` |

## 唯一主要变量

- 原样本：每个 RGB888 像素只要求 `24 <= max(R,G,B) < 240`。
- 新样本：保留原亮度窗口，增加 `max(R,G,B)-min(R,G,B) < CHROMA_THRESHOLD`，其中 `CHROMA_THRESHOLD=32`（RGB888 实验初值）；同拍 4 像素分别判定。没有调整输出 RGB 数据或像素延迟。
- 样本不足：有效低色度像素少于原有 `MIN_SAMPLES=1024` 时，不启动除法，保留上一个有效目标和当前 R/B 增益；不回退全帧纯色 Gray World。`GAIN_MIN=0.75`、`GAIN_MAX=3.00`、`GAIN_STEP=0.125/frame`、帧边界更新及其余参数均不变。
- `tests/awb_v2_selection_model.py` 用五类单色/中性色以及红物体占 25% 的混合场景检查定点增益趋势；它是离线模型，不是 RTL 时序仿真或上板证明。

## 资源与时序（归档 `build_evidence/`）

| 指标 | AWB_V2 | BLC_V1 | 变化 |
|---|---:|---:|---:|
| LUT6 | 13,708 / 21,216（64.61%） | 13,474 | +234 |
| Slice FF | 13,627 / 42,432（32.11%） | 13,627 | 0 |
| Slices（route QoR） | 15,669（73.85%） | 15,434 | +235 |
| ERAM20K | 40 / 108 | 40 | 0 |
| DSP | 9 / 40 | 9 | 0 |
| Setup WNS（route） | +0.101 ns | +0.137 ns | −0.036 ns |
| Hold WNS（route） | +0.020 ns | +0.020 ns | 0 |
| Setup / Hold TNS | 0.000 ns / 0.000 ns | 0.000 ns / 0.000 ns | 0 |
| 违反约束端点 | 0 | 0 | 0 |

综合、Physical Design、Timing Check 和 bitgen 全部成功。`final_timing.rpt` 于 22:43:39 生成；MIPI 接收时钟域最差 Setup slack 为 +3.823 ns（BLC_V1 为 +5.763 ns）。该裕量下降需在上板时注意视频连续性；全局 Setup/Hold 仍无违反。

## 告警

`build_evidence/phy_td_20261008_223941.log` 有既有 `PHY-5060` ×2（I²C/camera clock 混合扇出）和 `PHY-5079` ×1（时钟本地布线）；与 BLC_V1 相同，无新增关键告警或编译 Error。综合既有未驱动端口/引脚告警仍存在，本轮未改其所在接口。

## Board Test Status

**待上板**。先用 BLC_V1 bit 在相同灯光、机位、显示器下建立对照，再烧录 AWB_V2。依次测白纸、中性灰、正常综合色彩场景，以及各占画面约 20–30% 的红/绿/蓝目标（背景留中性色）；暗场只记录，不作为本次 AWB 成败指标。检查白/灰中性、彩色目标进出时整体白平衡和帧间闪色，并确认 HDMI 连续显示、OSD“安路”可见。若白/灰更偏、正常场景退化、增益长期不更新或明显闪色，回滚 BLC_V1 bit。

## 证据清单

| 文件 | 用途 |
|---|---|
| `build_evidence/syn_td_20261008_223524.log`、`syn_gate.qor`、`camera_to_dsi_display_gate.area` | 综合日志、QoR 与门级面积 |
| `build_evidence/phy_td_20261008_223941.log` | Physical Design、Timing Check、bitgen 日志 |
| `build_evidence/phy_route.qor`、`camera_to_dsi_display_phy.area`、`camera_to_dsi_display_phy.ts` | 路由后资源与时序摘要 |
| `build_evidence/camera_to_dsi_display_exception.timing` | 例外路径检查 |

完整多兆字节 `final_timing.rpt` 留在本地 TD `*_Runs/phy_1/`，按 `.gitignore` 不直接提交。
