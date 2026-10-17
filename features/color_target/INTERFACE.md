# `features/color_target/` 接口说明

| 项 | 值 |
|---|---|
| 角色 | **TARGET** |
| 协议版本 | `TEAM_PROTOCOL_V1`（`docs/TEAM_AI_WORK_PROTOCOL.md`） |
| 主线基线 SHA | `c42168e26026425660f2a6f51eec76b04c85eea0`（本地核对时的 `origin/main`） |
| 接口状态 | **接口草案**（§4.1 状态机：接口草案 → 负责人确认 → 已实现 → 已接入） |
| 对应赛题 | 扩展二、进阶二 |
| 当前进度 | T1 + T2 的独立模块与自检完成；**未接入主线、未产生 bit、未上板** |

> 本文件是**待 MAIN 确认的共同边界**。协议 §4.1 明确：目前主线没有可直接交付的统一
> 采集/显示帧身份接口，因此本模块的全部验证都在**显式模拟输入**下完成，不代表整机或
> 上板通过。

> **引用约定**：本文中带"协议"二字的 `§x` 指 `docs/TEAM_AI_WORK_PROTOCOL.md`（`TEAM_PROTOCOL_V1`）
> 的节号；指本文自身小节时一律写 `本文 §x`。本目录其他文档同样遵循此约定。

---

## 1. 模块与时钟

| 项 | 值 |
|---|---|
| 顶层模块 | `rtl/color_target_detect.v` |
| 子模块 | `rtl/color_classify.v`（单像素分类，纯组合） |
| 时钟 | 单时钟 `clk`，本模块**不引入新时钟域** |
| 复位 | `rst_n`，低有效；`posedge clk or negedge rst_n` |
| 反压 | **无**。本模块是观察者（sink），不产生 `ready`，不对采集链路施加反压 |
| 在通路中的位置 | **并接**在观察点上，不串联、不延迟像素。MAIN 只需把同一份观察流扇出给它 |

## 2. 输入：规范化像素观察流（§4.2）

| 信号 | 方向 | 位宽 | 说明 |
|---|---|---|---|
| `I_pixel_valid` | in | 1 | 为 1 时消费整拍 4 个像素 |
| `I_data` | in | 96 | lane0=`[95:72]`、lane1=`[71:48]`、lane2=`[47:24]`、lane3=`[23:0]`；每 lane 24 位 = `{R[7:0],G[7:0],B[7:0]}`，按显示坐标从左到右 |
| `I_x0` | in | `XW`(默认 11) | 本拍 **lane0** 的 x；lane k 的 x = `x0+k`。原点左上，x 向右 |
| `I_y` | in | `YW`(默认 10) | 本拍 4 个像素共用的 y，y 向下 |
| `I_sof` | in | 1 | 伴随**本帧首个有效拍** |
| `I_eol` | in | 1 | 伴随本行最后一个有效拍。**本版本不依赖它**，保留以对齐接口 |
| `I_eof` | in | 1 | 伴随**本帧最后一个有效拍** |
| `I_session_id` | in | 32 | 会话身份；复位/重新采集开始新 session |
| `I_frame_id` | in | 32 | 帧身份；回绕前应开启新 session |
| `I_frame_abort` | in | 1 | 中断/错误帧：本帧结果作废 |

**必须由 MAIN 确认的两点**（我无法在本地验证，协议 §4.2 已点到）：

1. **实际 lane 映射**。上面 `lane0=[95:72]` 是本协议 V1 的**约定值**。主线实际打包顺序
   由 MAIN 核实；若不同，由 MAIN 在适配器里转换，本模块不改。
2. **`sof` 的来源**。协议写明"主线现有提前帧通知不等于上述 `sof`"，MAIN 必须把它转换
   成"首个有效拍"再给出。本模块**不把任意 `tuser` 当成 sof**。

**观察点要求**：必须是可用于颜色判断的**彩色流**，位于边缘/区域填充等风格化输出**之前**（§4.2）。
颜色校正（CCM/白平衡）变化会改变分类结果，即使端口不变也必须通知 TARGET 重新评估（§4.2）。

