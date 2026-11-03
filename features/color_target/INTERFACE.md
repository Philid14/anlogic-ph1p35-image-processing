> 当前验证入口：[VERIFICATION.md](VERIFICATION.md)。系统适配仍为草案，不能从示意代码推断 MAIN 已接入。

# `features/color_target/` 接口说明

| 项 | 值 |
|---|---|
| 角色 | **TARGET** |
| 协议版本 | `TEAM_PROTOCOL_V1`（`docs/TEAM_AI_WORK_PROTOCOL.md`） |
| 主线基线 SHA | `c42168e26026425660f2a6f51eec76b04c85eea0`（本地核对时的 `origin/main`） |
| 接口状态 | **接口草案**（§4.1 状态机：接口草案 → 负责人确认 → 已实现 → 已接入） |
| 对应赛题 | 扩展二、进阶二 |
| 当前进度 | T1–T4 独立模块、自检与 A1 修复完成；A2 身份/年龄仍开放；**未接入主线、未产生 bit、未上板** |

> 本文件是**待 MAIN 确认的共同边界**。协议 §4.1 明确：目前主线没有可直接交付的统一
> 采集/显示帧身份接口，因此本模块的全部验证都在**显式模拟输入**下完成，不代表整机或
> 上板通过。

> **引用约定**：本文中带"协议"二字的 `§x` 指 `docs/TEAM_AI_WORK_PROTOCOL.md`（`TEAM_PROTOCOL_V1`）
> 的节号；指本文自身小节时一律写 `本文 §x`。本目录其他文档同样遵循此约定。

---

2026-10-20交付增补：本文保留旧检测器端口说明；新guard使用独立
[TRACK_GUARD_INTERFACE](integration/TRACK_GUARD_INTERFACE.md)，严格光栅首接建议和完整显式依赖见
[MAIN_HANDOFF](board/MAIN_HANDOFF.md)。本轮用户确认上传TARGET、由MAIN队友接入；当前未进入TD/bit。

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

**SOF 与恢复边界（更新至 A1/EOF 修复后）：** 每帧必须有且仅有一个与有效像素对齐的 SOF。
原检测器已在 EOF 关闭帧；之后缺 SOF 的 EOF 会发布 ready 但 valid=0，不再重复上帧有效统计。
它不检查完整固定光栅，也不能保证任意截断/提前 SOF 的系统恢复；独立流封装另有光栅检查及显式复位契约。
缺失 EOF、非完整尾拍及 reset 取消须由 MAIN 按可信事务记账。详见 [系统草案](integration/MAIN_CONTRACT_DRAFT.md)。

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
| 结果产生延迟 | 原检测器在 EOF 采样沿后结果和 ready 可见；以该沿为 0，下游 track 在 +1 沿消费。流封装旁路 +1、过滤 +WIDTH/4+3，详见 REPLAY.md |
| 统计口径 | 帧级；不含任何跨帧状态，无帧间滤波 |

## 5. 标注模块接口（T3，`rtl/color_target_overlay.v`）

**纯组合、无时钟、无流水级**：给定当前显示坐标与整帧锁存的结果，直接给出该像素的覆盖请求。
MAIN 逐像素调用即可，不引入对齐负担。

| 信号 | 方向 | 位宽 | 说明 |
|---|---|---|---|
| `I_pixel_valid` | in | 1 | 当前显示坐标有效 |
| `I_x` / `I_y` | in | `XW` / `YW` | 当前显示坐标 |
| `I_result_valid` / `I_target_present` | in | 1 / 1 | MAIN 显示域中已匹配并整帧提交的字段 |
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
| `I_show` / `I_state` | in | 1 / 2 | MAIN 提交的 show/state；`I_show` 只决定字形亮/暗，不决定是否覆盖 |
| `I_count` / `I_center_x` / `I_center_y` | in | 20 / `XW` / `YW` | MAIN 提交的 count / center_x / center_y |
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
| `O_show` | out | 1 | 当前 TRACK/HOLD 候选显示状态；不含去重/年龄/显示帧匹配保证 |
| `O_out_*`（count/坐标/身份） | out | 同输入 | HOLD 期间保持"上次被接受"的那一帧 |
| `O_state_change` | out | 1 | 状态变化时的一拍脉冲 |

