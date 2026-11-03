# A1：类别判据与完整结果包标签一致性

用户授权：本地隔离分支最小 A1 修复；禁止 push/merge/MAIN 改动；其他生产 RTL 先提案。
评审基线 `b4565a152458d251d694d850a48058a325d66bfb`，PR #2 仍指向该提交。
工作分支 `codex/target/a1-integration-audit`。原始 PROJECT_REVIEW.md 的哈希与核对信息见 `baseline.json`。

## 缺陷及最小修复

分类器只有 TARGET_CLASS=1/2 时选择绿/蓝，其余值回退红色；原检测器和 mask_stats
直接发布 TARGET_CLASS[1:0]。例如参数 7 对红帧命中，却输出 class=3。
严重程度 P2：默认 0/合法 1/2 不受影响，但违反已声明的越界回退语义。

只在 `color_target_detect.v` 与 `color_target_mask_stats.v` 增加相同编译期有效类别常量，
并用于结果标签；未改变分类器、封装、support3、track、文字、门限、端口或时序控制。
两个 Python 模型的发布标签同步采用已有分类回退语义。

## 独立硬期望

`run_target_class_contract.py` 的 GOLD 是人工列出的 12 组参数→期望类别表，
含 0/1/2、3/4/5/6/7、负值和 32bit 有符号边界；不调用生产模型产生 RTL 期望。
每组送 8×3 纯红/绿/蓝/白及完整 abort 共五帧，检查：

- 单独分类器 hit；原检测器；新封装旁路与启用过滤；直接二值统计器。
- session/frame、valid/present、class/count、框及中心的完整公开结果。
- 白帧无目标、abort 无效时数据字段清零；整块纯色保留 24 像素。
- 直接统计器测试使用显式掩膜，独立于 RGB 分类，三个有掩膜帧均应采用有效类别标签。

共 240 个结果包。修复前正确硬期望下 **5/12** 参数组通过、7 组失败，退出 1；
修复后 **12/12** 通过，退出 0。比较两轮实际输出：仅 **42 个结果包的 cls 字段**改变，
其他字段与分类 hit 完全相同。见 `a1-before.json`、`a1-after.json`、`a1-differences.json`。
两个 Python 模型也分别与同一硬期望核对，12/12 通过，不反过来充当 RTL oracle。

首轮测试台曾错误地期望 abort 让组合分类器 hit=0。abort 实际仅使帧统计无效；
该期望已订正并重新跑完整负对照。`a1-harness-draft.txt` 保留首轮 2/12 输出，
不能用它计数 RTL 缺陷；正式修复前证据为 `a1-before.txt/json` 的 5/12。

## 现有回归

| 检查 | 本轮实际结果 |
|---|---|
| 分类数学与参数夹取 | 40/40 组合，39079 像素，8/8 等价性 |
| 原检测器含 1280×720 | 25/25 |
| detect→track→overlay | 396 拍通过 |
| 六尺寸×两模式 RGB 回放 | 12 轮、2013324 输入时钟、7760408 接收像素、179 结果、178 跟踪消费、39928 显示查询 |
| 同轮旧检测器对照/复位取消 | 87 组一致，5 帧取消逐项列账 |

179/178 差异来自结果发布后、track 下一拍消费前发生复位，未将其解释为未追踪的丢包。
新旧语义仅改变非法类别标签，生产默认阈值与过滤关闭状态保持原样。
各命令 stdout、汇总及 LF 归一化源码哈希保存在本目录；完整每模式输出在本轮本机输出目录。

## 复现

在仓库根目录执行，`$py` 为真实 Python、`$msim` 为 ModelSim 安装目录，输出目录须不存在：

```powershell
& $py -B -X utf8 -u features/color_target/run_target_class_contract.py --sim modelsim --msim $msim --rtl-root <基线RTL目录> --out <before目录>
& $py -B -X utf8 -u features/color_target/run_target_class_contract.py --sim modelsim --msim $msim --out <after目录>
& $py -B -X utf8 -u features/color_target/run_target_class_contract.py --models-only --out <models目录>
& $py -B -X utf8 -u features/color_target/run_color_classify.py --sim modelsim --msim $msim
& $py -B -X utf8 -u features/color_target/run_color_target.py --full --sim modelsim --msim $msim
& $py -B -X utf8 -u features/color_target/run_color_target_chain.py --sim modelsim --msim $msim
& $py -B -X utf8 -u features/color_target/run_color_target_replay.py --full --sim modelsim --msim $msim --out <RGB目录>
```

本机解释器：`C:/Users/Kelinna/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`；
ModelSim：`D:/altera/14.1/modelsim_ase/win32aloem`；
原始输出：`C:/Users/Kelinna/Documents/Codex/2026-10-16/AnlogicTrack2/outputs/integration-audit-2026-10-18/`。
基线 RTL 是从 b4565a1 Git 对象提取的五个依赖文件，未覆盖历史证据。

## 边界

本轮未运行 TD，不新增综合/P&R/bit/板测结论。标签常量折叠后的资源和时序影响未经重新综合测量。
此前 918/1224 LUT 是独立 RGB 观测架 gate 结果，不是整机 P&R 或完整 TARGET 增量。
A2 及 MAIN 相关生产 RTL 均未修改。真实相机效果、观测超时、CDC/缓存/显示集成仍未关闭。