> ⚠️ **`sof` 是强依赖，漏发会静默出错（复查时发现，需 MAIN 注意）**
> 本模块用 `sof` 复位帧内累加器。若某一帧没有 `sof`：该帧的像素会**累加到上一帧的统计上**
> （像素数与包围框同时错），而且结果**仍会被判为有效**、带上的是上一帧的身份——
> 属于"不报错但结果错"的类型。
> 协议 §4.2 要求 MAIN 把现有的"提前帧通知"转换成"首个有效拍"的 `sof`，请务必保证
> **每帧有且只有一个 `sof`**。
> 若 MAIN 希望这种情况**响亮地失败**（无 `sof` 的帧直接产出 `O_result_valid=0`），
> TARGET 可以把内部 `open_f` 在发布后清零，是一处小改动，需要的话告知即可。

## 3. 输出：检测结果（§4.3）

结果在 **帧末原子锁存**，并在下一帧期间保持不变；`O_result_ready` 为单拍脉冲，
出现该脉冲时结果寄存器已同步更新。

| 信号 | 方向 | 位宽 | 说明 |
|---|---|---|---|
| `O_res_session_id` / `O_res_frame_id` | out | 32 / 32 | 与本次结果对应的身份 |
| `O_result_valid` | out | 1 | 中断帧为 0 |
| `O_target_present` | out | 1 | 为 0 时下列字段全部清零 |
| `O_color_class` | out | 2 | 0=红 1=绿 2=蓝 |
| `O_pixel_count` | out | 20 | 匹配像素数 |
| `O_xmin` / `O_xmax` | out | `XW` | 包围框左右，**两端均包含在范围内** |
| `O_ymin` / `O_ymax` | out | `YW` | 包围框上下，两端均包含 |
| `O_center_x` / `O_center_y` | out | `XW` / `YW` | **包围框中心 = (min+max)>>1 向下取整，不是像素质心** |
| `O_result_ready` | out | 1 | 单拍脉冲：新结果已锁存 |

**坐标约定**：一律以原图 1280×720 为准，来自 `I_x0`/`I_y`。**不使用 Sobel 的 640 点
下采样坐标**（§4.3 明确禁止）。像素数上限 1280×720 = 921 600，20 位足够。

**帧末语义（已按 §4.3 实现并自检）**：
- **最后一个有效拍的 4 个像素计入结果**（这是自检用例 `xmax_at_1279` 的判据之一）。
- 中断帧：`O_result_valid=0` 且所有数据字段清零。
- **中止状态只对"本帧"生效**：上一帧的中止标志**不得**泄漏到紧随其后的新帧。
  新帧开始那一拍只按本帧的 `I_frame_abort` 判定（自检用例 `abort_then_single_beat_ok`
  覆盖的正是"中止帧之后紧跟一帧正常单拍帧"这条路径；反向的
  `single_beat_aborted_still_void` 锁住"单拍帧自己中止时仍须作废"）。
- 命中数 < `MIN_COUNT`：`O_target_present=0`，坐标清零。
- 未收到 `eof` 的截断帧不发布（自检用例 `truncated_then_ok`）。
- `sof` 与 `eof` 同拍的单拍帧正常发布，且身份取本拍（自检用例 `single_beat_all_red` / `count_below_min`）。

**跨时钟域**：本模块全程在 `clk` 单域内。若 MAIN 需要在显示域使用结果，**CDC 由 MAIN 的
适配层负责**（§4.3 要求"由经确认的握手/FIFO 适配完成"），本模块不提供握手。

## 4. 延迟

| 项 | 值 |
|---|---|
| 像素通路延迟 | **0 拍**（并接观察，不串联像素） |
| 结果产生延迟 | `eof` 那一拍之后 **1 拍** 出现 `O_result_ready`，结果同时有效 |
| 统计口径 | 帧级；不含任何跨帧状态，无帧间滤波 |

## 5. 标注模块接口（T3，`rtl/color_target_overlay.v`）

**纯组合、无时钟、无流水级**：给定当前显示坐标与整帧锁存的结果，直接给出该像素的覆盖请求。
MAIN 逐像素调用即可，不引入对齐负担。

