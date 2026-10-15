# `features/color_target/` —— 颜色目标检测（TARGET）

对应赛题 **扩展二、进阶二**；对应协议 `TEAM_PROTOCOL_V1` 的 TARGET 角色与 §2.2 分阶段任务。
当前完成 **T1（参数化颜色分类）+ T2（匹配像素数 / 包围框 / 包围框中心 / 帧身份）+ T3（框线与中心十字的覆盖请求）**
的独立模块与自检；T4（动态跟踪与防抖）未开始。

> ⚠️ **状态口径（协议 §5.3.4、§6 要求如实区分）**：
> 本功能**独立模块完成、模拟事件验证通过**。**未接入主线、未生成 bit、未上板。**
> 不得对外表述为"已整机完成"或"进阶二已完成"。

---

## 1. 目录

| 路径 | 内容 |
|---|---|
| `rtl/color_classify.v` | 单像素颜色分类（HSV 扇区法，无除法器） |
| `rtl/color_target_detect.v` | 检测顶层：4 路并行分类 + 帧内统计 + 帧末原子锁存 |
| `rtl/color_target_overlay.v` | 标注模块（T3）：框线 + 中心十字的覆盖请求，纯组合、不加流水级 |
| `model/ref_color_target.py` | 位精确 Python 参考模型（与检测 RTL 逐拍等价） |
| `model/ref_color_target_overlay.py` | 标注的逐像素参考模型（单独成文件，与检测解耦） |
| `tb/tb_color_target.v` | 检测自检台；另带两条不依赖期望值的结构断言 |
| `tb/tb_color_target_overlay.v` | 标注自检台（纯组合，无需时钟） |
| `run_color_target.py` | 检测自检驱动：生成激励 → 仿真 → 与模型逐行比对 |
| `run_color_target_overlay.py` | 标注自检驱动 |
| `INTERFACE.md` | 接口说明（状态：**接口草案**，待 MAIN 确认） |
| `GITHUB_RESEARCH.md` | 外部实现调研记录（本目录内，不写共享 `docs/`） |
| `TASK.md` | 开工记录（等价任务说明；本机无法创建 GitHub Issue） |

## 2. 跑自检

```bash
python features/color_target/run_color_target.py            # 15 个用例
python features/color_target/run_color_target.py --full     # 追加一个完整 1280x720 帧
python features/color_target/run_color_target.py --sim modelsim
```

仿真器优先用 Icarus Verilog；本机没有安装时自动回落到 ModelSim（`--sim` 可强制指定）。
若 PATH 上的 `python` 是 Windows 应用商店占位符，请改用真实解释器。

最近一次结果：**15/15 通过**（`--full` 为 16/16），覆盖：

| 用例 | 覆盖点 |
|---|---|
| `flat_white_no_target` | 无目标：`present=0` 且坐标清零 |
| `single_beat_all_red` | `sof` 与 `eof` 同拍的**单拍帧** |
| `count_below_min` | 门限边界：3 < `MIN_COUNT`(4) → 不判存在 |
| `red_rect_bbox` | 包围框与**包围框中心**（非质心）精确值 |
| `corner_origin` | 贴 `x=0 / y=0` 的边界 |
| `xmax_at_1279` | `xmax` 达 11 位上限 1279（同时也是"eof 那拍必须计入"的判据） |
| `aborted_frame` | 中断帧：`valid=0` 且字段清零 |
| `truncated_then_ok` | 无 `eof` 的截断帧不发布，不污染下一帧 |
| `orange_out_of_hue` | hue 出窗（橙）不计入 |
| `low_chroma` / `dark_red` | 彩度/亮度下限（粉、暗红）不计入 |
| `green_as_class1` / `green_not_counted_as_red` / `blue_as_class2` | `TARGET_CLASS` 真的生效，不是写死红色 |
| `frame_id_propagation` | 跨帧 `session/frame` 身份对应正确 |
| `full_1280x720` | 完整帧尺寸（`--full`） |

自检台还带两条不依赖期望值的结构断言：`O_result_ready` 必须恰好对应当拍 `valid&&eof`；
未发布期间结果寄存器必须保持不变（§4.3 原子发布要求）。

### 2.1 标注模块（T3）自检

```bash
python features/color_target/run_color_target_overlay.py
```