参数：`ACQ_FRAMES`(3，连续检出多少帧确认)、`LOST_FRAMES`(15，连续丢失多少帧判彻底失去)、
`MAX_JUMP`(0=关闭，跳变门限，单位像素)。**合法范围**：`ACQ_FRAMES` / `LOST_FRAMES` 取
**1..255**（底层 8 位计数器；取 0 与取 1 同义 = 立即，超过 255 夹到 255），`MAX_JUMP` 取
**0 或正数**（负数夹到 0 = 关闭）。夹取在编译期完成，不产生运行时逻辑。
**门限对"TRACK 的首次丢失"同样生效**：`LOST_FRAMES=1` 时首次丢失就立刻隐藏
（自检用例 `lost_frames_1_hides_on_first_miss`）。

**语义与限制：** 有效无目标按既有丢失状态机处理；无效 strobe 被跳过，不能等同于目标消失。
当前 RTL 只在有效结果中处理 session 变化；无效新 session 不清旧状态，旧 session 有效包可回切。
重复/倒序身份不会被拒绝，无效帧列与停止输入不会使历史结果按时间失效。
这些已由 9 个采样、6 个 OPEN_GAP 复现，不能以原 21/21 状态机回归将其关闭。
[TRACK_ADMISSION_PROPOSAL.md](integration/TRACK_ADMISSION_PROPOSAL.md) 提出责任与不变量，尚未批准实现。

`O_out_*` 保持上次被接受的身份和字段。TRACK 状态也可能保持旧观测，不能仅用状态区分“本帧实检”。
MAIN 应按显示帧、观测身份、可信时间和已批准策略判断是否显示，并在显示边界整组提交；
禁止将原 `O_show` 和异步变化的坐标直接接到正在扫描的框/文字上。

## 7. 连接责任示意（不是现成 MAIN 适配器）

同一观察域内可由 detect.O_result_ready 驱动 track.I_result_strobe；其他结果字段同组连接。
现有链路测试验证这一级时序，但不验证生产 TRACK 的身份准入，也不实现跨域/DDR/显示选帧。

```text
规范化 RGB/坐标/标记/身份（MAIN）
    → 选定检测路径（TARGET） → 身份准入/年龄策略（待批准）
    → 原子结果跨域（MAIN，须证明容量和复位）
    → 与 DDR 所选 frame_key/槽代次关联（MAIN）
    → 文字准备完成 + 框/十字/字段一次显示提交（MAIN）
    → 两个独立覆盖模块 → MAIN mixer
```

以输入 EOF 采样沿为 0：原检测器结果在该沿后可见，track 在 +1 沿更新；
新流封装旁路结果 +1、track +2，过滤结果 +WIDTH/4+3、track 再 +1。
直接组合 overlay 会立刻跟随所接字段，不保证活动扫描稳定。
仅加一级帧边界寄存器可固定一帧的字段，但无法建立帧身份、修复槽复用或保证框文字同观测。
具体承诺与服务时限见 [MAIN_CONTRACT_DRAFT.md](integration/MAIN_CONTRACT_DRAFT.md)。

## 8. 参数

| 参数 | 默认 | 合法范围 | 含义 |
|---|---|---|---|
| `TARGET_CLASS` | 0 | 0 / 1 / 2 | 0=红 1=绿 2=蓝；其他配置回退红且结果标签 0（A1）；并列最大按低序号通道优先 |
| `HUE_HALF_WIDTH_DEG` | 30 | **0..60** | hue 半宽（度）；30 即 hue 落在目标色 ±30° 内 |
| `C_MIN` | 24 | **0..511** | 彩度 `max-min` 下限，兼滤白/灰与暗部噪声 |
| `V_MIN` | 32 | **0..255** | 亮度 `max` 下限 |
| `MIN_COUNT` | 64 | **≥1** | 低于此像素数判为无目标 |
| `XW` / `YW` | 11 / 10 | ≥ 1 | 坐标位宽。1280×720 需 `XW=11`/`YW=10`；更小的几何也支持（已实测 `XW=9/YW=8` 的 320×240、`XW=7/YW=6`、以及 `XW=2/YW=2` 的边界值），位宽不足时坐标按位宽截断，这是选定了位宽的自然结果 |