| 信号 | 方向 | 位宽 | 说明 |
|---|---|---|---|
| `I_pixel_valid` | in | 1 | 当前显示坐标有效 |
| `I_x` / `I_y` | in | `XW` / `YW` | 当前显示坐标 |
| `I_result_valid` / `I_target_present` | in | 1 / 1 | 直接来自 `color_target_detect` 的锁存结果 |
| `I_xmin` `I_xmax` `I_ymin` `I_ymax` | in | `XW`/`XW`/`YW`/`YW` | 同上 |
| `I_center_x` / `I_center_y` | in | `XW` / `YW` | 同上 |
| `O_overlay_valid` | out | 1 | 该像素是否要被覆盖 |
| `O_overlay_rgb` | out | 24 | RGB888 覆盖颜色 |

参数：`BOX_THICK`(3)、`BOX_RGB`(0x00FF00)、`CROSS_ARM`(12)、`CROSS_THICK`(1)、`CROSS_RGB`(0xFFFF00)。

**边界（§4.3 / §4.5）**：
- **帧/行内不改变基础像素数量**：只发出颜色请求，不消费、不延迟、不复制像素。
- **不决定遮挡与合成顺序**：§4.5 的优先级（Logo/主线状态 > 性能文字 > 目标框/十字）由 MAIN
  的 mixer 执行，本模块不做遮挡规避、不绑定按键/引脚、不改共用字库。
- **文字见 §5.1**：文字由**独立的** `color_target_text_overlay.v` 出（它同样不拥有字库，
  字形向 MAIN 借）；本模块只给几何。两者是并列的两个覆盖请求，优先级由 MAIN 的 mixer 定。
- 纯组合模块，**不承诺最大工作频率**；需由 MAIN 按整机时序预算决定是否插寄存器。

## 5.1 文字标注接口（T3 的文字部分，`rtl/color_target_text_overlay.v`）

对应赛题扩展要求(2) 的"文字说明"与高阶挑战项(2) 的"坐标叠加"。**逐像素、带时钟**（内部有一个
用 70 拍完成一组十进制转换的小状态机），区域与字形全部参数化。

| 信号 | 方向 | 位宽 | 说明 |
|---|---|---|---|
| `clk` / `rst_n` | in | 1 | 与**显示侧**同域（HDMI 像素时钟），不是观察时钟——见 §10 第 4 条 |
| `I_pixel_valid` / `I_x` / `I_y` | in | 1 / `XW` / `YW` | 当前显示坐标（与 `color_target_overlay` 同一约定） |
| `I_update` | in | 1 | **可选**：与 `clk` 同域的更新脉冲；结果字段或状态/明暗变化也会自动触发，异步源需先原子 CDC |
| `I_show` / `I_state` | in | 1 / 2 | `track.O_show` / `track.O_track_state`；`I_show` 只决定字形亮/暗，不决定是否覆盖 |
| `I_count` / `I_center_x` / `I_center_y` | in | 20 / `XW` / `YW` | `track.O_out_count` / `O_out_center_x` / `O_out_center_y` |
| `O_glyph_char` / `O_glyph_row` | out | 8 / 4 | **字形请求**：字符（ASCII）与该字形行（0..15） |
| `I_glyph_bits` | in | 16 | **字形点阵**，`[15]` 最左；由 MAIN 的 `osd_char_lib` 组合返回 |
| `O_overlay_valid` / `O_overlay_rgb` | out | 1 / 24 | 覆盖请求（区域内一律覆盖：底色或字形色） |

参数：`XW`/`YW`、`ENABLE`(1)、`X0`(16)、`Y0`(600)、`SCALE`(1，只支持 1 或 2)、`LINE_CHARS`(14)、
`TEXT_RGB`(白)、`DIM_RGB`(灰，`I_show=0` 时用)、`BG_RGB`(深灰)。区域尺寸 =
`LINE_CHARS×16×SCALE` 宽 × `2×16×SCALE+2×SCALE` 高。

**更新时间约定（2026-10-17 修复）**：空闲时对 `count/x/y/state/show` 整组快照；
三轮转换只读快照，70 拍内将数字、状态和明暗同拍发布。转换期间保持上一组完整显示。
忙时的新值在当前事务结束后自动处理，最新稳定值最多 140 拍可见；中间变化允许合并，
本接口不承诺逐事件排队。复位丢弃当前事务与旧显示，回到零值/SEARCH/暗色。
这保证的是同一拍的字段一致性，**不提供整显示帧的原子切换**：MAIN 仍需匹配帧身份，
并在消隐期预留转换时间，或用显示侧适配层安排帧边界切换。