最近一次结果：**10/10 通过**。逐像素比对（每例约 0.3k–27k 个采样点），覆盖：

| 用例 | 覆盖点 |
|---|---|
| `no_result` / `result_invalid` | 无目标或结果无效时不得有任何覆盖 |
| `box_and_cross_basic` | 框线四边 + 十字两臂 + 框内非描边处不覆盖 |
| `box_at_origin` | 框贴左上角，检验 `in+THICK-1` 与下界饱和 |
| `box_at_far_corner` | 框在 `x=1279 / y=719`，检验上界不溢出 |
| `box_smaller_than_thick` | 框小于线宽（`max-THICK+1` 会为负）时的饱和 |
| `cross_at_edge` | 十字贴在 `x=0 / y=0`，臂下界饱和到 0 |
| `degenerate_single_pixel_box` | 框退化为单像素 |
| `thick_cross` / `thick_box` | `CROSS_THICK=3` / `BOX_THICK=1` 的参数化 |

**T3 第一版只做几何，不做文字。** 坐标文字需要字库，而协议 §4.5 规定字库与字体由 MAIN
统一、且不得改写已有字库；因此文字由 MAIN 用它自己的字库、按本模块给出的框坐标呈现。
这是明确边界，不是遗漏。

**本模块不决定遮挡优先级。** §4.5 规定 Logo/主线状态 > 性能文字 > 目标框/十字，
合成顺序由 MAIN 的 mixer 执行；本模块不做遮挡规避，也不绑定按键/引脚。

## 3. 为什么这样设计

**为什么用 HSV 扇区法而不是 RGB 阈值**：协议 §2.2 要求"不修改主线 AWB/曝光来迁就检测"，
而 RGB 阈值随增益与白平衡漂移；hue 与亮度无关。公开资料的通行做法也是 HSV（见
`GITHUB_RESEARCH.md`）。

**为什么不需要除法器**：设 `C = max-min`，在"R 为最大通道"的扇区内有
`|hue 偏移| = 60°·|G-B|/C`，因此 `|hue 偏移| ≤ W` 等价于 `60·|G-B| ≤ W·C`。
把 `60/W` 预合并成一个 Q8 常数斜率后，整式只剩常数乘法（TD 用 CSD 移位加法分解）、
减法与比较——**无除法器、无 DSP 乘法器**，也避免引入厂商 divider IP。

**为什么不做形态学滤波**：T1 的前提是"单个主要颜色目标、背景较易区分"；在还没有实板
噪声数据时凭猜测加滤波器会引入无法归因的变量。去噪与防抖按协议属 **T4**，留到有实测
数据之后再做。

## 4. 资源估计（**估计值，未经综合验证**）

按逻辑逐项估算：4 路分类器约 400 LUT6（其中含 4 个 `8×10` 常数乘法，走 LUT 的 CSD
分解）；累加与比较约 80–150 LUT6 + 约 20 位进位链；结果锁存约 120 个触发器。

| 项 | 估计 | 说明 |
|---|---|---|
| LUT6 | **约 600–900** | 未综合，误差可能 ±40% |
| FF | 约 150–250 | |
| ERAM | **0** | 不新增任何缓存（协议 §4.5 要求） |
| DSP | **0** | 常数乘法不占 DSP |

**这是估计，不是实测**。协议 §4.5 要求提供"实际结果"与"最大工作频率依据"，需要由 MAIN
把本模块加入 TD 工程后跑综合才能给出，本角色不擅自改 TD 工程输入列表（§3）。模块在
59 MHz 观察时钟下为纯组合 + 单级寄存器，看起来余量充足，但**未经时序验证，不作承诺**。

## 5. 已知限制

完整清单见 `INTERFACE.md` 第 6 节，其中对外必须原样转述的是：

1. **整帧所有匹配像素合成一个包围框**，不分离多目标；画面中两块同色区域会被并进同一个框。
2. **无形态学/游程滤波**，孤立高饱和噪点会拉大包围框（T4 处理）。
3. **中心是包围框中心，不是像素质心**。
4. 强偏色下阈值可能失效，需重新评估 `HUE_HALF_WIDTH_DEG`，**不得改主线 AWB/曝光**。
5. **未接入主线、未上板。**
