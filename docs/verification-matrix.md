# 全系统模块验证矩阵 (Verification Matrix)

本矩阵严格遵循工程事实，标记各项功能的当前真实状态：
- `VERIFIED_ON_BOARD`：真板硬件已验证通过
- `BUILD_PASS`：TD 综合/实现/Bitstream 生成通过
- `SIM_PASS`：RTL 仿真与 Golden Model 对齐通过
- `IMPLEMENTED_UNVERIFIED`：已编写 RTL，但尚未通过完整验证
- `PLANNED`：已完成架构设计，尚未编码
- `BLOCKED`：受硬件、工具或资料缺口阻塞

---

## 1. 基础视频与显示链路 (底座)

| 功能模块 | 代码位置 | 验证级别 | 证据出处与说明 |
|---|---|---|---|
| **SC520CS MIPI RX** | `uics520_cfg/`, `uiisp_beta/` | `VERIFIED_ON_BOARD` | 用户实测已出实时画面；TD QoR Setup WNS > 1ns |
| **Demosaic (拜耳转RGB)**| `isp/demosaic_4x_2_0/` | `VERIFIED_ON_BOARD` | 组员工程与 TD 实现验证 |
| **DDR2 控制器** | `ph1p35_ddr/` | `VERIFIED_ON_BOARD` | 720p@30fps 帧缓存闭环 |
| **HDMI 输出** | `video_out.v`, `pll_hdmi.v` | `VERIFIED_ON_BOARD` | 稳定输出 720p 视频时序 |

---

## 2. 主线：YOLO-tiny 智能视觉系统

| 功能模块 | 代码位置 | 验证级别 | 证据出处与说明 |
|---|---|---|---|
| **卡通化流式滤波** | `work/rtl/video_cartoon_luma.v` | `BUILD_PASS` / `SIM_PASS` | iverilog 5329 周期无缝通过；TD 6.2 路由 Setup WNS 1389ps |
| **Python 黄金参考模型** | `work/models/cartoon_luma_reference.py` | `SIM_PASS` | 逐像素与 RTL 严格位对齐 |
| **YOLO 硬件可行性论证** | `docs/yolo-feasibility.md` | `SIM_PASS` | 算力与存储定量推导，确立片上 Micro-CNN 路线 |
| **轻量卷积加速单元 (PE)** | `work/rtl/yolo/` | `PLANNED` | 下一阶段攻坚核心 |
| **OSD 智能检测框叠加** | `work/rtl/osd/` | `PLANNED` | 基于坐标与置信度动态划线与安路 Logo 融合 |

---

## 3. 备用线：传统工业视觉检测系统

| 功能模块 | 代码位置 | 验证级别 | 证据出处与说明 |
|---|---|---|---|
| **四像素并行色彩二值化** | `color_detect_96.v` | `IMPLEMENTED_UNVERIFIED` | 原始 Lab3 RTL 完整保留，需补充 Testbench |
| **实时包围盒与面积统计** | `color_detect_96.v` | `IMPLEMENTED_UNVERIFIED` | 动态统计 xmin/ymin/xmax/ymax 及面积 |
| **形态学滤波 (开闭运算)**| `fallback/morphology/` | `PLANNED` | 规划消除孤立噪点 |
| **工件尺寸公差判定** | `fallback/defect_eval/` | `PLANNED` | 判定合格/异常并输出控制信号 |

---

## 4. 延迟测量与 OSD 显示（2026-10-16 新增）

| 功能模块 | 代码位置 | 验证级别 | 证据出处与说明 |
|---|---|---|---|
| **延迟测量（帧延迟 / 流水线延迟）** | `work/rtl/latency/latency_meter.v` | `SIM_PASS` | 4 个用例覆盖同钟稳态、突发溢出、空队列下溢、24 ns 跨钟；`work/output/latency-osd/*.log` |
| **字符叠加面板（3 拍固定延迟）** | `work/rtl/osd/text_overlay.v` | `SIM_PASS` | 8192 像素 + 921 600 像素（720p）整帧哈希、首行逐像素、`de_out` 三拍延迟 |
| **延迟格式化与顶层** | `work/rtl/osd/latency_osd.v` | `SIM_PASS` | 测量值、48 字节缓冲区、整帧哈希、`err_clr` 时序，见 `docs/evidence/goal-6/2026-10-16-latency-osd-sim.md` |
| **字符 ROM（生成）** | `work/rtl/osd/char_rom.v` | `SIM_PASS` | 由公开领域字体生成；`--check` 保证与上游一致；模型自检断言位序 |
| **软件黄金模型与预览** | `work/models/latency_osd_model.py`、`latency_osd_preview.py` | `SIM_PASS` | `--self-test` 通过；预览 PNG 使用标准库写出 |
| **Algorithm Lab 插件** | `work/algorithm_lab/plugins/latency_osd.py` | `VISUAL_REVIEW_PENDING` | 需 NumPy，本环境未执行；等待用户视觉确认 |
| **TD 综合 / 时序** | — | `BLOCKED` | 本环境无 TD；入口 `scripts/build-latency.py --td`（当前只做 iverilog 精细检查） |
