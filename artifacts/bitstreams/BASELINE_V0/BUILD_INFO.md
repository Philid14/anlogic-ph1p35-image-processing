# BUILD_INFO — BASELINE_V0

本版本是 2026-10-05 实际烧录到 HX1P35A 并用于基础颜色测试的基线工程（Bayer 双线性去马赛克 + 原始 AWB + OSD 例程），
测试结论为**基础颜色测试不通过**。详细现象见 `docs/IMAGE_TUNING_LOG.md` 的 Baseline V0 条目。

## 版本标识

| 项目 | 值 |
|---|---|
| Version | `BASELINE_V0` |
| Git Commit（源码归档提交） | `7466c7f19e8e3f592486b52ba5d9720eb5f176c0` |
| Git Tag | 无（本轮**不**建立 `baseline-official-osd`，原因见下） |
| Build Time | 2026-10-05 20:13–20:22（TD 本地时间） |
| Device | PH1P35MDG324（开发板 HX1P35A） |
| Top Module | `design_top_wrapper` |
| TD 版本 | Tang Dynasty 6.2.168116 |
| 原始 bit 生成路径 | `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/best_result/camera_to_dsi_display.bit` |
| 归档 bit 路径 | `artifacts/bitstreams/BASELINE_V0/camera_to_dsi_display.bit` |
| Bit 大小 | 1,789,539 字节 |
| Bit SHA-256 | `D42E4AFC8CC6939230DAB332EEBE6E439297F1EA9FC57E6984152B60C673D668` |

## 关键源码与哈希

| 文件 | SHA-256 | 说明 |
|---|---|---|
| `docs/baseline/awb_v0_compiled.v` | `B6D9D83A6B48952CC9531DAF39BC6C6B94C4E45DDEFE603908E9CB275533E50A` | 本版本实际参与综合的 `user_source/hdl_source/awb.v` 副本 |

工程树中的 `user_source/hdl_source/awb.v` 在归档提交 `7466c7f` 中已改为 AWB_V1；
因此 V0 的源码以 `docs/baseline/awb_v0_compiled.v` 为唯一可恢复副本。

## 资源与时序（数据来源：本目录 `build_evidence/`）

| 指标 | 值 | 来源文件 |
|---|---:|---|
| LUT6 | 13,107 / 21,216（61.78%） | `phy_run.log`（`#lut6`） |
| Slice FF（seqs） | 13,351 | `phy_run.log`（`RUN-0007`） |
| Slices | 15,087（71.11%） | `phy_run.log`（route QoR 表） |
| ERAM20K | 40 / 108（37.04%） | `phy_run.log`（`#eram20k`） |
| DSP | 9 / 40（22.50%） | `phy_run.log`（`#dsp`） |
| Setup WNS | +0.109 ns（109 ps） | `camera_to_dsi_display_phy.ts`、`phy_run.log` |
| Hold WNS | +0.020 ns（20 ps） | 同上 |
| Setup / Hold TNS | 0.000 ns / 0.000 ns | `camera_to_dsi_display_phy.ts` |

## 为什么没有建立 `baseline-official-osd` tag

`AGENTS.md` 要求基线 tag 必须对应**未经修改的官方参考例程**。归档时确认：

- `in_out_example/.../user_source/hdl_source/awb.v` 已是 AWB_V1 候选修改
  （SHA-256 `F952339EC4F19C61947B98C041CF9801021A6763B6CF103D32A46D89D6B47AD3`），
  与已归档的 V0 源码（`B6D9D83A…`）不同；
- 当前工作目录中不存在可逐字节校验的官方原始副本。

因此本轮不伪造基线历史。若需建立 `baseline-official-osd` / `baseline-official-edge`，
必须先取回官方原始压缩包并逐文件校验后再单独提交与打 tag。

## Board Test Status

| 项目 | 记录 |
|---|---|
| 测试日期 | 2026-10-05，约 21:00 |
| 测试环境 | 同一室内环境，白 / 蓝 / 绿 / 红物体，固定机位 |
| 结果 | 白明显偏青蓝/青绿；蓝绿难分；红成分严重不足；暗部较差；"安路"Logo 与黄色 OSD 文字正常 |
| 结论 | **基础颜色测试不通过**；无寄存器读回与数值色度数据 |
| 证据 | 显示照片 `C:/Users/Lenovo/Downloads/vivo办公套件/IMG_20261005_2100*.jpg`（不在本仓库内） |

## 已知缺口

- V0 的 route 时序报告（`final_timing.rpt` 同类文件）已被 AWB_V1 构建覆盖，本目录仅保留 route QoR 与 `.ts` 摘要。
- 无 SC500CS 寄存器读回、无 RAW 采样、无精确色度数据；C 相机链路是否存在问题的判断仍缺证据。
