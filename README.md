# 2026 FPGA 创新设计赛道 · 上海安路选题二

**基于安路 PH1P35 的实时数字图像处理系统**

以安路 **PH1P35MDG324** 为核心、在 **HX1P35A** 开发板上实现
`MIPI 采集 → FPGA 端图像处理 → 含"安路"Logo 的 OSD → HDMI 实时显示` 的完整链路。

工程基准、指标与验收要求的唯一权威文件是 [`AGENTS.md`](AGENTS.md)；
原始赛题见 [`docs/赛题/上海安路信息科技股份有限公司_2026FPGA创新设计赛道选题指南.pdf`](docs/赛题/上海安路信息科技股份有限公司_2026FPGA创新设计赛道选题指南.pdf) 第 16–18 页。

## EDGE_STYLE_FILL_V1 candidate

新增五模式中的 **STYLE：局部同色区域均值填色、64色块化与边界描黑**；
这是有界风格化，不是全局闭合轮廓/洞填充。原四模式保留，等待实板验收。

- [设计与边界](docs/EDGE_STYLE_FILL_V1_DESIGN.md)
- [构建、资源与验证报告](docs/EDGE_STYLE_FILL_V1_REPORT.md)
- [上板步骤与失败判定](docs/EDGE_STYLE_FILL_V1_BOARD_TEST.md)
- [bit与BUILD_INFO](artifacts/bitstreams/EDGE_STYLE_FILL_V1/BUILD_INFO.md)

## 目录结构

| 路径 | 内容 |
|---|---|
| `AGENTS.md` | 赛题基准、平台约束、验收门槛、Git/GitHub 与实验追溯规则 |
| `docs/TEAM_AI_WORK_PROTOCOL.md` | 三人 AI 分工、文件所有权、接口协议、GitHub PR 审查与角色启动提示词 |
| `docs/` | 画质调试记录、GitHub 参考调研、官方基线源码副本、赛题资料 |
| `docs/IMAGE_TUNING_LOG.md` | 每个实际上板版本的参数、bit、构建与测试记录 |
| `docs/GITHUB_REFERENCE_RESEARCH.md` | GitHub 外部参考的仓库/许可/采用方式记录 |
| `in_out_example/lab_ex3_osd_SC500_720P/` | 主工程：OSD 叠加例程（当前开发主线） |
| `edge_example/lab_ex2_edge_SC500_720P/` | 官方边缘检测例程（第二参考） |
| `artifacts/bitstreams/<VERSION>/` | 每个上板版本的最终 bit 与 `BUILD_INFO.md` |

## 构建与烧录

1. 用 Tang Dynasty（TD）打开工程入口 `.al`：
   `in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.al`
2. 依次执行 Synthesis → Physical Design → Timing Check → 生成 bit。
3. 将最终 bit 归档到 `artifacts/bitstreams/<VERSION>/`，并补齐 `BUILD_INFO.md`。
4. 按 [`AGENTS.md`](AGENTS.md) 的 Candidate → 上板 → 测试结果流程建立 commit 与 tag。

## 版本管理约定（摘要）

- 主分支：`main`；远程：`origin`（Private 仓库）。
- `*_Runs/`、TD 日志、未归档 bit 不入库；`.al` / RTL / 约束 / SDC / IP 配置 / ROM 初始化文件 / 文档必须入库。
- 每个生成 bit 并准备上板的版本对应唯一 commit + tag；一个版本只验证一个主要变量。
- 失败或未采用的版本同样保留历史，不删除、不移动已公开 tag。
- 追溯链：`bit → Git commit → 源码 + 工程配置 + 约束 + 文档 + 构建信息 + 上板记录`。
