# BUILD_INFO — GAIN_TEST_E candidate

| 项目 | 值 |
|---|---|
| Version | `GAIN_TEST_E`（模拟增益上限实验） |
| Git Commit SHA（构建时源码/配置） | `b2301a228050458051d4425484fef4c0c523a931` |
| Git Tag | `gain-test-e-candidate`（指向本归档提交） |
| Build Time | 2026-10-10 10:49–11:00，TD 本地时间 |
| Device / Top Module | `PH1P35MDG324` / `design_top_wrapper` |
| TD 版本 | Tang Dynasty 6.2.168116 |
| 原始 bit 生成路径 | `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display.bit` |
| 归档 bit 路径 | `artifacts/bitstreams/GAIN_TEST_E/camera_to_dsi_display.bit` |
| Bit SHA-256 | `EE477E5BAC6D3A315408D2935F80D9DFD85240D45060BA6C434AC421BFE900E2` |
| Bit 大小 | 1,789,539 bytes |
| Board Test Status | **已上板（用户 2026-10-10 本轮任务反馈）**：15.75×亮度基本满意，暂选为后续算法的固定画质基线；噪声定量、寄存器读回、长时间运行仍未提供。本结果对应正式 tag `gain-test-e`，原 candidate tag 保留。 |

## 唯一变量与源码指纹

固定 `0x3e08=0x1f, 0x3e09=0x3f`，理论模拟增益 **8×63/32=15.75×**。相对 GAIN_TEST_D，实际编译 RTL 的唯一功能变化是初始化表 `0x3e09: 0x30→0x3f`。Exposure `0x07c6`（1990 half-lines）、VTS 1000、HTS 1600、数字增益及其余 sensor 初始化值不变；BLC 15、AWB_V2 和视频链不变。测试期间不要按增益键。

| 有效源码 | SHA-256 |
|---|---|
| `user_source/hdl_source/uics500_cfg/uics500reg_720p60.v` | `22D1D423000146DFB583519E2325E7998DEB76162AAB13CADDE50C4EB11B233B` |
| `user_source/hdl_source/awb.v`（AWB_V2 冻结） | `5DB871953306D5EDB4F2D9B17E1EC18F0A6D32DE052192F77FDF999ECC336FF0` |
| `user_source/hdl_source/isp/isp_top.v`（BLC=15 冻结） | `4F15F8588FA6AA7249CD01D470E943E18B761F95B356AC3F7698E8C01B054DD5` |

## 构建、资源与时序

Synthesis、Physical Design、Timing Check、bitgen 完整结束；路由后 LUT6 **13,757**、Slice FF **13,625**、ERAM20K **40**、DSP **9**。Setup WNS **0.000 ns**、Hold WNS **+0.020 ns**，Setup/Hold TNS 均 **0.000 ns**，违反端点 0。**Setup 裕量为零**，属于贴边满足时序；上板应特别留意 HDMI 连续性，不能把此结果当作充裕的时序余量。最差 setup 路径位于 `HDMI_PIXEL_CLK` 时钟域，相关 HDL 未在本次实验改动。既有 `PHY-5060`、`PHY-5079` 类型告警，没有发现新增关键告警类型或 Error。

证据：`build_evidence/syn_td_20261010_104958.log`、`syn_gate.qor`、`camera_to_dsi_display_gate.area`、`phy_td_20261010_105502.log`、`phy_route.qor`、`camera_to_dsi_display_phy.area`、`camera_to_dsi_display_phy.ts`、`camera_to_dsi_display_exception.timing`。完整 `final_timing.rpt` 留在 TD 生成目录中，不纳入大型自动生成文件。
