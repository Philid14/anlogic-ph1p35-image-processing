# BUILD_INFO — AWB_V1

AWB_V1 是**单变量实验候选版本**：只修改实际参与综合的 `user_source/hdl_source/awb.v`，
其余摄像头寄存器、曝光/增益控制、MIPI、DDR、OSD、HDMI、Gamma、CCM 均保持 V0 不变。
本版本**尚未上板验证**，不得据此宣称画质已改善。

## 版本标识

| 项目 | 值 |
|---|---|
| Version | `AWB_V1` |
| Git Commit（本 bit 的源码提交） | `7466c7f19e8e3f592486b52ba5d9720eb5f176c0` |
| Git Tag | `awb-v1-candidate`（指向包含本 bit 与 BUILD_INFO 的归档提交） |
| Build Time | 2026-10-05 21:43–22:17（综合 22:07–22:11，实现 22:12–22:17，TD 本地时间） |
| Device | PH1P35MDG324（开发板 HX1P35A） |
| Top Module | `design_top_wrapper` |
| TD 版本 | Tang Dynasty 6.2.168116 |
| 原始 bit 生成路径 | `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display.bit` |
| 归档 bit 路径 | `artifacts/bitstreams/AWB_V1/camera_to_dsi_display.bit` |
| Bit 生成时间 | 2026-10-05 22:17:28 |
| Bit 大小 | 1,789,539 字节 |
| Bit SHA-256 | `6512B12C1F231DED42A7809766273CA58D677472FFB08BBE009B839512C729A3` |

## 关键源码与哈希

| 文件 | SHA-256 |
|---|---|
| `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/awb.v` | `F952339EC4F19C61947B98C041CF9801021A6763B6CF103D32A46D89D6B47AD3` |

注意：同一工程树内的 `user_source/hdl_source/isp/awb/awb.v` **不参与**本工程综合，
本轮未修改；综合日志 `build_evidence/syn_td_20261005_220717.log` 中展开的是上面这份 `hdl_source/awb.v`。

## 唯一主要变量

- 统计：每拍 4 像素共同统计全帧 `R/G/B` 累加（原为每拍仅 1 像素）
- 样本筛选：仅计入最大通道在 `[24, 239]` 的像素，且有效样本 ≥ 1024
- 更新时机：帧末计算、次帧固定增益（原为帧内逐拍更新）
- 增益范围与步进：Q4.16，限制 0.75×–3.00×，每帧最多变化 0.125×；含除零保护与饱和裁剪

## 资源与时序（数据来源：本目录 `build_evidence/`）

| 指标 | AWB_V1 | Baseline V0 | 变化 |
|---|---:|---:|---:|
| LUT6 | 13,561 / 21,216（63.92%） | 13,107 | +454 |
| Slice FF（seqs） | 13,568 | 13,351 | +217 |
| Slices（route QoR） | 15,688（73.94%） | 15,087 | +601 |
| ERAM20K | 40 / 108 | 40 | 0 |
| DSP | 9 / 40 | 9 | 0 |
| Setup WNS（route） | +0.101 ns | +0.109 ns | −0.008 ns |
| Hold WNS（route） | +0.020 ns | +0.020 ns | 0 |
| Setup / Hold TNS | 0.000 ns / 0.000 ns | 0.000 ns / 0.000 ns | 0 |
| 违反约束端点 | 0 | 0 | 0 |

综合（gate）阶段估算为 Setup WNS −2.363 ns、Hold WNS +0.114 ns
（`camera_to_dsi_display_gate.ts`），属综合估计值，最终实现后已收敛为正裕量。

## 关键告警

`build_evidence/phy_td_20261005_221212.log` 中有 3 条关键告警：

- `PHY-5060` ×2：既有 I²C / camera 时钟与控制混合扇出
- `PHY-5079` ×1：一条时钟网使用本地布线

与 V0 的 `phy_run.log` 告警集合相同；本轮未修改时钟、SDC 或约束。无编译 Error。

## Board Test Status

**未上板**。本 bit 已生成但尚未烧录测试，画质结论一律为"待验证"。
上板后必须按 `docs/IMAGE_TUNING_LOG.md` 的六场景复测步骤记录结果，再决定是否建立最终 tag `awb-v1`。

## 证据清单

| 文件 | 用途 |
|---|---|
| `build_evidence/syn_td_20261005_220717.log` | 综合日志，确认实际编译 `hdl_source/awb.v` 并展开 |
| `build_evidence/syn_gate.qor`、`camera_to_dsi_display_gate.area`、`camera_to_dsi_display_gate.ts` | 综合 QoR 与门级面积/时序摘要 |
| `build_evidence/phy_td_20261005_221212.log` | Physical Design 完整日志（含 route QoR、告警） |
| `build_evidence/phy_route.qor` | route 阶段 QoR 指标 |
| `build_evidence/camera_to_dsi_display_phy.ts` | route 后 Setup/Hold WNS/TNS 摘要 |
| `build_evidence/camera_to_dsi_display_phy.area` | 实现后面积占用明细 |
| `build_evidence/camera_to_dsi_display_exception.timing` | 例外路径/时序例外检查 |

未归档的多兆字节报告（`final_timing.rpt` 等）保留在本机
`td_project/camera_to_dsi_display_Runs/phy_1/`，该目录按 `AGENTS.md` 要求由 `.gitignore` 排除。