overlay 的参数见 §5 一节：`BOX_THICK >= 1`、`CROSS_THICK >= 1`、`CROSS_ARM >= 0`。
文字标注的参数见 §5.1：`ENABLE`、`X0`/`Y0`（区域，**由 MAIN 决定**）、`SCALE`(1 或 2)、
`LINE_CHARS`、三个颜色。区域尺寸由它们算出，不是写死的。

**数值门限在编译期夹取，类别使用上述回退规则**（常量折叠，不产生运行时逻辑），越界参数不会造成溢出、除零
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
6. **TRACK 未落实身份准入与时间年龄**。六个 OPEN_GAP 见本文 §6 和 A2 提案；不以状态或 O_show 单独证明新鲜度。
7. **文字颜色名固定 RED**（rtl/color_target_text_overlay.v 的字符选择）。绿/蓝检测结果标签一致性不代表文字类别联动；非红演示需另行适配批准。

## 10. 待确认 / 需要 MAIN 提供（一次性清单）

2026-10-18补查纠正：AWB的user是提前通知，不能直接作为本模块SOF。
当前完整接口/异常/CDC/显示契约以 [MAIN_CONTRACT_DRAFT.md](integration/MAIN_CONTRACT_DRAFT.md)
为待确认草案；下表第3项及示例已纠正，原始历史证据未覆盖。

下面每一条都给出：**我在主线代码里查到的事实**（带证据）、**我的默认假设**、以及**假设不成立的影响**。
MAIN 只需逐条"确认"或"纠正"，不必来回追问。证据都是只读查证，未修改任何主线文件。

| # | 事项 | 代码查到的事实（证据） | 我的默认假设 | 若不同，影响 |
|---|---|---|---|---|
| 1 | 观察点位置 | AWB 输出 `awb_O_tdata[95:0]` 即风格化之前：它进 `edge_control_stream` 才被二选一（`isp/isp_top.v:48,69,153`；`isp/edge_control_stream.v:49` `config_p[4][8] ? edge_data : original_p[4]`） | 取 `awb_O_tdata`（只读扇出，不串联、不加反压） | 若 MAIN 认为必须放在别处，本模块的输入宽度与 lane 约定要重评 |
| 2 | `I_data` 的 lane 排列与字节序 | **与 §4.2 完全一致**，无需转换：`isp/data128_96/data128_96.v:16` 反序取 24 位；demosaic 每像素 `{8'b0,R,G,B}`（`isp/demosaic_4x_2_0/bilinear_interpolation.v:882`），故 lane0=[95:72]、每 lane {R,G,B}；同链路的消费端 `isp/edge_detect_96.v:36-43`、`edge_status_osd.v:107-111` 亦同 | 直接按 §4.2 接 | 无 |
| 3 | **规范化SOF/EOL/EOF** | RAW侧 `isp/uial2axis.v:55-56` 为有效拍SOF和EOL；但编译的根 `awb.v:303-307` 将user保留为提前通知，RGB/valid另有延迟，last由valid包络生成 | MAIN提供与AWB RGB实际对齐的独立SOF/坐标/EOL/EOF，保留主线原提前通知；不能直接接awb user | SOF错位会漏开帧；把EOL当EOF会逐行发布；行内valid空洞也需单独处理 |
| 4 | 结果的 CDC 归属 | 观察流在 **`S_csi_rx_clk`**（`design_top_wrapper.v:589` → `isp_top`，`isp/isp_top.v:9`），**不是** HDMI 像素时钟；显示侧在 `I_clk`(HDMI_PIXEL_CLK) | 由 **MAIN 的适配层**实现原子请求/应答握手，源端保持整组数据至确认；是否需要 FIFO 由吞吐和保持能力决定。文字模块只接收适配后的同域字段 | 单拍脉冲直接过两级同步可能漏事件；字段分别同步不能保证整组一致，均不构成完整 CDC |
| 5 | 显示叠加区域与共用字库 | 主线已有 `osd_char_lib.v`（字库，"frozen"）与 `edge_status_osd.v`（**参数化区域 X0/Y0**、含不用除法器的三位十进制分解）；`hdmi_mixer.v:900-905` 是逐像素合成点（显示坐标 `S_x_2d/S_y_2d`，`:556-559`），`:563` 那段组合逻辑是自然接入位置；主线状态框占 (800,16)+448×72 | 框/十字与文字块区域由 MAIN 分配；我**默认**文字块放左下 (16,600)+224×34（720p），SCALE=1。**字形借 MAIN 已有实例**（我的模块不实例化字库） | 区域只影响 `X0/Y0` 参数；若 MAIN 要求另放一份字库，实测代价参考：整份 `edge_status_osd`（**含字库**）248 LUT/234 reg |
| 6 | 整机资源与时钟预算 | 历史 MAIN 完整 routed 结果未含 TARGET；独立 RGB gate 架含额外寄存器/选择器，不能作整机增量 | MAIN 提供真实顶层新资源、约束与 P&R；具体口径见 VERIFICATION.md §5 | 不能相加独立面积或用 gate WNS 推导整机 Fmax |
| 7 | 显示坐标约定 | `hdmi_mixer` 的 `S_x_2d/S_y_2d` 与 `S_video_data_2d` 对齐；mixer 有 `H_OFFSET/V_OFFSET` 参数 | 我假设 overlay 收到的 (x,y) **就是**显示坐标（与 `S_x_2d/S_y_2d` 同域同原点），**不需要**再减偏移 | 若需要减偏移，MAIN 在适配层处理；我的模块只认收到的坐标 |

