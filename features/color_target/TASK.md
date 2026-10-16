# 开工记录（等价任务说明）

按协议 §5.2："AI 未取得 GitHub Issue 创建权限时可先提交等价任务说明"。本机无 `gh`、无法
创建 Issue，故以本文件等价记录，**等待人类负责人确认后再继续 T3**。

```text
Role / GitHub username:
  TARGET / Enoshima Junko <enoshimajunko521@gmail.com>
  （注：本机 git 身份与仓库历史作者 Philid14 不同，提交作者会显示为 Enoshima Junko）

Issue / 人类确认来源:
  无 Issue（本机无 gh）。来源为队友在 2026-10-15 对话中确认的角色指派：
  "颜色目标检测"，并要求按 TEAM_PROTOCOL_V1 全力推进。
  **这是对话内的指派，不是仓库内登记的 Issue**；请负责人补登记或追认。

目标与不包含的内容:
  目标：T1 参数化颜色分类（首个演示目标默认红）+ T2 匹配像素数 / 包围框 /
        包围框中心 / session+frame 身份 + T3 框线与中心十字的覆盖请求
        + T4 跟踪状态机与参数化防抖，均做成独立可自检模块。
  不包含：T3 第一版不做坐标**文字**（字库按 §4.5 归 MAIN）；T4 不做多目标分离与
        目标 ID 关联；不做神经网络；不新增整帧缓存；不改主线任何文件。

Base branch / Base SHA:
  origin/main / c42168e26026425660f2a6f51eec76b04c85eea0

Task branch:
  codex/target/color-target-detect-v1

允许修改范围:
  仅 features/color_target/**。未触碰主工程、共享测试、根 AGENTS/README、docs/、
  TD 工程输入、约束、sensor/DDR/HDMI/时钟。

Interface version / 状态:
  TEAM_PROTOCOL_V1 §4.2（输入观察流）/ §4.3（输出结果）；
  本模块接口状态 = 接口草案，待 MAIN 确认（见 INTERFACE.md 第 10 节的 6 项待确认）。

依赖MAIN或另一个角色的输入:
  1) 观察点的实际位置，且必须是风格化输出之前的彩色流；
  2) I_data 的实际 lane 排列与字节序是否与 §4.2 一致；
  3) sof 由 MAIN 从现有提前帧通知转换而来；
  4) 结果的 CDC 归属（本模块单域，跨域由 MAIN 适配）；
  5) T3 需要 MAIN 分配显示叠加区域并统一字库。
  以上未落实期间，只能报告"独立模块完成 / 模拟事件验证通过"。

交付物与验收条件:
  交付物：rtl/{color_classify, color_target_detect, color_target_overlay, color_target_track}.v、
          model/{ref_color_target, ref_color_target_overlay, ref_color_target_track,
                 ref_color_target_chain}.py、
          tb/{tb_color_classify, tb_color_target, tb_color_target_overlay,
              tb_color_target_track, tb_color_target_chain}.v、
          run_color_classify.py、run_color_target{,_overlay,_track,_chain}.py、
          INTERFACE.md、INTEGRATION.md、README.md、GITHUB_RESEARCH.md、本文件。
  验收：run_color_classify.py 40/40 参数组合 / 39079 像素 + 8 条参数等价性
          （期望值按数学判据独立计算）；
        run_color_target.py 23/23（--full 24/24）＋两条结构断言；
        run_color_target_overlay.py 10/10 + 5 条夹取等价性；
        run_color_target_track.py 21/21；
        run_color_target_chain.py 396 拍逐拍比对通过（三级链路端到端）；
        render_color_target_frames.py 192010 拍 / 768000 像素逐像素比对通过 + 10 帧 PNG。
```

## 未完成 / 待办

| # | 事项 | 归属 |
|---|---|---|
| 1 | Issue 登记或追认本任务 | 人类负责人 / MAIN |
| 2 | `INTERFACE.md` 第 10 节的 6 项待确认 | MAIN |
| 3 | 资源与时序的**实测**结果（当前只有估计） | MAIN 接入 TD 后 |
| 4 | T3 标注：**几何部分（框线 + 中心十字）已完成并自检；坐标文字待 MAIN 用统一字库呈现** | TARGET 已完成几何 / 文字归 MAIN（§4.5） |
| 5 | T4 跟踪状态机与防抖：**已完成并自检（21/21）**；`ACQ_FRAMES` / `LOST_FRAMES` / `MAX_JUMP` 的取值待有实板噪声数据后确定（合法范围已明确为 1..255 / 1..255 / ≥0，编译期夹取） | TARGET 已完成结构 / 参数待实板 |
| 6 | **结果与显示帧的对齐**：实测若把 overlay 直接接在 track 上，本帧最后 1~2 个像素会用上刚发布的新结果（框在帧末跳变）。需 MAIN 在帧边界寄存一级（协议 §4.3） | MAIN |
| 7 | `GITHUB_RESEARCH.md` 的 commit / License 核实 | 仅在将来需要**采用代码**时才需要 |
| 8 | 审查意见 ①②③ 的三处修复与回归：**已完成**（`README.md` §6 记录了复现、影响面与"修复前 RTL 喂给新回归确认会失败"） | TARGET 已完成 / 待 Philid14 复审 |
| 9 | 整机接口对齐、统一 OSD 合成顺序、资源与时序实测、上板效果 | **MAIN 集成确认**（§4.5 / §5.3.4） |
| 10 | 参数健壮性收敛（所有越界参数编译期夹取 + 等价性断言）与链路渲染验收：**已完成**（`README.md` §7、§2.5） | TARGET 已完成 / 待 Philid14 复审 |
| 11 | **像素级去噪**（默认关闭的可选模块）：目前最大的功能性缺口。渲染量化了后果——40 个孤立噪点把框从 60×60 撑到 309×209，且被 HOLD 保持若干帧。**滤波器形态需要实板噪声数据才能定**，建议等 MAIN 的实拍样本 | 待实拍数据；TARGET 可先做机制 |
