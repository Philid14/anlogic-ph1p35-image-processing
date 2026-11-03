# TARGET 外部实现调研记录（颜色目标检测）

范围：FPGA 上的颜色目标检测 / 分割 / 包围框 / 质心统计的公开实现。
本文件放在 `features/color_target/` 内——按协议 §3，共享的 `docs/GITHUB_REFERENCE_RESEARCH.md`
由 MAIN 维护，队友不写。

> **历史条目与本次核查范围**
> §1–§4 为早期调研存档，当时由公开网页检索完成、没有逐文件直读源码，以下限制只适用于这些历史条目。
> **2026-10-17 新核查见 §5**：已固定六个仓库的 commit，读取许可和列出的相关源码。
> 本次后续方案以 §5 及 `research/ROADMAP.md` 为依据，不把早期未核实条目升级为已验证来源。
> 对历史 §1–§4：
> - **所有 commit SHA 均未核实**，链接只固定到仓库/文件页，不声称是某个 revision；
> - **所有 License 状态均未核实**；
> - 本轮的采用范围**只有设计思路**，**未复制任何第三方代码、参数或寄存器值**。
>
> 这与 `docs/GITHUB_REFERENCE_RESEARCH.md` 的记录粒度要求（固定 commit + 核实 License）
> 有差距。若后续要**采用代码**，必须先补上 commit 与 License 核实；本轮不采用代码，
> 所以该缺口不阻塞当前实现。

---

## 1. 公开实现的通行流水线

多份公开资料描述的流水线高度一致：

```
RGB/YCbCr 输入 → RGB→HSV 转换 → HUE 阈值分割 → 形态学去噪 → 包围框或质心 → 跟踪/控制
```

## 2. 逐项对照