### 10.1 接线示意（按默认假设）

```verilog
// 观察（S_csi_rx_clk 域，只读扇出，不串联像素）
color_target_detect #(...) u_detect (
    .I_pixel_valid(awb_O_tvalid), .I_data(awb_O_tdata[95:0]),
    .I_sof(ct_pixel_sof),               // MAIN规范化；awb user是提前通知
    .I_eol(ct_pixel_eol),               // MAIN核实与本拍像素对齐
    .I_eof(ct_frame_eof),                // ← MAIN 生成（第 3 条）
    ...);

color_target_track #(...) u_track (...);   // 同域，吃 detect 的 O_result_ready

// MAIN 待实现：准入/年龄 → 整包 CDC（容量/epoch 证明）→ DDR帧关联 → 显示整组提交 td_*
// 显示（HDMI 像素时钟域，在 hdmi_mixer 的逐像素合成处）
color_target_overlay      #(...) u_box  (.I_x(S_x_2d), .I_y(S_y_2d), ...);
color_target_text_overlay #(...) u_text (.I_x(S_x_2d), .I_y(S_y_2d),
                                          .I_count(td_count), .I_state(td_state), ...,
                                          .O_glyph_char(fnt_char), .O_glyph_row(fnt_row),
                                          .I_glyph_bits(fnt_bits));
// 合成优先级（§4.5）：文字 > 框/十字 > 基础图像
```

MAIN 还须提供规范化完整帧事务、错误/取消、唯一身份与槽代次、原子 CDC 服务能力、
框文字显示提交、区域和真实资源/时钟预算；这些尚未在主工程实现。详见 INTEGRATION.md。

### 10.2 EOF 关闭语义修复（2026-10-18）

原 `color_target_detect` 已在有效 EOF 关闭当前帧。后续 EOF 若没有新的有效 SOF，
仍产生 ready 事件，但 valid/present/class/count/坐标均为零，不能作为新观测；
无效结果中的身份沿用原接口行为，不作可信观测身份。下一有效 SOF 开始新帧。
详见 `evidence/eof_close_2026-10-18/VALIDATION.md`。

## 11. 研究候选 A（2026-10-17，未接入）

另有默认旁路的独立二值掩膜过滤原型 `color_target_support3`，见 [SUPPORT3.md](SUPPORT3.md)。
它不改变本文件前述检测/跟踪接口。启用后需要行延迟和 EOF 自动补零结算，不能与原始 RGB
按旧拍号混用；只接受完整固定尺寸光栅，截断流需复位恢复。其额外诊断口与异常帧适配
尚未成为 TEAM 接口。实际接入仍须 MAIN 确认观察点、预算、身份及 CDC/显示适配。

另有默认旁路的独立 RGB 封装 `color_target_detect_stream`，将分类/过滤/统计连接，见
[REPLAY.md](REPLAY.md)。结果延迟为旁路 EOF+1 拍，过滤 EOF+WIDTH/4+3 拍；
完整错误帧无效，截断需显式复位，可能取消前一张完整输入帧的未发布结果。
该封装和全局诊断口仍属独立实验接口，未替换原检测器或 MAIN 适配器。
