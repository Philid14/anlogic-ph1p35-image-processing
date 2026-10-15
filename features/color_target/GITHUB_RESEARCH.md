# TARGET 外部实现调研记录（颜色目标检测）

范围：FPGA 上的颜色目标检测 / 分割 / 包围框 / 质心统计的公开实现。
本文件放在 `features/color_target/` 内——按协议 §3，共享的 `docs/GITHUB_REFERENCE_RESEARCH.md`
由 MAIN 维护，队友不写。

> ⚠️ **本轮方法与可信度声明（请勿省略）**
> 本轮由**公开网页检索**完成，**没有**逐文件直读源码，因此：
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

1. **用 HSV/hue 而不是 RGB 阈值**（依据 2.1/2.2/2.5）。直接原因是协议 §2.2 禁止为迁就
   检测去改主线 AWB/曝光，而 hue 与亮度无关。
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
