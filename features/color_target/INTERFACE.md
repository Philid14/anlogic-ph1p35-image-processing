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

## 4.1 标注模块接口（T3，`rtl/color_target_overlay.v`）

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
- **文字由 MAIN 出**：坐标文字需要字库，§4.5 规定字库统一由 MAIN 维护；本模块只给几何，
  MAIN 用它自己的字库按框坐标渲染文字。
- 纯组合模块，**不承诺最大工作频率**；需由 MAIN 按整机时序预算决定是否插寄存器。

## 4.2 跟踪模块接口（T4，`rtl/color_target_track.v`）

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
`MAX_JUMP`(0=关闭，跳变门限，单位像素)。

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

## 4.3 三级接线参考（给 MAIN）

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
    /* O_* 见 §4.2 */
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

## 5. 参数

| 参数 | 默认 | 含义 |
|---|---|---|
| `TARGET_CLASS` | 0 | 0=红 1=绿 2=蓝 |
| `HUE_HALF_WIDTH_DEG` | 30 | hue 半宽（度）；30 即 hue 落在目标色 ±30° 内 |
| `C_MIN` | 24 | 彩度 `max-min` 下限，兼滤白/灰与暗部噪声 |
| `V_MIN` | 32 | 亮度 `max` 下限 |
| `MIN_COUNT` | 64 | 低于此像素数判为无目标 |
| `XW` / `YW` | 11 / 10 | 坐标位宽 |

## 6. 失效条件与已知限制（必须原样转述，不得省略）

1. **不分离多目标**。整帧所有匹配像素合成**一个**包围框。若画面中有两块同色区域，
   会被统计进同一个框，**这是已知限制而非缺陷**（§2.2 要求报告）。
2. **不做形态学/游程滤波**。孤立的高饱和噪点会拉大包围框。去噪与防抖属 **T4**，
   本版本刻意不做，以免在无实板噪声数据时凭猜测调参。
3. **不计算质心**。只给包围框中心。
4. **强偏色光源下阈值可能失效**。hue 法抗亮度变化，但若白平衡把红目标整体推成橙色系，
   需由 MAIN 按 §4.2 通知 TARGET 重新评估 `HUE_HALF_WIDTH_DEG`——**不得为了迁就检测
   去改主线 AWB/曝光**（§2.2）。
5. **未接入主线、未上板**。当前只有模拟输入下的自检结果。

## 7. 待 MAIN 确认 / 需要 MAIN 提供

| # | 事项 | 状态 |
|---|---|---|
| 1 | 观察点的实际位置与彩色流是否位于风格化输出之前 | 待确认 |
| 2 | `I_data` 的 lane 排列与每 lane 字节序是否与 §4.2 一致 | 待确认 |
| 3 | `sof` 由 MAIN 从现有提前帧通知转换而来 | 待确认 |
| 4 | 结果的 CDC 归属与采样方式（谁做握手/FIFO） | 待确认 |
| 5 | 显示叠加区域分配（T3 需要）与共用字库 | 待确认 |
| 6 | 整机资源预算中给本模块的份额 | 待确认 |
