# OPEN_SOURCE — 开源算法与 RTL 参考索引

> **使用规则**  
> - 适配等级 A：算法或验证代码可参考，接口须适配 PH1P35。  
> - 适配等级 B：模块结构可参考，需改接口和时序。  
> - 适配等级 C：仅供协议/架构学习。  
> - D：弱相关。  
> 无许可证或许可证不明的仓库：仅用于研究思想，**禁止直接复制代码**。  
> 所有候选须在 `docs/research/sources.yaml` 中有对应条目，并标注精确 commit / tag。

---

## 1. 已评估候选（旧有）

这些条目已在 `sources.yaml` 中登记，信息来源为 2026-09-21 批量研究。

| 仓库 | 适配等级 | 相关阶段 | License | 主要用途 |
|---|---|---|---|---|
| [georgeyhere/fpga-video-processing](https://github.com/georgeyhere/fpga-video-processing) | B | G3、G4 | 待确认 | Line Buffer、FIFO、Sobel、HDMI 教学型工程 |
| [Galapple/Image-processing---Verilog](https://github.com/Galapple/Image-processing---Verilog) | B | G4 | 待确认 | 4 行缓存、3×3 窗口、Sobel |
| [olivier-le-sage/camera-filters](https://github.com/olivier-le-sage/camera-filters) | B | G3 | 待确认 | 定点颜色处理（VHDL） |
| [hdl-util/hdmi](https://github.com/hdl-util/hdmi) | C | G1、G6 | MIT | HDMI/DVI 时序参考 |
| [cliffordwolf/SimpleVOut](https://github.com/cliffordwolf/SimpleVOut) | C | G1、G6 | ISC | 视频输出 + Overlay 结构参考 |
| [FHDO-ICLAB/MIPI-CSI-2-HDMI-Bridge](https://github.com/FHDO-ICLAB/MIPI-CSI-2-HDMI-Bridge) | C | G1 | 待确认 | MIPI 链路架构学习 |
| [circuitvalley/mipi_csi_receiver_FPGA](https://github.com/circuitvalley/mipi_csi_receiver_FPGA) | C | G1 | MIT | MIPI 协议参考（Legacy） |
| [gatecat/CSI2Rx](https://github.com/gatecat/CSI2Rx) | C | G1 | 待确认 | CSI-2 协议参考（VHDL） |
| [hdl-util/mipi-demo](https://github.com/hdl-util/mipi-demo) | C | G1 | 待确认 | MIPI CCS 示例 |

---

## 2. 新增候选评估（2026-10-11 详细研究）

评估时间：2026-10-11；研究方法：访问仓库主页、README、LICENSE、代码结构。

### [amd/mini-isp](https://github.com/amd/mini-isp)

| 项目 | 值 |
|---|---|
| Stars | 数十至百量级 |
| 最近 commit | 2025–2026 活跃 (`inferred`) |
| License | **MIT** ✅ |
| 主要语言 | SystemVerilog 54% / Python 40% |
| 相关 Goal | G2、G3、G4 |
| 适配等级 | B（架构参考） |

**核心模块**：decompanding、BLC、digital_color_gain、Malvar-He-Cutler 拜耳解码、CCM、Gamma LUT + Python 仿真框架。  
**仿真环境**：完善 ✅ Makefile 驱动 Verilator + Python 双轨比对。  
**许可证风险**：低 — MIT，无 Copyleft。  
**PH1P35 适配**：不可直接移植（SystemVerilog + AMD UltraScale+ 原语 + XDC 约束）。ISP 算法（拜耳解码、CCM、Gamma）为纯数学逻辑，可用 Verilog 重写。Python 仿真框架完全可复用。  
**建议用途**：① 参考 Malvar-He-Cutler 拜耳算法原理（G2 ISP 基线）；② 仿照 Python ↔ Verilator 双轨验证框架方法论；③ 禁止直接导入 SystemVerilog 或 XDC。

---

### [georgeyhere/FPGA-Video-Processing](https://github.com/georgeyhere/FPGA-Video-Processing)

| 项目 | 值 |
|---|---|
| Stars | 数十 |
| 最近 commit | 约 2019–2020（已停止维护） |
| License | **MIT** ✅ |
| 主要语言 | Verilog |
| 相关 Goal | G3、G4、G6 |
| 适配等级 | B（架构参考） |

**核心模块**：OV7670 接口、异步 FIFO、RGB→灰度、BRAM Line Buffer（3 行）、3×3 窗口、Gaussian + Sobel、BRAM 帧缓存、HDMI 输出。  
**仿真环境**：无独立 testbench（教学型）。  
**PH1P35 适配**：Line Buffer + 3×3 + Sobel 算法逻辑可参考，结构平台无关；摄像头（DVP）和帧缓存（BRAM，640×480）不可用于本项目。Xilinx 原语须替换为安路原语。  
**建议用途**：① Line Buffer + 3×3 窗口架构（G4 核心依据）；② Sobel 梯度位宽/饱和/阈值设计参考；③ 摄像头/帧缓存部分不参考。

---

### [maojinxiang/FPGA-ANLU-National-First-Prize](https://github.com/maojinxiang/FPGA-ANLU-National-First-Prize)

| 项目 | 值 |
|---|---|
| Stars | ~15 以下 |
| 最近 commit | 2025 年（竞赛提交） |
| License | **❌ 无 License** |
| 主要语言 | Verilog |
| 相关 Goal | G1、G3、G4、G6 |
| 适配等级 | B/C（**严禁代码复制**） |

**核心模块**：多图像处理模式（原图/灰度/二值化/Sobel/浮雕/热力图/腐蚀/膨胀/形态学等）、Line Buffer 邻域窗口、以太网/HDMI/SDRAM 分离工程。  
**仿真环境**：无独立 testbench。  
**许可证风险**：**高 ⚠️ — 无 License 文件，默认版权归作者，禁止复制代码。**  
**PH1P35 适配**：同安路赛题最贴近参考，但摄像头为 OV5640（DVP，非 MIPI），帧缓存为 SDRAM（非 DDR2），无 YOLO。  
**建议用途**：① 仅阅读不复制；② 多图像处理模式系统分层和切换逻辑参考；③ 形态学算法思路参考。

---

### [Xilinx/finn](https://github.com/Xilinx/finn)

| 项目 | 值 |
|---|---|
| Stars | ~1,100 |
| 最近 commit | 2025–2026 持续活跃 |
| License | **BSD-3-Clause** ✅ |
| 主要语言 | Python / C++ / Vitis HLS / Verilog |
| 相关 Goal | G5、G7 |
| 适配等级 | C（思想借鉴） |

**核心价值**：Streaming Dataflow 架构（逐层流式串联）；INT8/QAT via Brevitas 量化；BN Folding（折叠 BatchNorm 进卷积权重，消除硬件除法器）；逐层 BRAM 缓存特征图。  
**仿真环境**：有（Jupyter + Python），但依赖 Vitis HLS + Vivado，不可在安路环境运行。  
**PH1P35 适配**：完整框架不可在安路 TD 运行。量化方法论（Brevitas QAT + BN Folding）和 Streaming Dataflow 架构思想对 G5 极有价值。  
**建议用途**：① 研读数据流推理架构设计；② 使用 Brevitas 做量化感知训练获取权重；③ 禁止用 finn 生成 IP 导入安路工程。

---

### [dog-qiuqiu/Yolo-FastestV2](https://github.com/dog-qiuqiu/Yolo-FastestV2)

| 项目 | 值 |
|---|---|
| Stars | ~941 |
| 最近 commit | 约 2022–2023 |
| License | **MIT（待直接确认）** ⚠️ |
| 主要语言 | Python |
| 相关 Goal | G5、G7 |
| 适配等级 | C（思想借鉴） |

**核心模块**：ShuffleNetV2 Backbone、LightFPN、解耦检测头（Obj/Cls/Reg）、YOLOv5 风格锚框匹配、PyTorch 训练脚本、ONNX 导出。  
**PH1P35 适配**：无 FPGA/RTL 代码，纯 PyTorch。ShuffleNetV2 的 Depthwise Convolution + Channel Shuffle 在纯 RTL FPGA 中效率低。**注意：本项目目标是 YOLO-tiny（不同架构）**，不可直接替代，但轻量化思路（250k 参数、解耦头、轻量 FPN）是裁剪参考。  
**建议用途**：① 轻量 YOLO 设计思路参考；② Python 推理改造为 Golden Model；③ PyTorch→ONNX→权重提取工具链参考。

---

## 3. 开源优先工作流（每次实现前执行）

1. 明确当前模块需求、接口（位宽、速率、时钟域）和硬件约束（BRAM/DSP 预算）。
2. 查询本文件及 `sources.yaml`，确认是否有已评估候选。
3. 若无，按需在 GitHub 检索 3–5 个候选，更新本文件。
4. 高 Star 不能代替接口适配、许可证和验证。
5. 选定候选后，先运行候选仓库原有测试或软件参考。
6. 评估 PH1P35 接口差异：原语替换、位宽、时钟、复位、握手。
7. 将候选及精确 commit hash 写入 `sources.yaml`。
8. 记录：算法思想借鉴 / 架构参考 / 许可证允许复用代码（三选一）。
9. 再开始移植或新写 RTL。

---

## 4. 许可证状态汇总（2026-10-11 更新）

| 仓库 | License | 可复用代码 | 来源 |
|---|---|---|---|
| `amd/mini-isp` | **MIT** ✅ | 是（属性标注后，须重写为 Verilog） | `reference` |
| `georgeyhere/FPGA-Video-Processing` | **MIT** ✅ | 是（平台无关算法逻辑部分） | `reference` |
| `Xilinx/finn` | **BSD-3-Clause** ✅ | 是（软件代码，非 RTL 直接使用） | `reference` |
| `Yolo-FastestV2` | **MIT（待直接确认）** ⚠️ | 待确认后决定 | `reference` |
| `maojinxiang/FPGA-ANLU-National-First-Prize` | **❌ 无 License** | **禁止复制代码** | `reference` |
| `hdl-util/hdmi` | MIT | 是 | `reference` |
| `cliffordwolf/SimpleVOut` | ISC | 是 | `reference` |
| `Galapple/Image-processing---Verilog` | **待确认** | 仅思想借鉴 | `reference` |
| 其余旧有条目 | 待确认 | 默认仅思想借鉴 | `reference` |

> [!CAUTION]
> `maojinxiang/FPGA-ANLU-National-First-Prize` 无 License，禁止复制任何代码，仅供阅读参考架构思路。  
> 许可证未确认前，所有代码仅用于研究思想，禁止直接复制粘贴进入比赛工程。

## 2026-10-12 实时视频卡通化专项：5 个 GitHub 参考

本轮只实现 Algorithm Lab 软件效果对比；硬件适配栏为结构判断，未代表 PH1P35 实测。评价同时看可复现入口、许可和逐像素流水线成本。没有复制任何仓库源码。

| 仓库 | 可复现与许可 | 卡通化可借鉴点 | FPGA 适配判断 |
|---|---|---|---|
| [opencv/opencv](https://github.com/opencv/opencv) | 成熟库、文档和测试；Apache-2.0 | 双边滤波、自适应阈值、色阶处理的软件画质基线 | 仅软件参考；双边滤波每像素多邻域权重与归一化，硬件成本高 |
| [opencv/opencv_contrib](https://github.com/opencv/opencv_contrib) | 扩展模块与示例；仓库 LICENSE 为 Apache-2.0，模块依赖仍须逐项核查 | ximgproc 边缘保留滤波等替代画质路线 | 暂不优先；相应滤波需另做定点化与吞吐评估 |
| [NhanPhamThanh-IT/Cartoonify-Images-OpenCV](https://github.com/NhanPhamThanh-IT/Cartoonify-Images-OpenCV) | Gradio、模块化 Python、示例；README 标注 MIT | K-Means 量化、双边平滑、局部阈值组合及交互对比 | K-Means 需全图迭代/聚类，不能直接逐像素流式移植；仅用于视觉方案 |
| [amd/mini-isp](https://github.com/amd/mini-isp) | ISP 代码、文档；MIT | 流式图像处理结构、软件与 RTL 验证方法 | 结构可借鉴；AMD 原语、IP 与约束不能直接用于安路 |
| [georgeyhere/FPGA-Video-Processing](https://github.com/georgeyhere/FPGA-Video-Processing) | RTL、testbench、演示说明；仓库未见 LICENSE，代码仅供阅读 | 3×3 Gaussian、Sobel、行缓存、阈值控制 | 运算结构可借鉴；Artix-7/OV7670/RGB444/640×480，与本项目接口不同 |

**本轮三效果**：A 保色亮度分层（较适合 FPGA），B RGB 色阶量化（较适合 FPGA），C 双边滤波+自适应描边（画质参考、暂不优先）。A/B 为本项目已有软件模型的参数变体，C 为现有 OpenCV 视觉模型；均不是直接移植上述仓库源码。用户选择前状态为 VISUAL_REVIEW_PENDING。

## 2026-10-12 Y1 三个目标检测原始仓库复核

固定 Commit、许可证、预训练权重、检测头、算子和硬件成本见 [Y1 实验报告](../experiments/2026-10-12-y1-fastestdet.md)。FastestDet@50473cd155cb088aa4a99e64ff6a4b3c24fa07e1 为 BSD-3-Clause，仓库有 COCO 80 类权重与 ONNX；Yolo-FastestV2@ac2a5e3060bff76dd1e45f9b921dd77bfbeb194d 仓库无许可证文件但有 COCO 权重；TinyissimoYOLO@19bea4bd1ea1e2c29a6ee6b14bd7494ce8c6ba25 仓库无顶层许可证和可直接使用的预训练权重，含基于 Ultralytics 的代码与 AGPL 声明。后两者只作结构参考。FastestDet 软件复现结果表明原模型直接移植 PH1P35 为 NO-GO；Y2 应先研究三类微型网络训练。

---

## 2026-10-12 深度评估：adamgallas/fpga_accelerator_yolov3tiny

本地路径：`reference/fpga_accelerator_yolov3tiny/`  
Commit: `6ba312bd220e67a987d3417bacd030db30b15770`  
License: **Apache-2.0** ✅  
适配等级：**B（核心计算模块与量化截断可直接参考，控制通路需解耦）**

### 1. 仓库背景与价值
- **来源**：2021年全国大学生集成电路创新创业大赛（DIGILENT杯）一等奖作品。
- **架构**：纯 Verilog 实现通用卷积硬件加速器，部署 YOLOv3-tiny（包含口罩识别、安全帽识别 Demo），基于 Angel-Eye / Going Deeper 等经典 FPGA CNN 加速器架构。
- **性能与指标**：INT8 量化，24K LUT，23K FF，40 BRAM36K，296 DSP48（基于 Xilinx ZU3EG），推理延迟 <50ms。

### 2. 对本项目 Goal 5 的核心参考价值
1. **纯 Verilog 核心算子实现**（位于 `vivado_prj/source/`）：
   - `cal_acc.v` / `module_acc_1x8.v`：累加与多通道处理。
   - `cal_addtree_int16_x9.v` / `cal_addtree_int18_x9.v`：3×3 卷积树状加法器网络（流水线化）。
   - `cal_mul_int8_x2.v` / `cal_mul_int8_x2_dsp.v`：INT8 乘法器结构，可方便替换为安路 DSP 原语或 LUT 乘法器。
   - `cal_scale.v` / `cal_scale_shift.v` / `cal_sat_int16_int8.v`：量化 Scale 与 Shift 截断饱和硬件模块，与定点量化数学模型完全对应。
   - `linebuffer_3x3_collect.v`：面向特征图卷积的 Line Buffer 结构。
   - `module_pool_kernel.v`：2×2 Maxpooling 单元。
2. **完整量化与权重导出工程**（`python_prj/`）：
   - 包含 PyTorch 训练、INT8 对称/非对称量化导出二进制权重文件的方法。

### 3. 安路 PH1P35 适配差异与风险
- **控制与调度**：原工程依赖 Zynq PS（ARM CPU）通过 AXI-Lite 配置寄存器并通过 AXI DMA 搬运特征图/权重。本项目为**纯 Verilog 无软核**系统，无法直接使用其 C 语言调度器；控制通路需改造成有限状态机（FSM）或紧凑型 Micro-Sequencer。
- **DSP 资源**：原工程使用了 296 个 DSP48，PH1P35 芯片硬件 DSP 资源较有限，需根据安路 DSP 数量裁减并行通道数（例如从 8 通道并行裁剪为更低并行度），或将部分乘法器映射至 LUT。

### 4. 2026-10-12 独立仿真后的适用范围修正

上文“可直接参考”“完全对应”仅表示值得研究，**不表示可直接移植或与本项目量化数学等价**。隔离 Icarus 验证见 [`../../work/yolo_fpga_feasibility/report.md`](../../work/yolo_fpga_feasibility/report.md)：原 `cal_addtree_int16_x9.v` 的 18 位和在 9 个全幅 INT8 正乘积时发生回绕；19 位隔离候选通过同一组 305 向量。乘法打包 372 向量、scale/saturation 352 向量的稳定算术结果与独立模型一致，但逐拍时序、安路 DSP 推断和网络量化尚未验证。Yolo-FastestV2 官方权重 352 输入的三类抽样效果较差，且 16 MAC/100 MHz 的理想卷积下界为 66.49 ms/帧；原版 30 fps 部署判 NO-GO。

## 2026-10-12 YOLOv8 软件效果基准复核

- 来源：[Ultralytics YOLOv8 官方文档](https://docs.ultralytics.com/models/yolov8/)，本机 ultralytics 8.4.175；许可 AGPL-3.0（官方同时提供商业授权）。本次仅使用官方预训练权重与现有 Python 包，不复制厂商 RTL。
- 权重：Ultralytics assets v8.4.0/yolov8m.pt，SHA-256 5d4a90cdc7a21786cc59cd19778e9eafff836df9e2da32524737c7ee6efe4fe5；代码运行实测 25,902,640 参数。
- 定位：PC Visual Reference，640 默认、960 对照；COCO 80 类推理，仅显示 bottle/cup/cell phone。固定公开60图及不重叠55图均改善检出，但仍有漏检/误报。不得称三类效果门通过。
- 硬件成本：仅按 INT8 每参数1字节已约25.9 MB，远大于既有视频工程名义空闲 ERAM；没有 PH1P35 整网综合/量化证据，不能作为直接上板模型。
- 证据：work/algorithm_lab/exports/yolo_quality_comparison/，实验报告 docs/experiments/2026-10-12-yolo-quality-comparison.md。

---

## 2026-10-13 安路 FPGA 工业视觉参考工程专项（已完整克隆与源码审计）

本地参考目录：`.tools/references/anlogic-vision/`（已受 `.gitignore` 保护，同步脚本见 `scripts/sync-anlogic-vision-references.ps1`，清单见 `.tools/references/anlogic-vision/inventory.json`）。

### 1. 六个安路参考项目综合对照表

| 项目编号与仓库 | 目标器件与板卡 | 核心工业视觉功能 | 源码完整度 | 验证证据等级 | 许可证状态 | 移植价值与主要使用边界 |
|---|---|---|---|---|---|---|
| **01 视频平台**<br>[lifeng0718/...](https://github.com/lifeng0718/Multifunctional-video-processing-platform) | PH1A90SBG484 | 四分屏、HDMI视频移动、旋转、多模式切换 | 完整 (带 TD 工程及位流) | `reference` (国一宣称，含 B 站演示) | **无 License** ⚠️ | 仅架构借鉴；器件为高端 PH1A90，不可直接移植其底层 DDR/PHY 原语 |
| **02 算法库**<br>[maojinxiang/...](https://github.com/maojinxiang/FPGA-ANLU-National-First-Prize) | EG4S20BG256 | 3×3 腐蚀/膨胀 (`morphology_process.v`)、Sobel、浮雕、Line Buffer | 完整 (带 TD 工程及位流) | `reference` (国一宣称，含 PPT 及上位机) | **无 License** ❌ | **严禁复制代码**；3×3 两级比较树形态学流水线适合作为纯 Python/Verilog 黄金模型参考 |
| **03 几何识别**<br>[InitialXE/...](https://github.com/InitialXE/Multi-Function-Image-Processing-PLAT) | EG4S20BG256 (SparkRoad) | 流式周长/面积统计 (`Perimeter_aera.v`)、Hu不变矩、手势判定 | 完整 (带 TD 工程) | `reference` (国二宣称，含实物照片) | **无 License** ⚠️ | 仅学习流式几何累加与面积/周长比计算；Hu矩定点除法器与高阶乘法极度消耗 DSP/LUT，需优化 |
| **04 多目标BBox**<br>[YuxiangJia111/...](https://github.com/YuxiangJia111/FPGA_ANLU_National_First_Prize) | **PH1P35MDG324** (同款) | 连通域多目标 BBox (`digit_multi_bbox.v`)、CNN 裁剪适配器 | 完整 (带 TD 工程) | **`FAIL` 明确记录** (`route_failure_notes.md`) | **无 License** ⚠️ | **重点避坑**：布线 3 小时失败（224KB ROM 展平逻辑门）；但 3×3 采样 Bitmap + 双 Bank 连通域状态机极具启发 |
| **05 BBox/模板匹配**<br>[zdxddmx/...](https://github.com/zdxddmx/anlogic_fpga_vision_udp) | EG4S20BG256 | 流式单目标 BBox 与蓝框叠加 (`bounding_box.v`)、运动检测、模板匹配 | 完整 (带 TD 工程) | `reference` (带上位机客户端) | **MIT** ✅ (部分子模块第三方版权) | **推荐核心参考**：单帧流式坐标极值更新 + 次帧边界绘框极简优雅，时序干净，适合直接作为 F1/F4 基准 |
| **06 规范化基线**<br>[Aurora-520/...](https://github.com/Aurora-520/anlogic-ph1p35-vision) | **PH1P35MDG324** (同款) | 解耦架构、无乘法器 BT.601 Y、自适应二值化、双BRAM Sobel、3位色阶卡通化、Logo OSD | 完整规范 (带 TD 工程、构建与验证文档) | `project` / `reference` (规范工程) | **无独立 License** ⚠️ | **最高规范基线**：平台层与应用层彻底解耦，倒数乘法代替除法器，无乘法器 Y 提取，直接契合本项目 Goal 3/4 |

---

### 2. 深入源码技术分析与架构卡片

#### 01_video_processing_national_prize (lifeng0718)
- **Commit**: `c8c0c1864d24c7ea3d6e9da5bc51d5b04a00a6ea`
- **目标器件**: Anlogic PH1A90SBG484 (PH1A 系列 90K 逻辑单元，BGA484)
- **核心模块**: `four_channel_video_splicer.v`, `down_samping_2x2.v`, `design_top_wrapper.v`
- **数据流与架构**: 针对多路视频源（双目、HDMI、SFP、以太网）进行 2×2 降采样后通过 DDR 仲裁写入对应显存区块，读取时根据模式控制信号产生全屏或四分屏显示时序。
- **移植风险与边界**: 器件逻辑量和引脚数远超 PH1P35MDG324，且 DDR 控制器配置为 PH1A 专用 IP，不可直接移植；其视频多模式切换的控制状态机（FSM）与降采样流式处理结构具备高参考价值。

#### 02_image_algorithm_library (maojinxiang)
- **Commit**: `0672ee8ddff84385683afbbd799b09839f2405be`
- **目标器件**: Anlogic EG4S20BG256 (内置 2MByte SDRAM)
- **核心模块**: `morphology_process.v` (膨胀/腐蚀), `sobel_process.v`, `line_buffer.v`, `emboss_process.v`
- **数据流与架构**:
  - `morphology_process.v`: 级联 `line_buffer.v` 获取 3×3 邻域窗口。第一级流水线通过 `max2`/`min2` 组合函数计算每行最大值与最小值；第二级流水线再求 3 行极值，输出 1 拍延迟的 `dilate_out` 与 `erode_out`。
  - 内置行计数器与边界控制，完全流式处理，无跨时钟域停顿。
- **移植风险与边界**: **该仓库无开源许可证**，严格禁止直接复制源码。其 3×3 极值树算法非常典型，应在 PC 端 Python Algorithm Lab 验证等价数学后，由本项目从零编写等价流式 Verilog。

#### 03_geometry_recognition (InitialXE)
- **Commit**: `25ab494f8845dbf15565e8f05d64f94b9d63cd2a`
- **目标器件**: Anlogic EG4S20BG256 (SparkRoad)
- **核心模块**: `Perimeter_aera.v`, `Hu_Invariant_moment.v`, `Dilation_Detector.v`, `Caculate_Sobel.v`
- **数据流与架构**:
  - `Perimeter_aera.v`: 在设定窗口 `(150<=x<=450, 50<=y<=350)` 内，统计 Sobel 边缘像素计数作为周长 `Perimeter`（24位计数器），统计膨胀二值前景像素作为面积 `Aera`。
  - 帧尾触发安路 IP `Divider` 计算 `Aera*10 / Perimeter` 作为形状特征比值，用于区分手势/形状。
- **移植风险与边界**:
  - `Hu_Invariant_moment.v` 包含 7 个不变矩的大量高位宽定点乘加与归一化除法，在 EG4/PH1P 容易造成严重的 DSP 和时序阻塞；
  - 工业分拣推荐采用其 `Perimeter_aera.v` 的轻量统计思路（长宽比 + 面积 + 周长比），摒弃复杂的全图 Hu 矩。

#### 04_ph1p35_bbox_cnn (YuxiangJia111) — 重点避坑与多目标启发
- **Commit**: `60c11a2d9b59d0e8e9f9824e60b9b1841baf68ef`
- **目标器件**: **Anlogic PH1P35MDG324** (与本项目完全一致)
- **核心模块**: `digit_multi_bbox.v`, `bbox_gray_downsampler.v`, `bbox_cnn_adapter.v`, `doc/route_failure_notes.md`
- **数据流与架构**:
  - `digit_multi_bbox.v`: 针对 1280×720 图像，按 3×3 步长降采样得到紧凑二值 Bitmap（减少 BRAM 占用）；
  - 采用双 Bank 内存交替工作（Ping-Pong）：一帧采集写入 Bank A，下一帧由状态机 `PR_SCAN` → `PR_MATCH` → `PR_PUBLISH` 扫描连通块并动态合并相邻行 Run，输出多达 8 个目标的 `(x_min, x_max, y_min, y_max)`。
- **重大教训与避坑记录**:
  - `doc/route_failure_notes.md` 披露：TD 布局布线运行 3 小时未结束而放弃；
  - 根本原因分析：`cnn/database.v`（224 KB）用巨大的 Verilog `case` 组合逻辑存储网络权重，综合器将其展开为数十万门组合网表，彻底压垮路由引擎；另外 Demosaic 128-bit 总线与 AWB 接口未对齐导致画面三分裂。
  - **核心启示**：特征图与权重必须严格通过 BRAM IP/MIF 实例化，严禁在 Verilog 源码中硬编码大型常量查找表！

#### 05_vision_bbox_template (zdxddmx) — 单目标 BBox 推荐实践
- **Commit**: `5595d8368e279af8cee6e5b2abb559060138780d`
- **目标器件**: Anlogic EG4S20BG256
- **核心模块**: `import/dual_cam/bounding_box.v`, `import/other/motion_border_overlay.v`
- **许可证**: **MIT** (顶层明确授权)
- **数据流与架构**:
  - `bounding_box.v`: 像素流入时，若当前像素为二值化前景（`idata_r == 1`），单周期动态更新 `x_minr = min(x_minr, x)`, `x_maxr = max(x_maxr, x)`, `y_minr`, `y_maxr`；
  - 帧场同步 `vsync` 边界将极值锁存至 `x_min/x_max/y_min/y_max` 供下一帧使用；
  - 在下一帧视频流出时，当坐标落在线框边界（如 `hcout == x_min || hcout == x_max`）时，强制替换为蓝色像素 `24'h0000ff`；
  - 同时输出中心点坐标 `coor_data = (x_max + x_min) >> 1`。
- **移植价值**: 逻辑仅消耗数十个寄存器，无 BRAM 压力，WNS 极高，是 F1/F4 工业单目标检测框的最佳实现范例。

#### 06_ph1p35_vision_baseline (Aurora-520) — 架构典范与零乘法器实现
- **Commit**: `3ccd79f97107041dc7d6470521c80ab5be4148cf`
- **目标器件**: **Anlogic PH1P35MDG324** (与本项目完全一致)
- **核心模块**: `rtl/app/vision_pipeline.v`, `rtl/isp/pixel_algorithm.v`, `rtl/overlay/logo_overlay.v`
- **数据流与架构**:
  - 遵循与本项目极其一致的高内聚低耦合规范：将平台底层封装为 `vendor_lab1_core.v`，业务逻辑封装为 `vision_pipeline.v`；
  - `pixel_algorithm.v`:
    1. 灰度提取：无乘法器移位展开实现 BT.601 `Y = (77R + 150G + 29B) >> 8`；
    2. 自适应二值化：全帧累加亮度，利用倒数乘法 `146 / 2^27`（移位加法）计算均值，彻底消除了硬件除法器；
    3. Sobel 与卡通化：双 BRAM 行缓存，3 位色彩量化截断 + 边缘黑色融合（`24'h101010`），流水线只有 2 级延迟，时序极其干净；
  - `logo_overlay.v`: 从片上 ROM 读取安路官方 Logo 并在 HDMI 画面右上角稳定叠加。
- **移植价值**: 解决了本项目 Goal 3/4 的核心算子优化（无除法、无乘法器灰度、自适应阈值），应作为首选参考。

---

## 4. 延迟测量与 OSD 显示（2026-10-16，G6-L）

| 仓库 | 适配等级 | 相关阶段 | License | 主要用途 |
|---|---|---|---|---|
| [dhepper/font8x8](https://github.com/dhepper/font8x8) | A | G6 | Public Domain（文件头声明，源自 IBM 公开领域 VGA 字体） | 8×8 位图字体表，用于生成 `work/rtl/osd/char_rom.v` 与 `work/models/font8x8_public_domain.py` |

- **Commit**: 未固定分支（2026-10-16 取 `master` 的 `font8x8_basic.h`），上游文件原样保存在
  `work/models/third_party/font8x8_basic.h`，SHA-256
  `49D8DF366296B203CA3211BC0672CF2A762135BF12710735B6292756B19DFFD5`。
- **用法**: 只取 U+0020–U+007E 共 95 个字形，每个字符 8 个行字节；`scripts/gen_char_rom.py`
  把每 8 个字节打包成一个 64 位常量并按行做变量部分选择，生成 ROM 与 Python 表，二者由同一上游
  推导，因此软件预览与 RTL 的字形必然一致。
- **位序**: 字节 bit0 为最左像素（与上游渲染顺序一致），已由模型自检断言（`glyph_rows("A")[0] == 0x0C`）。
- **未使用**: 本项目没有引入该仓库的其他文件，也没有移植其渲染/绘制代码。
- **时基方案为自研**: 延迟测量没有采用第三方工程，方法（翻转跨域 + 单域时间基 + 分数累加刻度）
  记录在 `docs/architecture/latency-osd-interface.md`。

---