画面内容（两行）：

```
RED Xnnnn Ynnn              ← 目标中心坐标（**不是质心**）
Nnnnnnn SEARCH|ACQ|TRACK|HOLD
```

**三条硬约束/约定**：
1. **本模块不实例化字库**（§3：共享 OSD 归 MAIN）。`O_glyph_char`/`O_glyph_row` 是**组合请求**，
   MAIN 把它接到已有的 `osd_char_lib` 实例上，把返回的 16 位点阵接回 `I_glyph_bits` 即可。
   字库未定义字符返回 `0x0000`（主线的 `default` 就是 0），所以空格自然是空白。
2. **只能在显示侧合成**（不能放在 ISP→DDR 之前）：检测结果帧末才有，塞不进本帧像素流。
   详细理由见 §10 与模块文件头。
3. **超显示位数时饱和、不截断**：`count>999999`→`999999`、`x>9999`→`9999`、`y>999`→`999`。
   实际取值范围内不会触发（`count≤921600`、`x≤1279`、`y≤719`）。

**接入前已验证**：与主线**真实字库**逐位比对通过（28 用例 / 307078 像素），
即"字形位索引 `[15]` 最左、16 位/行、16 行"这条隐式契约与主线一致。

## 6. 跟踪模块接口（T4，`rtl/color_target_track.v`）

`detect` 与 `overlay` 之间的一级。把"每帧一次的原始检出"变成"稳定可演示的显示结果"，
数据通路为 **`detect → track → overlay`**。

| 信号 | 方向 | 位宽 | 说明 |
|---|---|---|---|
| `I_result_strobe` | in | 1 | 接 `color_target_detect` 的 `O_result_ready` |
| `I_result_valid` / `I_target_present` | in | 1 / 1 | 接 detect 的同名输出 |
| `I_pixel_count` | in | 20 | 同上 |
| `I_xmin` `I_xmax` `I_center_x` | in | `XW` | 同上 |
| `I_ymin` `I_ymax` `I_center_y` | in | `YW` | 同上 |
| `I_session_id` / `I_frame_id` | in | 32 / 32 | 同上 |
| `O_track_state` | out | 2 | 0=SEARCH 1=ACQ 2=TRACK 3=HOLD（可直接送 MAIN 的 OSD 显示状态文字） |
| `O_show` | out | 1 | 1 时才有可显示的框（TRACK 或 HOLD） |
| `O_out_*`（count/坐标/身份） | out | 同输入 | HOLD 期间保持"上次被接受"的那一帧 |
| `O_state_change` | out | 1 | 状态变化时的一拍脉冲 |

参数：`ACQ_FRAMES`(3，连续检出多少帧确认)、`LOST_FRAMES`(15，连续丢失多少帧判彻底失去)、
`MAX_JUMP`(0=关闭，跳变门限，单位像素)。**合法范围**：`ACQ_FRAMES` / `LOST_FRAMES` 取
**1..255**（底层 8 位计数器；取 0 与取 1 同义 = 立即，超过 255 夹到 255），`MAX_JUMP` 取
**0 或正数**（负数夹到 0 = 关闭）。夹取在编译期完成，不产生运行时逻辑。
**门限对"TRACK 的首次丢失"同样生效**：`LOST_FRAMES=1` 时首次丢失就立刻隐藏
（自检用例 `lost_frames_1_hides_on_first_miss`）。

**接 overlay 的接线**（两行即可）：

```verilog
overlay.I_result_valid   = track.O_show;
overlay.I_target_present = track.O_show;
```

**语义要点（§4.1 / §4.3）**：
- **中止帧（`I_result_valid=0`）不评估**：跳过，不改变状态。§4.3 说检测模块丢弃中止帧结果，
  但"丢一帧结果"不等于"目标消失"，当丢失处理会误判。
- **会话变化强制清零**：新会话首帧按 SEARCH 重新判定，不把旧会话状态带过去（§4.1）。
- **HOLD 期间不清零显示结果**：保持上一次被接受的那一帧的坐标与身份，避免框突然消失。
- 需要 MAIN 注意：`O_out_session_id/frame_id` 是**上一次被接受**的那一帧身份，不是当前帧。
  MAIN 若要判断"这个框是不是本帧的"，应比较该身份与当前帧身份。

