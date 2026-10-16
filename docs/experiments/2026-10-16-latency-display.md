# 实验记录：端到端延迟测量与 OSD 显示（2026-10-16）

## 1. 目标

按三人分工，完成「延迟显示」部分：在 FPGA 侧测量端到端延迟，并把结果显示在 HDMI 画面上，
满足赛题基本要求 4（OSD 叠加文字）与项目目标 5（端到端延迟有实测或可审计依据）。

## 2. 版本与环境

| 项 | 内容 |
|---|---|
| 源码版本 | 本仓库 `main` 分支 + 本记录对应的提交（见文末哈希） |
| 仿真器 | Icarus Verilog 14.0 (devel, s20260301)，`vvp` 同版本 |
| 仿真入口 | `python work/tests/run_latency_sim.py`（可选 `--full` 跑 1280×720 整帧） |
| 参考模型 | `work/models/latency_osd_model.py`（仅用标准库，整数/位精确） |
| 预览 | `python work/models/latency_osd_preview.py`（标准库写 PNG，无需 NumPy/Pillow） |
| 未使用 | Tang Dynasty（本环境无 TD）、开发板、摄像头、显示器 |

## 3. 交付物

| 类别 | 文件 |
|---|---|
| RTL | `work/rtl/latency/latency_meter.v`、`work/rtl/osd/text_overlay.v`、`work/rtl/osd/latency_osd.v` |
| 生成 RTL | `work/rtl/osd/char_rom.v`、`work/rtl/osd/osd_layout.vh` |
| 软件模型 | `work/models/latency_osd_model.py`、`work/models/latency_osd_preview.py` |
| 生成器 | `scripts/gen_char_rom.py`、`scripts/gen_osd_layout.py`（均支持 `--check`） |
| 测试 | `work/tests/tb_latency_meter.v`、`tb_text_overlay.v`、`tb_latency_osd.v`、`run_latency_sim.py` |
| 算法实验室 | `work/algorithm_lab/plugins/latency_osd.py`、`registry.json` 条目（`VISUAL_REVIEW_PENDING`） |

## 4. 步骤与预期

1. 用 `scripts/gen_char_rom.py` 从公开领域字体生成 Python 字形表与 Verilog 字符 ROM；
   `--check` 必须报告「up to date」。
2. 用 `scripts/gen_osd_layout.py` 从模型生成字符缓冲区布局；同样 `--check`。
3. 用 `run_latency_sim.py` 生成激励向量（由模型计算期望值），编译并运行 7 个用例：

| 用例 | 目的 |
|---|---|
| `meter_same_clock` | 同钟稳态测量，刻度为 10.5 拍（走分数累加器），校验 `lat_cycles`/`lat_ticks` |
| `meter_queue` | 源事件突发：队列顺序、深度溢出、粘滞标志 |
| `meter_edges` | 空队列出队、整数刻度周期、粘滞下溢 |
| `meter_cross_clock` | 24 ns 源时钟 vs 10 ns 视频时钟（翻转跨域），逐拍精确比对 |
| `overlay_small` | 128×64 光栅、4×1 面板：整帧哈希 + 首行每个像素 + `de` 三拍延迟 |
| `overlay_full_720p` | 1280×720 整帧回归（92 万像素） |
| `osd_small` | 集成：测量值、字符缓冲区 48 字节、整帧哈希、`err_clr` 时序 |

4. 用 `latency_osd_preview.py` 渲染面板预览与放大图，作为软件侧视觉验收材料。

## 5. 实际结果（`project`）

- 7 个用例全部 PASS，`cases: 7, failed: 0`。RTL 与模型在以下量上逐位一致：
  `lat_ticks`、`lat_cycles`、`lat_valid`、粘滞错误位、面板 48 字节字符、整帧输出像素哈希。
- `overlay_full_720p` 覆盖 921 600 个有效像素，输出哈希与模型一致。
- `osd_small` 中屏幕显示为 `LAT-F   1.90MS` / `LAT-P   0.18MS` / `FRM 00000004 E0`
  （仿真用 10.5 拍/刻度、2000 拍帧前置量、4 帧），与模型计算结果一致。
