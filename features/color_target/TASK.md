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
          tb/{tb_color_target, tb_color_target_overlay, tb_color_target_track,
              tb_color_target_chain}.v、
          run_color_target{,_overlay,_track,_chain}.py、
          INTERFACE.md、INTEGRATION.md、README.md、GITHUB_RESEARCH.md、本文件。
  验收：run_color_target.py 17/17（--full 18/18）＋两条结构断言；
        run_color_target_overlay.py 10/10；run_color_target_track.py 11/11；
        run_color_target_chain.py 396 拍逐拍比对通过（三级链路端到端）。
```

## 未完成 / 待办

| # | 事项 | 归属 |
|---|---|---|
| 1 | Issue 登记或追认本任务 | 人类负责人 / MAIN |
| 2 | `INTERFACE.md` 第 10 节的 6 项待确认 | MAIN |
| 3 | 资源与时序的**实测**结果（当前只有估计） | MAIN 接入 TD 后 |
| 4 | T3 标注：**几何部分（框线 + 中心十字）已完成并自检；坐标文字待 MAIN 用统一字库呈现** | TARGET 已完成几何 / 文字归 MAIN（§4.5） |
| 5 | T4 跟踪状态机与防抖：**已完成并自检（11/11）**；`ACQ_FRAMES` / `LOST_FRAMES` / `MAX_JUMP` 的取值待有实板噪声数据后确定 | TARGET 已完成结构 / 参数待实板 |
| 6 | **结果与显示帧的对齐**：实测若把 overlay 直接接在 track 上，本帧最后 1~2 个像素会用上刚发布的新结果（框在帧末跳变）。需 MAIN 在帧边界寄存一级（协议 §4.3） | MAIN |
| 7 | `GITHUB_RESEARCH.md` 的 commit / License 核实 | 仅在将来需要**采用代码**时才需要 |