## 7. 三级接线参考（给 MAIN）

数据通路：**`detect → track → overlay`**，其中 track 与 overlay 的连接只需两行：

```verilog
u_track u_track (
    .clk(clk), .rst_n(rst_n),
    .I_result_strobe  (u_detect.O_result_ready),
    .I_result_valid   (u_detect.O_result_valid),
    .I_target_present (u_detect.O_target_present),
    .I_pixel_count    (u_detect.O_pixel_count),
    .I_xmin (u_detect.O_xmin), .I_xmax (u_detect.O_xmax), .I_center_x (u_detect.O_center_x),
    .I_ymin (u_detect.O_ymin), .I_ymax (u_detect.O_ymax), .I_center_y (u_detect.O_center_y),
    .I_session_id (u_detect.O_res_session_id), .I_frame_id (u_detect.O_res_frame_id),
    /* O_* 见 §6 */
);

u_overlay u_overlay (
    .I_pixel_valid   (display_pixel_valid),   // 显示坐标有效
    .I_x (display_x), .I_y (display_y),
    .I_result_valid   (u_track.O_show),
    .I_target_present (u_track.O_show),
    .I_xmin (u_track.O_out_xmin), .I_xmax (u_track.O_out_xmax),
    .I_center_x (u_track.O_out_center_x),
    .I_ymin (u_track.O_out_ymin), .I_ymax (u_track.O_out_ymax),
    .I_center_y (u_track.O_out_center_y),
    /* O_overlay_valid / O_overlay_rgb 交 MAIN 的 mixer */
);
```

**⚠️ 必须由 MAIN 处理的一件事：结果与显示帧的对齐。**
已实测（`run_color_target_chain.py`，396 拍逐拍比对）的实际时序是：

| 时刻 | 事件 |
|---|---|
| 本帧最后一个有效拍 | detect 收到 `eof` |
| 该拍**之后 1 拍** | detect 发 `O_result_ready`，结果锁存 |
| 同上那一拍 | track 消费结果 → `O_show` 与框坐标更新 |
| 同上那一拍 | overlay 是纯组合的，**立刻**改用新结果 |

也就是说，若把 overlay 直接接在 track 上，**本帧最后 1~2 个像素会用上刚发布的新结果**
（框在这一帧末尾就跳了）。要完全避免，MAIN 需在**帧边界**把结果寄存一级再喂给 overlay
——这正是协议 §4.3 要求的"读出时使用匹配结果；不能把上一帧的框悄悄标成当前帧检测结果"。

本自检台按**现有直接接线**测量并如实记录该现象，没有替 MAIN 加适配层，免得掩盖真实接线行为。

## 8. 参数

| 参数 | 默认 | 合法范围 | 含义 |
|---|---|---|---|
| `TARGET_CLASS` | 0 | 0 / 1 / 2 | 0=红 1=绿 2=蓝（并列最大时给低序号通道优先，分类互斥） |
| `HUE_HALF_WIDTH_DEG` | 30 | **0..60** | hue 半宽（度）；30 即 hue 落在目标色 ±30° 内 |
| `C_MIN` | 24 | **0..511** | 彩度 `max-min` 下限，兼滤白/灰与暗部噪声 |
| `V_MIN` | 32 | **0..255** | 亮度 `max` 下限 |
| `MIN_COUNT` | 64 | **≥1** | 低于此像素数判为无目标 |
| `XW` / `YW` | 11 / 10 | ≥ 1 | 坐标位宽。1280×720 需 `XW=11`/`YW=10`；更小的几何也支持（已实测 `XW=9/YW=8` 的 320×240、`XW=7/YW=6`、以及 `XW=2/YW=2` 的边界值），位宽不足时坐标按位宽截断，这是选定了位宽的自然结果 |

overlay 的参数见 §5 一节：`BOX_THICK >= 1`、`CROSS_THICK >= 1`、`CROSS_ARM >= 0`。
文字标注的参数见 §5.1：`ENABLE`、`X0`/`Y0`（区域，**由 MAIN 决定**）、`SCALE`(1 或 2)、
`LINE_CHARS`、三个颜色。区域尺寸由它们算出，不是写死的。

