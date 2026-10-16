# 安路 PH1P35 实时图像处理竞赛项目

面向 2026 FPGA 创新设计竞赛安路赛道题目二，计划在 HX1P35A / PH1P35MDG324 上实现 SC520CS MIPI 采集、ISP 预处理、DDR2 帧缓存、HDMI 显示，以及 Sobel、卡通化和 INT8 YOLO-tiny 硬件检测，并联动 OSD、LED 和 WM8978 语音播报。

## 先从这里开始

| 你要找的东西 | 位置与用途 |
| --- | --- |
| **今天在哪里工作** | [work/ 工作入口](work/README.md)：算法模型；进入 TD 工程的命令；当前构建和实验记录 |
| **方案与计划如何验收** | [验收矩阵](docs/verification/acceptance-matrix.md)：阶段依赖、测试方法、通过条件与证据模板 |
| **项目完整步骤** | [新手项目手册](docs/setup/beginner-project-guide.md)：Goal 1 至 Goal 8 的操作和验收条件 |
| **打开 SC520 原图工程** | 在本目录运行 `pwsh -File .\scripts\open-td.ps1`；实际工程在 `.tools/td/work/lab_ex1_mipi_hdmi_sc520/` |
| **打开时钟修复副本** | 运行 `pwsh -File .\scripts\open-td.ps1 -ClockFix`；副本在 `.tools/td/work/lab_ex1_mipi_hdmi_sc520_clockfix/` |
| **最新 Goal 1 构建与上板状态** | [构建摘要](docs/build/goal-1-sc520-lab1/build-summary.md)、[上板记录](docs/evidence/goal-1/2026-10-02-bringup.md)；具体下载文件以记录中的路径和哈希为准 |
| **资料和规则** | [研究索引](docs/research/INDEX.md)、[资料缺口](docs/research/known-gaps.md)、[项目准则](AGENTS.md) |

原始厂商资料在根目录的 `SC520CS摄像头资料/` 和 `安路HX1P35A比赛文档2026/`，用于对照，不是日常编辑位置。`.tools/td/app/` 是 TD 程序，`.tools/td/work/` 是本机 TD 工作副本；这些目录不随 GitHub 仓库同步。项目自己的代码从 `work/` 找，构建与测量证据从 `docs/build/`、`docs/experiments/`、`docs/evidence/` 找。

## 当前状态

**2026-10-11 更新：** 已接收组员 `HX1P35A2026/` 并核对 11 个 TD 工程。资料已有原图、边缘、OSD 和卡通 RTL/位流；卡通版附带路由报告 Setup WNS -1574 ps，尚未通过时序，且发现算术、行缓存及握手问题。用户反馈原图已能实时显示，具体成功位流仍待绑定。本次完成资料同步与审计，未重建或下载。后续入口见 [组员工程同步记录](docs/setup/team-sync-2026-10-11.md)。

用户补充确认：**模式切换可以实现，但卡通化效果失败**。具体故障表现与对应位流待确认，尚未完成修复或独立上板复测。

以下为此前本机工作副本的状态：

本仓库目前保存赛题研究、来源与缺口记录、到板前准备包和软件参考模型。TD 6.2.1 已在本机项目目录下打开并构建 SC520CS Lab1 原图工程，生成 Bitstream。独立的时钟修复副本已完成软件构建；仍有普通告警待分类，且没有上板验收结果。SC500CS 样例仅用于资料参考和 TD 环境冒烟，不是本项目摄像头目标。YOLO-tiny、卡通化、LED、WM8978 和端到端延迟尚未因方案描述而视为已实现。

## 入口

- [延迟测量与 OSD 显示（三人分工·延迟显示）](docs/experiments/2026-10-16-latency-display.md)：接口契约见 [docs/architecture/latency-osd-interface.md](docs/architecture/latency-osd-interface.md)
- [项目执行准则](AGENTS.md)
- [研究资料索引](docs/research/INDEX.md)
- [赛题要求摘录](docs/research/competition/topic2-requirements.md)
- [资料缺口](docs/research/known-gaps.md)
- [到板前准备包](preboard/README.md)
- [官方资料包文件清单](preboard/06-package-manifest.md)
- [TD 本机环境与构建记录](docs/setup/tangdynasty.md)
- [从现在到提交的详细操作手册（新手版）](docs/setup/beginner-project-guide.md)
- [SC520CS 资料与验证边界](docs/research/camera/sc520cs.md)

打开本机 SC520CS Lab1 工程：

```powershell
pwsh -File .\scripts\open-td.ps1
```

打开时钟告警修复副本：

```powershell
pwsh -File .\scripts\open-td.ps1 -ClockFix
```

运行独立于板卡的算法参考模型：

```powershell
python .\work\models\reference_model.py --self-test
```

## 官方样例与复现边界

官方资料分享入口及文件名见 `preboard/06-package-manifest.md`。本机取得的官方压缩包和解压工程尚未整理成可移植、可公开分发的工程；原始 TD 工程含生成物和本机绝对路径。因此，本仓库当前不能单独重建 Bitstream。取得来源许可和完成工程审计后，再将必要的 RTL、约束和 IP 配置作为可复现工程纳入版本控制。

项目目标、阶段门和验收证据以 `AGENTS.md` 为准；未确认的硬件参数、模型接口和外设管脚记录在 `docs/research/known-gaps.md`。
