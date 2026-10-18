# 诊断证据索引

2026-10-18，精确QUALITY候选基线b64daf39af09980621adb1138df1674a8501ea09。
无真实RGB连续帧；所有算法实验输入均合成。正式RTL、约束、历史bit不变。

- `rtl_full_summary.json`：最终 `python -X utf8 tests/run_edge_stability_diag.py --full` 完整退出0；实际RTL断言输出、期望图像分级SHA、15个历史bit SHA。
- `rtl_summary.json`：开发早期Edge-only检查点（早于AWB/历史独立回归加入入口），不是完整最终验收摘要；保留原结果，不据此代替full结果。
- `historical_rtl.txt` / `isolated_rtl.txt`：独立历史版本与NMS/连接隔离检查的先行原始输出；最终full入口也重新执行。
- `integration_bubble_failure.txt`：首次完整流非四拍边界气泡导致打包失败的原始数值、重现条件和范围；不是修复成功记录。
- `source_sta_audit.json`：61个实际工程入口哈希、四版commit和8个共同源码blob、实际Ignored约束事实。
- `model_summary.json`：固定图一致性指纹、三种微扰反例、AWB选样敏感性；不等于板上统计。
- `temporal_metrics.csv`：240条同ROI/因果中心补偿后的跨帧最终指标；包括白点数量与两种归一化口径。
- `stage_metrics.csv`：220条同级跨帧变化（灰度、Gaussian、梯度、NMS、强/弱、hop1..4）；不同级之间不直接比较未补偿坐标。
- `mechanisms.png`：经检查的合成反例图，B/C是中间级输入，不能当原始RGB照片。

Python3.12.14、Icarus12.0、NumPy2.3.5、Pillow12.3.0、Matplotlib3.11.2。
TD未运行，资源与STA只读取历史路由归档。真实控制流采样、物理IP、CDC偏斜、硬件注入/冻结AWB和长稳全部待测。