**合法范围都在编译期夹取**（常量折叠，不产生运行时逻辑），越界参数不会造成溢出、除零
或"高位被悄悄丢掉"这类退化行为。判据用交叉乘积 `60·|d| ≤ W·C`，**位宽与 `W` 无关**，
所以 `W` 取任何合法值都不会出现乘积截断；这条正是审查意见①的修复内容（`README.md` §6）。
夹取与逐条对应关系见 `README.md` §7——那里也说明了为什么"碰巧对"不算对。

## 9. 失效条件与已知限制（必须原样转述，不得省略）

1. **不分离多目标**。整帧所有匹配像素合成**一个**包围框。若画面中有两块同色区域，
   会被统计进同一个框，**这是已知限制而非缺陷**（§2.2 要求报告）。
2. **不做形态学/游程滤波**。孤立的高饱和噪点会拉大包围框。`README.md` §2.5 的渲染把这个
   后果量化了：320×240 画面里 40 个孤立单像素红点就把框从 `60×60` 撑到 `309×209`；
   而且框只在"被接受"的帧更新，被撑大的框会被 HOLD 保持到有新的被接受帧为止。
   去噪与防抖属 **T4**；本版本刻意不做像素级滤波，以免在无实板噪声数据时凭猜测调参。
3. **不计算质心**。只给包围框中心。
4. **强偏色光源下阈值可能失效**。hue 法抗亮度变化，但若白平衡把红目标整体推成橙色系，
   需由 MAIN 按 §4.2 通知 TARGET 重新评估 `HUE_HALF_WIDTH_DEG`——**不得为了迁就检测
   去改主线 AWB/曝光**（§2.2）。
5. **未接入主线、未上板**。当前只有模拟输入下的自检结果。

## 10. 待确认 / 需要 MAIN 提供（一次性清单）

下面每一条都给出：**我在主线代码里查到的事实**（带证据）、**我的默认假设**、以及**假设不成立的影响**。
MAIN 只需逐条"确认"或"纠正"，不必来回追问。证据都是只读查证，未修改任何主线文件。

| # | 事项 | 代码查到的事实（证据） | 我的默认假设 | 若不同，影响 |
|---|---|---|---|---|
| 1 | 观察点位置 | AWB 输出 `awb_O_tdata[95:0]` 即风格化之前：它进 `edge_control_stream` 才被二选一（`isp/isp_top.v:48,69,153`；`isp/edge_control_stream.v:49` `config_p[4][8] ? edge_data : original_p[4]`） | 取 `awb_O_tdata`（只读扇出，不串联、不加反压） | 若 MAIN 认为必须放在别处，本模块的输入宽度与 lane 约定要重评 |
| 2 | `I_data` 的 lane 排列与字节序 | **与 §4.2 完全一致**，无需转换：`isp/data128_96/data128_96.v:16` 反序取 24 位；demosaic 每像素 `{8'b0,R,G,B}`（`isp/demosaic_4x_2_0/bilinear_interpolation.v:882`），故 lane0=[95:72]、每 lane {R,G,B}；同链路的消费端 `isp/edge_detect_96.v:36-43`、`edge_status_osd.v:107-111` 亦同 | 直接按 §4.2 接 | 无 |
| 3 | **`sof` / `eof`（最重要的一条）** | `I_user` **就是 SOF**（`isp/uial2axis.v:56` `axis_tuser = vcnt==0 && hcnt==0 && tvalid`）；但 `I_last` **是行尾 EOL 不是帧尾**（`isp/uial2axis.v:55` `axis_tlast = hcnt == IMG_WIDTH_4X-1`；`isp_top.v:124` 注释亦写"行结束信号"）。**帧尾没有现成的流信号** | `I_sof ← I_user`；`I_eol ← I_last`；**`I_eof` 由 MAIN 生成**（最后一行最后一个有效拍，可由行计数 + vsync/计数器导出） | 若把 `I_last` 直接当 `I_eof`，每行都会"发布一次结果"——整帧统计会完全错。这是接入时最容易踩的一条 |
| 4 | 结果的 CDC 归属 | 观察流在 **`S_csi_rx_clk`**（`design_top_wrapper.v:589` → `isp_top`，`isp/isp_top.v:9`），**不是** HDMI 像素时钟；显示侧在 `I_clk`(HDMI_PIXEL_CLK) | 由 **MAIN 的适配层**实现原子请求/应答握手，源端保持整组数据至确认；是否需要 FIFO 由吞吐和保持能力决定。文字模块只接收适配后的同域字段 | 单拍脉冲直接过两级同步可能漏事件；字段分别同步不能保证整组一致，均不构成完整 CDC |
| 5 | 显示叠加区域与共用字库 | 主线已有 `osd_char_lib.v`（字库，"frozen"）与 `edge_status_osd.v`（**参数化区域 X0/Y0**、含不用除法器的三位十进制分解）；`hdmi_mixer.v:900-905` 是逐像素合成点（显示坐标 `S_x_2d/S_y_2d`，`:556-559`），`:563` 那段组合逻辑是自然接入位置；主线状态框占 (800,16)+448×72 | 框/十字与文字块区域由 MAIN 分配；我**默认**文字块放左下 (16,600)+224×34（720p），SCALE=1。**字形借 MAIN 已有实例**（我的模块不实例化字库） | 区域只影响 `X0/Y0` 参数；若 MAIN 要求另放一份字库，实测代价参考：整份 `edge_status_osd`（**含字库**）248 LUT/234 reg |
| 6 | 整机资源预算中给本模块的份额 | 现存 EDGE_CONTROL_V1：`#lut 18307 / 38189`（48%）、slice 利用率 68.84%（`artifacts/bitstreams/EDGE_CONTROL_V1/build_evidence/camera_to_dsi_display_gate.area`） | 文字模块独立 gate 为 282 LUT/194 reg（见 `evidence/text_atomic_2026-10-17/VALIDATION.md`）；其余模块仍为估计，整机预算待 MAIN 确认 | 预算不足时 MAIN 可先关闭文字模块（`ENABLE=0`） |
| 7 | 显示坐标约定 | `hdmi_mixer` 的 `S_x_2d/S_y_2d` 与 `S_video_data_2d` 对齐；mixer 有 `H_OFFSET/V_OFFSET` 参数 | 我假设 overlay 收到的 (x,y) **就是**显示坐标（与 `S_x_2d/S_y_2d` 同域同原点），**不需要**再减偏移 | 若需要减偏移，MAIN 在适配层处理；我的模块只认收到的坐标 |

