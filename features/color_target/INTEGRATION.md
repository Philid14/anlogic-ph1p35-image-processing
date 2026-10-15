# `features/color_target/` 接入说明（给 MAIN）

一页读完即可接线。接口的完整定义在 [`INTERFACE.md`](INTERFACE.md)，逐项自检与边界在
[`README.md`](README.md)。本页只讲**怎么接、参数怎么给、期望什么行为、资源大概多少**。

> 状态：**独立模块完成、模拟验证通过。未接入主线、未生成 bit、未上板。**
> 接入与整机验收属 MAIN（协议 §5.3.6、§6）。

---

## 1. 交付物与自检命令

| 模块 | 文件 | 自检 |
|---|---|---|
| 颜色检测（T1/T2） | `rtl/color_classify.v` + `rtl/color_target_detect.v` | `python features/color_target/run_color_target.py`（17/17，`--full` 18/18） |
| 标注（T3） | `rtl/color_target_overlay.v` | `python features/color_target/run_color_target_overlay.py`（10/10） |
| 跟踪与防抖（T4） | `rtl/color_target_track.v` | `python features/color_target/run_color_target_track.py`（11/11） |
| 三级链路 | 上述三者的组合 | `python features/color_target/run_color_target_chain.py`（396 拍逐拍比对） |

自检台优先用 Icarus Verilog；本机没装时**自动回落到 ModelSim**（也可 `--sim modelsim` 强制）。
若 PATH 上的 `python` 是 Windows 应用商店占位符，请改用真实解释器。

## 2. 怎么接

接线代码见 [`INTERFACE.md` §7](INTERFACE.md)。三条要点：

1. **detect 是观察者，不是通路**：把观察点（风格化之前的彩色流）**扇出**给它即可，
   它不产生 `ready`、不串联像素、不施加反压。§4.2 的 lane 映射与 `sof` 来源需 MAIN 核实。
2. **track 接 detect 靠 `O_result_ready` 这一个 strobe**，其余字段同名直连。
3. **overlay 接 track 只要两行**：`I_result_valid = I_target_present = track.O_show`。

## 3. 参数与建议初值

| 参数 | 模块 | 建议初值 | 说明 |
|---|---|---|---|
| `TARGET_CLASS` | detect | `0`（红） | 0=红 1=绿 2=蓝；已自检证明可切换 |
| `HUE_HALF_WIDTH_DEG` | detect | `30` | hue 半宽。**取 30 时斜率恰为 2 的幂，乘法退化成移位，不占 LUT**；调小更严、调大更松 |
| `C_MIN` | detect | `24` | 彩度下限，同时滤白灰与暗部噪声 |
| `V_MIN` | detect | `32` | 亮度下限 |
| `MIN_COUNT` | detect | `64` | 帧内命中像素数门限 |
| `ACQ_FRAMES` | track | `3` | 连续几帧确认。**待实板噪声数据后定** |
| `LOST_FRAMES` | track | `15` | 连续几帧判彻底失去；越小框消失越快 |
| `MAX_JUMP` | track | `0`（关闭） | 跳变门限。**默认不要开**——开了会让快速移动的目标被判丢 |
| `BOX_THICK` / `CROSS_ARM` | overlay | `3` / `12` | 框线粗细与十字半臂长 |

**不要为了迁就检测去改主线 AWB / 曝光**（协议 §2.2）。hue 法本身抗亮度变化；若白平衡把红目标
整体推成橙色系，正确的动作是通知 TARGET 重新评估 `HUE_HALF_WIDTH_DEG`（协议 §4.2），不是改主线。

## 4. 期望行为

- **每帧一个结果**：detect 在 `eof` 后 1 拍发布；track 在那一拍消费。
- **状态机**：`SEARCH → ACQ → TRACK → HOLD`。HOLD 期间**框保持上一次被接受的那一帧**，
  所以演示时框不会闪；连续丢满 `LOST_FRAMES` 帧才归 SEARCH、框消失。
- **中止帧不改状态**：`O_result_valid=0` 的帧被跳过。**丢一帧结果不等于目标消失**。
- **会话变化清零**：新 session 首帧按 SEARCH 重判，不把旧会话状态带过去（§4.1）。
- **结果里带的身份是"上一次被接受"的那一帧**（`O_out_session_id/frame_id`），不是当前帧。
  MAIN 若要判断"这个框是不是本帧的"，应比较该身份与当前帧身份。

### ⚠️ 结果与显示帧的对齐（MAIN 必须处理）

实测（`run_color_target_chain.py`，396 拍逐拍比对）：detect 的结果在 `eof` 之后 1 拍才发布，
track 在那一拍更新，而 overlay 是纯组合的会**立刻**改用新结果。所以若把 overlay 直接接在
track 上，**本帧最后 1~2 个像素会用到刚发布的新结果，框会在帧末跳一下**。

