# BUILD_INFO — GAIN_TEST_D candidate

| 项目 | 值 |
|---|---|
| Version | `GAIN_TEST_D`（模拟增益上区间测试） |
| Git Commit SHA（构建时源码/配置） | `1a3e549fb2ebef29412c90098ccae3c44681f021` |
| Git Tag | `gain-test-d-candidate`（指向本归档提交） |
| Build Time | 2026-10-10 10:39–10:49，TD 本地时间 |
| Device / Top Module | `PH1P35MDG324` / `design_top_wrapper` |
| TD 版本 | Tang Dynasty 6.2.168116 |
| 原始 bit 生成路径 | `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display.bit` |
| 归档 bit 路径 | `artifacts/bitstreams/GAIN_TEST_D/camera_to_dsi_display.bit` |
| Bit SHA-256 | `78E20726747B65B7CC6B5A1149698824B0AA83157E6A8A4DD3BB5DEAEA00C80A` |
| Bit 大小 | 1,789,539 bytes |
| Board Test Status | **待上板**。A/B/C 的增益响应已获用户实测确认，本版亮度、噪声与色彩尚未实测。 |

## 唯一变量与源码指纹

固定 `0x3e08=0x1f, 0x3e09=0x30`，目标模拟增益 **8×48/32=12×**。相对已上板 GAIN_TEST_C，实际编译 RTL 的唯一功能变化是初始化表 `0x3e09: 0x20→0x30`，另把旧的“细档保持 0x20”注释改为中性说明。Exposure `0x07c6`（1990 half-lines）、VTS 1000、HTS 1600、数字增益及其余 sensor 初始化值不变；BLC 15、AWB_V2 和视频链不变。测试期间不要按增益键。

| 有效源码 | SHA-256 |
|---|---|
| `user_source/hdl_source/uics500_cfg/uics500reg_720p60.v` | `C0EB1AA627A943AC466B8B4683032D7B9E26A17251F519814D7EAE79D41743A5` |
| `user_source/hdl_source/awb.v`（AWB_V2 冻结） | `5DB871953306D5EDB4F2D9B17E1EC18F0A6D32DE052192F77FDF999ECC336FF0` |
| `user_source/hdl_source/isp/isp_top.v`（BLC=15 冻结） | `4F15F8588FA6AA7249CD01D470E943E18B761F95B356AC3F7698E8C01B054DD5` |

## 构建、资源与时序

Synthesis、Physical Design、Timing Check、bitgen 完整通过；路由后 LUT6 **13,841**、Slice FF **13,631**、ERAM20K **40**、DSP **9**，Setup WNS **+0.106 ns**、Hold WNS **+0.020 ns**，Setup/Hold TNS 均 **0.000 ns**，违反端点 0。既有关键告警 `PHY-5060` ×2、`PHY-5079` ×1；没有发现新增关键告警或 Error。全局 setup 裕量较窄，仍须上板验证显示连续性。

证据：`build_evidence/syn_td_20261010_103924.log`、`syn_gate.qor`、`camera_to_dsi_display_gate.area`、`phy_td_20261010_104341.log`、`phy_route.qor`、`camera_to_dsi_display_phy.area`、`camera_to_dsi_display_phy.ts`、`camera_to_dsi_display_exception.timing`。完整 `final_timing.rpt` 留在 TD 生成目录中，不纳入大型自动生成文件。
