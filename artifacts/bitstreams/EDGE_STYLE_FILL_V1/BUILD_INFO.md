# BUILD_INFO — EDGE_STYLE_FILL_V1

| 项目 | 实际值 |
|---|---|
| Version / Role | EDGE_STYLE_FILL_V1 / MAIN |
| Branch | codex/main/edge-style-fill-v1 |
| 实际TD输入源码commit | 042345cb0e92a1cc5ea0a74fed1be352cf338f2c |
| Git Tag | edge-style-fill-v1-candidate |
| 基线 / PR | EDGE_MULTI_MODE_V1 ed55269；Draft PR 以 codex/main/edge-multi-mode-v1 为 base，不自动合并 |
| Build Time | 2026-10-19T18:48:13.913675+08:00 |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit | D:\anlogic_formal_project\in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit |
| 归档bit | artifacts/bitstreams/EDGE_STYLE_FILL_V1/camera_to_dsi_display.bit |
| SHA-256 / bytes | B4FBB61FABD6A510B26EEC6DAD4D950FF8A3D2B6F561753D5611B334274B336E / 1789539 |
| Build Result | Synthesis → Physical Design → final Timing Check → bitgen；PASS |
| Release Decision | candidate; board validation pending |
| LUT6 | 16592 / 21216 |
| FF | 16972 / 42432 |
| Slice | 17792 / 21216 (83.86%) |
| ERAM20K / DSP | 85 / 108；21 / 40 |
| Setup WNS / Hold WNS | +0.104ns / +0.020ns |
| Setup TNS / Hold TNS | 0ps / 0ps |
| STA coverage | 95.99% |
| Critical warnings | ['PHY-5060', 'PHY-5079']；新增类型[]，原始上下文随附 |
| Board Test Status | pending; STYLE appearance, five-mode switching, B/S and 30-minute stability unverified |

## 实际功能与验证

新增 STYLE：有界2×2同色区域均值、64色填色与高对比描黑；不是完整对象/洞填充。
19位配置，五模式；27拍分支对齐、2拍OSD、1拍打包保持30拍总处理窗口。
算法、模型、测试与边界见 docs/EDGE_STYLE_FILL_V1_DESIGN.md 和 REPORT.md。
历史FIFO B/S与Gray约束覆盖问题未修复；实板持续运行与画质待用户验收。
回滚：烧录 artifacts/bitstreams/EDGE_MULTI_MODE_V1/camera_to_dsi_display.bit，
SHA256 8C62195DA8A2F8748CE9D6CFD7D9703BCB81E6F6CDA09AEDF4BBB0DE0FE0BBE9。

