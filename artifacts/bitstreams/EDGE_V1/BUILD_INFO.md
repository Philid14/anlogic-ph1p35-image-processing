# BUILD_INFO — EDGE_V1 candidate

| 项目 | 值 |
|---|---|
| Version | `EDGE_V1`，固定Sobel黑白输出 |
| Git Branch | `main` |
| Git Commit SHA（实际构建源码/配置） | `dd42086963eec1b1dbf8284048335502139da069` |
| Git Tag | `edge-v1-candidate`，指向包含本归档的candidate提交；用 `git rev-parse edge-v1-candidate^{commit}` 获得归档提交SHA |
| Build Time | 2026-10-10，Synthesis 21:41:04–21:46:15；Physical/Timing/bitgen 21:48:30–21:53:43，TD本地时间 |
| Device / Top Module | `PH1P35MDG324` / `design_top_wrapper` |
| TD版本 | Tang Dynasty 6.2.168116 |
| 原始bit生成路径 | `D:\anlogic_formal_project\in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit` |
| 归档bit路径 | `D:\anlogic_formal_project\artifacts\bitstreams\EDGE_V1\camera_to_dsi_display.bit` |
| Bit SHA-256 | `268EAEE8830AF99C6275EAB45AC1C1CDE231127B91DC3B4729754C6FD581D1D6` |
| Bit大小 | 1,789,539 bytes |
| Build Result | Synthesis → Physical Design → Timing Check → bitgen全部完成，两个TD命令退出码0 |
| LUT6 | 14,174 / 21,216（66.81%） |
| FF | 13,656 / 42,432（32.18%） |
| Slice | 16,031 / 21,216（75.56%） |
| RAM / ERAM | 34 ERAM20K / 108（31.48%）；全设计DRAM LUT552、shifter LUT112 |
| DSP | 9 / 40（22.50%） |
| Setup WNS / TNS / 违例端点 | +0.107 ns / 0.000 ns / 0 |
| Hold WNS / TNS / 违例端点 | +0.020 ns / 0.000 ns / 0 |
| 新的关键warning | 未发现新增类型；既有PHY-5060、PHY-5079保留，见原始日志 |
| Board Test Status | **待上板**；本轮仅完成固定Edge candidate，未宣称采集/显示/长稳实测通过 |

## 唯一主要变量与冻结基线

基线为GAIN_TEST_E，用户确认15.75×亮度基本满意，并暂选为固定画质基准。唯一新增功能为AWB后Sobel：`EDGE_ENABLE=1`、`EDGE_THRESHOLD=80`。算法为相邻两像素灰度平均的640点水平采样、3×3 Sobel、`|Gx|+|Gy| >= 80`、每结果复制两像素；输出仍为1280×720紧凑RGB及原128b DDR打包。前两行/每行首4像素清黑，因果窗口约右移2原像素/下移1行。

冻结Exposure1990 half-lines（0x07c6）、VTS1000、HTS1600、`0x3e08=0x1f`、`0x3e09=0x3f`（理论15.75×）、Digital Gain、BLC15、AWB_V2 CHROMA32及其他参数、MIPI/demosaic/DDR/OSD/HDMI、按键、PLL、ADC/SDC。192个主工程冻结文件及68个B/C只读参考文件在构建结束后SHA核对一致。未实现AE/Gamma/CCM或运行时模式切换。

## 接口与资源解释

算法采用5级寄存流水，data/valid/提前SOF通知tuser/行尾tlast统一延迟5拍。打包器再寄存1拍，Edge分支顶层tlast补1拍；不把现有提前SOF误当成首valid拍。新增模块I_tready固定1，保留正式工程不可背压的视频契约。Original编译分支保留原直通接线。

两行逻辑缓存共10240bit，Sobel层级综合实测256分布式RAM LUT、32 F7MUX、0 ERAM、0 DSP。比E的路由结果增加417 LUT6、31 FF、379 Slice，ERAM减少6，DSP不变；ERAM减少来自固定黑白输出导致的既有FIFO优化。不得把此数字外推为未来四模式所需资源。Setup为正但余量有限，仍需实拍及长稳验证。

## 有效源码指纹

| 文件（相对正式工程） | SHA-256 |
|---|---|
| `user_source/hdl_source/isp/edge_detect_96.v` | `0CEEEFE359D04369AFEA8A9B4BF205252032CD70320A29AB0F9DCEF790A099FC` |
| `user_source/hdl_source/isp/isp_top.v` | `82BD1CCC1082583B16DEC42B9C77D24D1771559DC57559346D09CB7074F94807` |
| `user_source/hdl_source/awb.v` | `5DB871953306D5EDB4F2D9B17E1EC18F0A6D32DE052192F77FDF999ECC336FF0` |
| `user_source/hdl_source/uics500_cfg/uics500reg_720p60.v` | `22D1D423000146DFB583519E2325E7998DEB76162AAB13CADDE50C4EB11B233B` |

## 验证与证据

`tests/run_edge_v1.py --full` 的7组逐拍独立空间参考比较全部通过，共512024有效输入拍，含两完整1280×720帧、阈值边界、RGB顺序、行/帧通知、截断帧恢复、Original和Edge的实际ISP边界接线及真实打包器。每完整帧172800个128b DDR字。测试不模拟完整MIPI/AWB/DDR/HDMI，不能替代上板验证。

`build_evidence/`保留：综合日志、gate.qor、gate.area、物理日志、route.qor、phy.area、phy.ts、exception.timing、RTL_VERIFICATION.md。完整多MB逐路径报告留在忽略的TD Runs目录。既有IP锁存/未连接/宽度告警保留，新增Sobel无对应告警；物理关键告警为PHY-5060与PHY-5079，没有新增关键类型或Error。

前一次源码检查点的综合因发现打包后行尾标记需再对齐一拍而主动中断，未生成有效候选；本bit来自修正提交dd42086后重新完整构建。上板采用PROGRAM_SRAM，步骤和待填反馈见 `docs/EDGE_V1_BOARD_TEST.md`。本candidate归档后停止，等待用户实测。