要完全避免：MAIN 在**帧边界**把结果寄存一级再喂给 overlay —— 这正是协议 §4.3 的
"读出时使用匹配结果；不能把上一帧的框悄悄标成当前帧检测结果"。

## 5. T3 的文字部分：本模块已提供哪些字段

T3 的任务描述含"坐标的覆盖请求"，但**坐标文字需要字库，而 §4.5 规定字库与字体由 MAIN 统一维护、
不得改写已有字库**。所以本模块只输出几何（框线 + 中心十字），文字由 MAIN 用它自己的字库渲染。
MAIN 需要的数据本模块都已经给出，不必再算：

| 想显示的内容 | 取自哪个信号 |
|---|---|
| 包围框中心坐标 | `track.O_out_center_x` / `O_out_center_y`（或 `detect.O_center_x/center_y`） |
| 包围框范围 | `track.O_out_xmin/xmax/ymin/ymax` |
| 匹配像素数 | `track.O_out_count` |
| 当前状态文字（SEARCH/ACQ/TRACK/HOLD） | `track.O_track_state`（2 位，直接译码） |
| 这个框属于哪一帧 | `track.O_out_session_id` / `O_out_frame_id` |
| 颜色类别 | `detect.O_color_class`（0=红 1=绿 2=蓝） |

**放置与格式由 MAIN 定**（§4.5：显示区域、字体、位置、合成顺序都归 MAIN）。两点提示供参考：
- 默认优先级是 **Logo/主线状态 > 性能文字 > 目标框/十字 > 基础图像**，所以文字区域别压到 Logo 上；
- `O_out_*` 在 HOLD 期间保持"上一次被接受"的那一帧，若想让 MAIN 区分"实检"与"保持"，
  用 `O_track_state`（2=TRACK 为实检，3=HOLD 为保持）即可，不必新加信号。

## 6. 资源与延时（**估计，未经综合**）

按逻辑逐项估算（`HUE_HALF_WIDTH_DEG=30` 时斜率是 2 的幂，8×10 的常数乘法不占 LUT）：

| 模块 | LUT6 | FF | 依据 |
|---|---:|---:|---|
| detect（4 路分类 + 累加 + 锁存） | 600–900 | 150–250 | 4 路分类各约 60–80；20 位计数与 6 组 min/max 约 80–150；锁存约 120 FF |
| track（状态机 + 计数器 + 结果保持） | 150–250 | 150–250 | 2 个 8 位计数、状态译码、跳变门减法 ≈22 位、结果寄存 |
| overlay（纯组合） | 120–200 | 0 | 8 组 12 位范围比较 + 少量加法 |
| **合计** | **约 900–1350** | **约 300–500** | |
| ERAM | **0** | | 不新增任何缓存（§4.5） |
| DSP | **0** | | 常数乘走 LUT 的 CSD / 移位 |

**这是估计，不是实测**，误差可能 ±40%。§4.5 要求的"实际结果"与"最大工作频率依据"必须由 MAIN
把模块加入 TD 工程后综合得到——本角色不擅自改 TD 输入清单（§3）。

**延时**：像素通路 **0 拍**（detect 是并接观察，不串联）；结果在 `eof` 后 1 拍可用；track 与
overlay 不额外增加像素通路延迟（overlay 纯组合）。**最大工作频率未验证**：detect 的每拍路径
是"分类 → 4 路归约 → 一个寄存器"，未做流水切割；能否在观察时钟下收敛请由 MAIN 用真实综合报告判定。

## 7. 接入步骤建议

1. 核实 §4.2 的观察点位置、lane 映射、`sof` 来源（三项都在 [`INTERFACE.md` §10](INTERFACE.md) 待确认）。
2. 把 `features/color_target/rtl/*.v` 加入 TD 输入清单，按 `INTERFACE.md` §7 接线。
3. 先只接 detect，跑一次综合看资源与时序余量；再依次加 track、overlay。
4. 首次上板建议：`MAX_JUMP=0`、`ACQ_FRAMES=3`、`LOST_FRAMES=15`，先用**红色实物**在
   简单背景前验证；记录阈值是否需要调整（§4.2 允许因颜色校正变化要求重估）。
5. 上板异常时记录触发条件与所用参数，不要只写"效果不好"（协议 §6）。

## 8. 需要 MAIN 确认/提供的项

见 [`INTERFACE.md` §10](INTERFACE.md) 的 6 条：观察点与彩色流位置、`I_data` 排列、`sof` 来源、
结果 CDC 归属、T3 需要的叠加区域与统一字库、整机资源份额。

在这 6 条确认前，按协议 §5.2 本功能只能报告 **"独立模块完成 / 模拟事件验证通过"**，
不能称整机接入或进阶二已完成。
