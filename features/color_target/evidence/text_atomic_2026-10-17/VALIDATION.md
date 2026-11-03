# 文字更新一致性修复：独立验证

日期：2026-10-17。角色：TARGET。修复基线：`f540f7b50c3e3906cafa04b614aafebe4da41fa8`。

## 问题与约定

旧实现三轮读取实时输入并依次更新数字，状态/明暗直接读取输入，导致同一时刻输出混合结果。
修复使用输入快照及暂存数字，完成后原子发布数字、状态与明暗。转换 70 拍；忙时变化可合并，
最新稳定输入最多 140 拍可见。复位清空事务和显示。端口不变。

原子性限定在同一时钟的字段组；显示帧边界、帧身份及 CDC 仍由 MAIN 适配。

## 仿真

本机显式选择 ModelSim ASE 14.1。以下命令从仓库根目录运行；仿真器路径通过
`--msim <目录>` 或 `COLOR_TARGET_MSIM` 指定，不依赖任何个人安装路径。

```text
python features/color_target/run_color_target_text_updates.py --sim modelsim
python features/color_target/run_color_target_text_overlay.py --sim modelsim --font real
python features/color_target/render_color_target_frames.py --sim modelsim --font real --out <输出目录>
```

| 检查 | 实际结果 |
|---|---|
| 新动态回归，11/10 与 14/12 位宽 | 7962 拍，0 不一致 |
| 同一动态回归指向基线 RTL（`--rtl <旧文件>`） | 按预期失败，4036 个不一致采样；2926 个数字字段混合采样 |
| 既有真实字库回归 | 28/28 用例，307078 像素一致 |
| 既有链路渲染（含真实字库） | 192010 拍、768000 像素一致，76160 个文字覆盖像素，10 帧合成画面 |

动态测试只读公开字形/颜色端口。数值期望用十进制格式化计算；完整输出必须属于一次输入快照，
并检查最新稳定值的收敛和中途复位。旧实现首个混合数字例子：
`RED X0000 Y000` / `N123456 TRACK `，输入从零组变为 count=123456、X=789、Y=321。

## TD 独立 gate 综合

工具：TD V6.2.168116，与仓库 `.al` 版本一致。
器件：`ph1_35p.db / PH1P35MDG324 / speed 3`。默认参数，人工 10 ns 测试时钟。

在空的输出目录运行，Tcl 路径请用正斜杠：

```text
td_commands_prompt.exe <仓库绝对路径>/features/color_target/tools/synth_text.tcl
```

通过 `COLOR_TARGET_RTL=<旧文件>` 可在另一个空目录运行相同设置的基线对照。
检查日志中 `PASS_TEXT_SYNTH`，以及生成的 `text_gate.area` 和 `text_gate.ts`。

| gate 资源 | 基线 | 修复后 | 增量 |
|---|---:|---:|---:|
| LUT | 232 | 282 | +50 |
| reg | 148 | 194 | +46 |
| ERAM | 0 | 0 | 0 |
| DSP | 0 | 0 | 0 |

原始报告：[基线](before.area.txt)、[修复后](after.area.txt)。顶层为文字模块，字库通过输入端口提供。
该独立顶层的 122 个逻辑端口没有绑定板卡引脚，工具报告 `SYN-6021 CRITICAL-WARNING`；
本检查仅综合，不生成 bit，也不通过设置忽略引脚约束去生成 bit。

以上资源为 gate 阶段结果，未做布局布线；10 ns 是测试约束，不能作为最大频率或整机时序结论。
主线接入、统一 OSD、route 后时序、bit 与真实上板均未验证。