| # | 来源 | 参考内容 | 对本项目的用处 | 采用范围 |
|---|---|---|---|---|
| 2.1 | MIT 6.111 2019 team01（[报告](https://fpga.mit.edu/videos/2019/team01/report.pdf)） | SystemVerilog 顶层 `object_detection` 打包 `hsv_threshold` + 腐蚀 + 膨胀 + 质心；**腐蚀/膨胀用一维核与小寄存器**以省延迟与存储；质心每 16 个样本平均以抑抖 | 支持"HSV 阈值 + 形态学"的流水线；"用一维核降低存储"是将来做去噪时的低成本选项 | **思路**。未复制代码；报告非代码仓库，许可不适用 |
| 2.2 | MIT 6.111 Fall 2016（[报告](http://web.mit.edu/6.111/www/f2016/projects/lolzhang_Project_Final_Report.pdf)） | 在 NTSC 视频上加 `hsv_threshold`，按键/拨码在线调阈值；讨论了噪声/饱和度问题与固定流水线延迟 | 支持"hue 阈值要可在线调整"，本模块因此把 `HUE_HALF_WIDTH_DEG` 等做成参数 | **思路** |
| 2.3 | MIT 6.111 2013 team05（[报告](https://fpga.mit.edu/videos/2013/team05/report.pdf)） | 用颜色索引（红/黄/绿/蓝）而非完整 HSV；由像素数决定是否输出质心 | 支持"按像素数门限判目标存在"——本模块的 `MIN_COUNT` 即此思路 | **思路** |
| 2.4 | Massey 大学 2005（[论文 PDF](https://www-ist.massey.ac.nz/dbailey/sprg/pdfs/2005_IVCNZ_422.pdf)） | 颜色分割后**构造包围框**包围该色类全部像素，给出位置/尺寸/朝向；讨论实时约束与流水 | 直接支持"包围框包围全部匹配像素"的 T2 定义 | **思路**；论文非代码仓库 |
| 2.5 | IET HLS 视频处理（[PDF](http://www.ece.iit.edu/~eoruklu/IIT/Publications_files/IET%20HLS%20Video%20processing.pdf)） | Virtex-5 平台上 RGB→HSV→分割→**boundary box**→跟踪；给出 HLS C 代码与综合结果 | 与本项目 T2 目标最接近的公开描述 | **思路**；未复制 HLS 代码 |
| 2.6 | UTP 2013 学位论文（[PDF](http://utpedia.utp.edu.my/id/eprint/15302/1/2013%20-Optimized%20Architecture%20Design%20And%20Implementation%20Of%20Object%20Tracking%20Algorithm%20On%20FPGA.pdf)） | 对比表列出"基于颜色阈值的分割"实现规模：798 LE、114 688 memory bits、768×288、25 fps、27 MHz | 提供一个**量级参照**：颜色分割本身不大，但若加整帧缓存会吃掉大量存储 | **量级参照**；不同器件与工艺，不能直接搬数字 |
| 2.7 | `HYDRA-GUY-RUM/Motion-Sensor-and-video-filter-system-using-FPGA`（[Color_Detector_FSM.v](https://github.com/HYDRA-GUY-RUM/Motion-Sensor-and-video-filter-system-using-FPGA/blob/master/Color_Detector_FSM.v)） | Verilog 颜色检测 FSM：把像素各通道与阈值比较后输出方向信号 | 与查询最接近的 GitHub RTL 实例 | **仅列为查询结果**。**未核实 License**，未读完整仓库，未复制任何代码 |
| 2.8 | `lp6m/imageDetectionHW2`（[仓库](https://github.com/lp6m/imageDetectionHW2)） | HLS 的 HOG+BGRHSV+SVM 红灯检测，Ultra96 >142 fps | 说明"学习类方法"在 FPGA 上另有路线 | **仅列为查询结果**；HLS 路线、未核实 License、与本题 T1 前提不同 |
| 2.9 | 任意 FPGA 视觉跟踪教学文章（[示例](https://kaifayun.com/article/weixin_42550597/1183163)） | 优化过的 RGB→HSV Verilog 与"像素坐标累加求质心" | 说明质心法的常见做法 | **仅列为查询结果**。教学文章，不属于可引用许可来源 |

## 3. 本轮实际采用的设计判断

只采用了**思路**，实现全部独立完成：

1. **用 HSV/hue 而不是 RGB 阈值**（早期依据 2.1/2.2/2.5）。协议 §2.2 禁止为迁就检测
   去改主线 AWB/曝光。补充数学边界：无量化/截断的统一通道增益可保持色相比值，
   但低彩度噪声、饱和与 AWB 的不同通道增益会破坏这一条件，不能称为绝对光照不变。
2. **包围框而不是质心作为中心输出**。公开资料两类都用（2.4 用框、2.1/2.3 用质心），
   而协议 §2.2 明确要求"包围框中心不是像素质心"并要区分，因此本模块只实现框中心，
   不计算质心。
3. **按像素数门限判存在**（依据 2.3 的思路），即 `MIN_COUNT`。
4. **形态学去噪采用"一维核 + 小寄存器"这一低成本方向**（依据 2.1），但**本轮不实现**，
   留给 T4 在有实板噪声数据后再定，避免凭猜测引入变量。

## 4. 与主工程的边界

- 不采用任何第三方 RTL，因此不涉及"替换安路厂商 IP"的问题（协议 §"GitHub 外部参考"禁止）。
- 2.6 的规模数字只能当量级参照；本项目的资源必须以 TD 真实综合报告为准（协议 §4.5）。
- 若将来要**采用代码**：必须先补齐 commit 固定与 License 核实，并在本文件登记，
  再走协议 §5.2 的流程。当前没有任何待补的代码引用。

## 5. 2026-10-17：固定版本、许可与源码核查

研究基线：`172815e97587c19a63863c27c1c86bc8e85353bd`。
逐文件 URL、blob SHA 和下载内容 SHA-256 见
[`来源清单`](research/2026-10-17-source-manifest.json)。核查了许可文件及相关源码，未审计仓库全部依赖/权重。
以下仅采用架构/方法启发；未复制第三方代码、参数表或寄存器配置进工程。

| Repository / Owner | 固定 commit | 许可核查 | 读过的关键文件 | 参考判断与是否采用 |
|---|---|---|---|---|
| [Topi-ab/linkruncca](https://github.com/Topi-ab/linkruncca/tree/a84d236c6e67b3ca511d4dfaa3a11ff605f057de) | `a84d236c6e67b3ca511d4dfaa3a11ff605f057de` | `COPYING.txt`；README/RTL 标为 LGPL v3 或以后，GitHub 标识 LGPL-3.0 | `src/verilog/LinkRunCCA.v`、`equivalence_resolver.v`、`feature_accumulator.v` | 1PPC 单遍游程/等价统计架构；思路参考，未移植 |
| [Xilinx/Vitis_Libraries](https://github.com/Xilinx/Vitis_Libraries/tree/3ab1ecd20cf338b3f8f2824fdfeee115f3398889) | `3ab1ecd20cf338b3f8f2824fdfeee115f3398889` | `vision/LICENSE.txt` Apache-2.0；所读头文件一致 | `vision/L1/include/imgproc/xf_erosion.hpp`、`xf_dilation.hpp` | 行窗口与打包像素边界处理；不能直接替换安路 RTL/IP |
| [FoundationVision/ByteTrack](https://github.com/FoundationVision/ByteTrack/tree/d1bf0191adff59bc8fcfeaa0b33d3d1642552a99) | `d1bf0191adff59bc8fcfeaa0b33d3d1642552a99` | `LICENSE` MIT | `yolox/tracker/byte_tracker.py` | 强候选优先、低置信补救；提出本项目类比假设，非原算法 FPGA 移植 |
| [noahcao/OC_SORT](https://github.com/noahcao/OC_SORT/tree/8462e7e729a93ccd3bd995c0a79a890336cb3a0b) | `8462e7e729a93ccd3bd995c0a79a890336cb3a0b` | `LICENSE` MIT | `trackers/ocsort_tracker/ocsort.py` | 历史观测辅助关联；仅列下一步帧结果层研究 |
| [facebookresearch/EdgeTAM](https://github.com/facebookresearch/EdgeTAM/tree/7711e012a30a2402c4eaab637bdb00a521302c91) | `7711e012a30a2402c4eaab637bdb00a521302c91` | `LICENSE` Apache-2.0 | `sam2/modeling/sam2_base.py` | 跨帧记忆的启发；未装模型、未引入 NN 或整帧缓存 |
| [yformer/EfficientTAM](https://github.com/yformer/EfficientTAM/tree/abcd061ebd3cc6e7527d152d75b890126aaa53f6) | `abcd061ebd3cc6e7527d152d75b890126aaa53f6` | `LICENSE` Apache-2.0 | `efficient_track_anything/modeling/efficienttam_base.py` | 轻量编码/记忆研究参照；无 PH1P35 部署或资源结论 |

另外回读了两个出版方/会议原始资料：

- [Real-Time FPGA Implementation of Parallel Connected Component Labelling for a 4K Video Stream](https://link.springer.com/article/10.1007/s11265-021-01636-4)，2021，DOI `10.1007/s11265-021-01636-4`，出版页标明 CC BY 4.0。关注 §4.4/§5.4 的合并冲突与暂停/消隐依赖，排除直接套用。
- [Efficient Track Anything，ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Xiong_Efficient_Track_Anything_ICCV_2025_paper.html)。用于核对正式版本；不把手机/GPU 指标外推为本 FPGA 性能。

本次产物见 [`research/ROADMAP.md`](research/ROADMAP.md)：硬门槛、方法比较、创新假设与淘汰条件。
另有独立 CPU 掩膜对照：22 模板×4 种子、10 方法、880 评价；保留了弱桥、细目标、冷启动歧义
及粗网格失败。该模型尚未证明任何候选可用于 4PPC RTL 或真实视频，不改变生产默认配置。

后续执行：候选 A 的独立 RTL 与两行缓存机制见 [SUPPORT3.md](SUPPORT3.md)。它按本项目的
二值数学定义自行实现，没有移植上述第三方代码；开源对照中发现的细目标和噪团限制仍保留。
本机 TD 官方原语仅作为只读仿真依赖，文件哈希及综合/仿真状态列于对应验证目录。
