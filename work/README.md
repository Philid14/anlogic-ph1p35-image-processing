# 日常工作区

从仓库根目录开始。这里放**我们自己编写、可以纳入 Git 的实现**；厂商 TD 工程仍在 `.tools/td/work/`，因为它含本机路径和生成文件，移动会影响现有工程引用。

| 要做什么 | 打开哪里 |
| --- | --- |
| 接续组员原图/卡通工作 | [2026-10-11 同步记录](../docs/setup/team-sync-2026-10-11.md)：导入目录、源码差异、时序失败、位流哈希及待修复项；原包在 `../HX1P35A2026/` |
| 看当前该做哪一步 | [新手项目手册](../docs/setup/beginner-project-guide.md) |
| 修改或运行算法参考模型 | [models/reference_model.py](models/reference_model.py)；测试图 [models/step.pgm](models/step.pgm) |
| 改 SC520 Lab1 的 FPGA 工程 | 在仓库根目录运行 `pwsh -File .\scripts\open-td.ps1`；实际工程在 `../.tools/td/work/lab_ex1_mipi_hdmi_sc520/td_project/camera_to_dsi_display.al` |
| 看时钟修复候选工程 | 运行 `pwsh -File .\scripts\open-td.ps1 -ClockFix`；改动只在独立工作副本中 |
| 看本次构建结果与上板证据 | [构建摘要](../docs/build/goal-1-sc520-lab1/build-summary.md)、[实验记录](../docs/experiments/goal-1-baseline.md)、[上板记录](../docs/evidence/goal-1/2026-10-02-bringup.md) |
| 查接口和算法定义 | [接口契约](../preboard/02-interface-contract.md)、[算法契约](../preboard/03-algorithm-contract.md) |
| 做延迟测量与 OSD 显示（三人分工中「延迟显示」部分） | [接口契约](../docs/architecture/latency-osd-interface.md)、[实验记录](../docs/experiments/2026-10-16-latency-display.md)、[仿真证据](../docs/evidence/goal-6/2026-10-16-latency-osd-sim.md)；跑 `python work/tests/run_latency_sim.py`、看预览 `python work/models/latency_osd_preview.py` |

在仓库根目录运行软件模型：

```powershell
python .\work\models\reference_model.py --self-test
python .\work\models\reference_model.py --input .\work\models\step.pgm --out-dir .\work\output --threshold 128 --edge-threshold 128
```

`work/output/` 是本机生成结果，已被 Git 忽略。将来新增的自有 RTL、仿真和样例可在 `work/` 下按模块建目录；目前还没有可宣称通过硬件验证的自有 RTL。修改 TD 厂商基线前先记录原始构建结果，按 [AGENTS.md](../AGENTS.md) 的阶段门推进。