### 10.1 接线示意（按默认假设）

```verilog
// 观察（S_csi_rx_clk 域，只读扇出，不串联像素）
color_target_detect #(...) u_detect (
    .I_pixel_valid(awb_O_tvalid), .I_data(awb_O_tdata[95:0]),
    .I_sof(awb_O_tuser),                 // = SOF，见第 3 条
    .I_eol(awb_O_tlast),                 // = EOL
    .I_eof(ct_frame_eof),                // ← MAIN 生成（第 3 条）
    ...);

color_target_track #(...) u_track (...);   // 同域，吃 detect 的 O_result_ready

// 跨域（MAIN 的适配层，第 4 条）：把 track 的结果窄握手到显示域 → td_* 信号
// 显示（HDMI 像素时钟域，在 hdmi_mixer 的逐像素合成处）
color_target_overlay      #(...) u_box  (.I_x(S_x_2d), .I_y(S_y_2d), ...);
color_target_text_overlay #(...) u_text (.I_x(S_x_2d), .I_y(S_y_2d),
                                          .I_count(td_count), .I_state(td_state), ...,
                                          .O_glyph_char(fnt_char), .O_glyph_row(fnt_row),
                                          .I_glyph_bits(fnt_bits));
// 合成优先级（§4.5）：文字 > 框/十字 > 基础图像
```

需要 MAIN 额外提供而本角色**不能自造**的只有三样：**`I_eof` 的生成**、**跨域适配**、
**区域分配**。其余都已在上面查证或已参数化。

## 11. 研究候选 A（2026-10-17，未接入）

另有默认旁路的独立二值掩膜过滤原型 `color_target_support3`，见 [SUPPORT3.md](SUPPORT3.md)。
它不改变本文件前述检测/跟踪接口。启用后需要行延迟和 EOF 自动补零结算，不能与原始 RGB
按旧拍号混用；只接受完整固定尺寸光栅，截断流需复位恢复。其额外诊断口与异常帧适配
尚未成为 TEAM 接口。实际接入仍须 MAIN 确认观察点、预算、身份及 CDC/显示适配。
