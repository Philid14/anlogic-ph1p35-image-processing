# BUILD_INFO — GAIN_TEST_C candidate

| 项目 | 值 |
|---|---|
| Version | `GAIN_TEST_C`（高模拟增益档） |
| Git Commit SHA（构建时源码/配置） | `1e3a601cfb8074aa30d81f83600ef5a7a8c42712` |
| Git Tag | `gain-test-c-candidate`（指向本归档提交） |
| Build Time | 2026-10-09 19:49–20:00，TD 本地时间 |
| Device / Top Module | `PH1P35MDG324` / `design_top_wrapper` |
| TD 版本 | Tang Dynasty 6.2.168116 |
| 原始 bit 生成路径 | `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display.bit` |
| 归档 bit 路径 | `artifacts/bitstreams/GAIN_TEST_C/camera_to_dsi_display.bit` |
| Bit SHA-256 | `A7CDBFADF6E10FB68C0B79FE8786AFFBA142D8F4509B48D449C4289ACE32FC66` |
| Bit 大小 | 1,789,539 bytes |
| Board Test Status | **待上板**；不能声称 I²C ACK/寄存器读回成功 |

## 唯一变量与源码指纹

固定 `0x3e08=0x1f, 0x3e09=0x20`，SC500CS 目标模拟增益 **8×**；Exposure `0x07c6`（1990 半行/995 行）、VTS 1000、HTS 1600、数字增益及其余 sensor 初始化值不变。相对 GAIN_TEST_A，实际编译 RTL 唯一变化是 `0x3e08` 的初始化字节。测试期间不要按增益键，避免 `ae_set` 同时重写曝光。

| 有效源码 | SHA-256 |
|---|---|
| `user_source/hdl_source/uics500_cfg/uics500reg_720p60.v` | `813E696926DAC3049C3B6209F1E5F94BC3EA7DAE7625332971B8E6054D761CDC` |
| `user_source/hdl_source/awb.v`（AWB_V2 冻结） | `5DB871953306D5EDB4F2D9B17E1EC18F0A6D32DE052192F77FDF999ECC336FF0` |
| `user_source/hdl_source/isp/isp_top.v`（BLC=15 冻结） | `4F15F8588FA6AA7249CD01D470E943E18B761F95B356AC3F7698E8C01B054DD5` |

## 构建、资源与时序

Synthesis、Physical Design、Timing Check、bitgen 完整通过；路由后 LUT6 **13,787**、Slice FF **13,632**、ERAM20K **40**、DSP **9**，Setup WNS **+0.104 ns**、Hold WNS **+0.020 ns**，Setup/Hold TNS 均 **0.000 ns**，违反端点 0。既有关键告警 `PHY-5060` ×2、`PHY-5079` ×1；没有发现新增关键告警或 Error。全局 setup 裕量较窄，不能代替上板长稳验证。

证据：`build_evidence/syn_td_20261009_194939.log`、`syn_gate.qor`、`camera_to_dsi_display_gate.area`、`phy_td_20261009_195409.log`、`phy_route.qor`、`camera_to_dsi_display_phy.area`、`camera_to_dsi_display_phy.ts`、`camera_to_dsi_display_exception.timing`。原始完整 `final_timing.rpt` 留在 TD 生成目录中，不纳入大型自动生成文件。