- 预览图：`work/output/latency-osd/preview.png`、`preview-panel.png`（1280×720，面板放大图）。
- 原始日志：`work/output/latency-osd/*.log`、汇总 `results.json`。

## 6. 已知限制与风险

- `unknown`：本环境没有 Tang Dynasty 与开发板，**没有**综合、布局布线、位流或上板证据；
  资源、时序和真实延迟都必须等 Goal 1/G2 之后补。任何「已实时」「已达标」的说法都不成立。
- `inferred`：`lat_ticks` 的分辨率是 10 µs，相对精确比值有不超过 ±1 个刻度（±0.01 ms）的量化；
  需要更高分辨率时用 `lat_cycles`（同钟用例逐拍精确比对）。
- `project`：跨域测量值包含 0–4 个目标时钟周期的非负偏移（同步器 + 边沿检测），
  物理上不可消除；文档已给出该预算。
- `project`：`osd_small` 中 `lat_cycles` 与模型相差 1 拍，原因是集成测试台的源事件脉冲按
  「时钟沿 + 1 ns」驱动，采样沿落在相邻拍；同钟与跨域的**精确**周期比对由
  `tb_latency_meter` 完成，集成用例只对周期量给 1 拍容差，并对屏幕量（刻度、字符、像素哈希）
  做严格比对。
- `unknown`：`work/algorithm_lab/plugins/latency_osd.py` 需要 NumPy，本环境的 Python 是
  OSS CAD Suite 自带的 MinGW 版 3.11，无法安装 PyPI 二进制轮子，因此**插件本身未在本机执行**；
  它调用的 `latency_osd_model.py`（纯标准库）与预览脚本已实际运行。上机前需在项目 Python 环境
  中打开 Algorithm Lab 复核，并**由用户**确认视觉效果后才可标记 `VISUAL_APPROVED`。

## 7. 结论与下一步

- 结论：延迟测量与显示部分在**仿真层面**完成并通过与黄金模型的逐位比对；屏幕布局有可运行的
  软件预览。状态：`RTL_SIM_PASS`（Stage E），未进入 Stage F/G。
- 下一步（退出条件）：
  1. 用户在 Algorithm Lab 或预览图上确认面板布局与数字格式（`VISUAL_APPROVED`）。
  2. 在 Goal 2 接口审计中确定 `sof_frame_src`、`sof_pipe_src`、`vs` 的真实来源，并确认它们
     所在时钟域；据此决定是否需要第三处 `latency_meter`。
  3. 用 `scripts/build-latency.py` 做 TD 单模块综合，记录 LUT/寄存器/ERAM 与 WNS；
     再并入显示链路（Stage F）。
  4. 上板后用示波器/计数器交叉验证绝对延迟（Stage G），并区分帧缓存延迟与流水线延迟。

## 8. 文件哈希（SHA-256 前 16 位）

| 文件 | SHA-256 |
|---|---|
| `work/rtl/latency/latency_meter.v` | `26da9df48ade19e7...` |
| `work/rtl/osd/text_overlay.v` | `dde47535c1ccfb82...` |
| `work/rtl/osd/latency_osd.v` | `50e1d1eb9e53d206...` |
| `work/rtl/osd/char_rom.v` | `3c540c28a308b93d...` |
| `work/rtl/osd/osd_layout.vh` | `4d9a7150b8df8d07...` |
| `work/models/latency_osd_model.py` | `4d7d05bb570b2d29...` |
| `work/models/font8x8_public_domain.py` | `a8cc24e9545bdfbc...` |
| `work/models/latency_osd_preview.py` | `e22502d7851046ee...` |
| `work/tests/tb_latency_meter.v` | `cf98d8b9907a9c75...` |
| `work/tests/tb_text_overlay.v` | `9aa14062125753c9...` |
| `work/tests/tb_latency_osd.v` | `2132cd580af9abb8...` |
| `work/tests/run_latency_sim.py` | `eb7e8e2833e8bcdc...` |
| `scripts/gen_char_rom.py` | `6beede34fc0e975f...` |
| `scripts/gen_osd_layout.py` | `96aac18753a677da...` |
