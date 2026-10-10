# BUILD_INFO — GAIN_TEST_B candidate

| 项目 | 值 |
|---|---|
| Version | `GAIN_TEST_B`（当前模拟增益对照档） |
| Git Commit SHA（构建时源码/配置基线） | `16be9c4378fd5a94c467315a0a9e9e45e54b5965` |
| Git Tag | `gain-test-b-candidate`（指向本归档提交） |
| Build Time | 2026-10-09 19:28–19:38，TD 本地时间 |
| Device / Top Module | `PH1P35MDG324` / `design_top_wrapper` |
| TD 版本 | Tang Dynasty 6.2.168116 |
| 原始 bit 生成路径 | `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display.bit` |
| 归档 bit 路径 | `artifacts/bitstreams/GAIN_TEST_B/camera_to_dsi_display.bit` |
| Bit SHA-256 | `A34131C7F2E991F3C9C59627DADBE797CCE7A33E4EB0A0F9A272A5BD9C8CB37E` |
| Bit 大小 | 1,789,539 bytes |
| Board Test Status | **已上板（用户 2026-10-10 反馈）**；在完全相同场景下 A(1×)→B(4×)→C(8×) 亮度稳定、明显、单调增加。B 为中间对照；无 I²C ACK/寄存器读回或定量噪声记录。 |

## 唯一变量与源码指纹

本版固定 `0x3e08=0x0f, 0x3e09=0x20`，SC500CS 目标模拟增益 4×；Exposure `0x07c6`（1990 半行/995 行），VTS 1000，HTS 1600。本版是 AWB_V2 的 sensor gain 对照档；与 A、C 的**功能源码唯一差异**应为实际编译初始化表中的 `0x3e08` 数据字节。测试期间不要按增益键，以免 `ae_set` 同时重写不合法的 3000 半行曝光。

| 有效源码 | SHA-256 |
|---|---|
| `user_source/hdl_source/uics500_cfg/uics500reg_720p60.v` | `51E693624B711E0828DEE37BC3B8A0C3904CC5A29631040365452BDA674A0AFD` |
| `user_source/hdl_source/awb.v`（AWB_V2 冻结） | `5DB871953306D5EDB4F2D9B17E1EC18F0A6D32DE052192F77FDF999ECC336FF0` |
| `user_source/hdl_source/isp/isp_top.v`（BLC=15 冻结） | `4F15F8588FA6AA7249CD01D470E943E18B761F95B356AC3F7698E8C01B054DD5` |

## 构建、资源与时序

Synthesis、Physical Design、Timing Check、bitgen 完整通过；路由后 LUT6 **13,214**、Slice FF **13,610**、ERAM20K **40**、DSP **9**，Setup WNS **+0.107 ns**、Hold WNS **+0.020 ns**，Setup/Hold TNS 均 **0.000 ns**，违反端点 0。既有关键告警 `PHY-5060` ×2、`PHY-5079` ×1；没有发现新增关键告警或 Error。全局 setup 裕量较窄，不能代替上板长稳验证。

证据：`build_evidence/syn_td_20261009_192854.log`、`syn_gate.qor`、`camera_to_dsi_display_gate.area`、`phy_td_20261009_193437.log`、`phy_route.qor`、`camera_to_dsi_display_phy.area`、`camera_to_dsi_display_phy.ts`、`camera_to_dsi_display_exception.timing`。原始完整 `final_timing.rpt` 留在 TD 生成目录中，不纳入大型自动生成文件。
