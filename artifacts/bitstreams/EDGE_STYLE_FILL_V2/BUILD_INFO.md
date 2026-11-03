# BUILD_INFO — EDGE_STYLE_FILL_V2

| 项目 | 实际值 |
|---|---|
| Version / Role | EDGE_STYLE_FILL_V2 / MAIN |
| Branch | codex/main/edge-style-fill-v2 |
| 实际TD输入源码commit | 694559fd76676093e134229d435161ecb44ab00c |
| Git Tag | edge-style-fill-v2-candidate |
| 基线 / PR | EDGE_STYLE_FILL_V1 e17a1af；Draft PR 以 codex/main/edge-style-fill-v1 为 base，不自动合并 |
| Build Time | 2026-10-19T22:49:55.706046+08:00 |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit | D:\anlogic_formal_project\in_out_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit |
| 归档bit | artifacts/bitstreams/EDGE_STYLE_FILL_V2/camera_to_dsi_display.bit |
| SHA-256 / bytes | CFB7435648ED50310F053AFE138702F2094B0061B6A7DD68B3B064B6B3D88F51 / 1789539 |
| Build Result | Synthesis → Physical Design → final Timing Check → bitgen；PASS |
| Release Decision | candidate; board validation pending |
| LUT6 | 17170 / 21216 |
| FF | 16814 / 42432 |
| Slice | 18140 / 21216 (85.50%) |
| ERAM20K / DSP | 85 / 108；21 / 40 |
| Setup WNS / Hold WNS | +0.100ns / +0.020ns |
| Setup TNS / Hold TNS | 0ps / 0ps |
| STA coverage | 96.14% |
| Critical warnings | ['PHY-5060', 'PHY-5079']；新增类型[]，原始上下文随附 |
| Board Test Status | pending; STYLE appearance, five-mode switching, B/S and 30-minute stability unverified |

## 实际功能与验证

V2仅修改STYLE渲染：同色保守均值、9档共享明度/低色度中性保护、相干亮度暗侧描边。
仍为5拍局部STYLE与原27拍对齐窗口、2拍OSD、1拍打包；端到端新增0拍。
其余65个TD输入与V1一致；原四模式、EDGE_TEMPORAL、Sensor/ISP、按键/OSD、DDR/HDMI、PLL/SDC冻结。
模型、RTL结果与实板反馈边界见 docs/EDGE_STYLE_FILL_V2_DESIGN.md / REPORT.md / BOARD_TEST.md。
历史FIFO/Gray约束风险未修复，V2真实画质待用户上板。
回滚：artifacts/bitstreams/EDGE_STYLE_FILL_V1/camera_to_dsi_display.bit，
SHA256 B4FBB61FABD6A510B26EEC6DAD4D950FF8A3D2B6F561753D5611B334274B336E。

