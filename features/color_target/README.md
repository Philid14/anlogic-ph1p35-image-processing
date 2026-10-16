# `features/color_target/` —— 颜色目标检测（TARGET）

对应赛题 **扩展二、进阶二**；对应协议 `TEAM_PROTOCOL_V1` 的 TARGET 角色与 §2.2 分阶段任务。
当前完成 **T1（参数化颜色分类）+ T2（匹配像素数 / 包围框 / 包围框中心 / 帧身份）+ T3（框线与中心十字的覆盖请求）+ T4（跟踪状态机与参数化防抖）**
的独立模块与自检。数据通路为 `detect → track → overlay`，三段都可独立自检。

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
| `tb/tb_color_classify.v` | 单像素分类的参数化自检台（纯组合，参数由 runner 逐个组合注入） |
| `tb/tb_color_target.v` | 检测自检台；另带两条不依赖期望值的结构断言 |
| `tb/tb_color_target_overlay.v` | 标注自检台（纯组合，无需时钟） |
| `run_color_classify.py` | 分类器自检驱动：**期望值按数学判据独立计算**，不经过模型 |
| `run_color_target.py` | 检测自检驱动：生成激励 → 仿真 → 与模型逐行比对 |
| `run_color_target_overlay.py` | 标注自检驱动 |
| `rtl/color_target_track.v` | 跟踪状态机与防抖（T4）：SEARCH / ACQ / TRACK / HOLD |
| `model/ref_color_target_track.py` | 跟踪的逐帧参考模型 |
| `tb/tb_color_target_track.v` | 跟踪自检台 |
| `run_color_target_track.py` | 跟踪自检驱动 |
| `model/ref_color_target_chain.py` | 三级链路的组合参考模型（按逐拍时序，非简单首尾相接） |
| `tb/tb_color_target_chain.v` | 链路自检台：实例化全部三个模块 |
| `run_color_target_chain.py` | 链路自检驱动 |
| `tools/simlib.py` | 五个自检脚本共用的仿真内核调用；**不写死任何人的安装路径**（协议 §5.1） |
| `INTERFACE.md` | 接口说明（状态：**接口草案**，待 MAIN 确认） |
| `INTEGRATION.md` | **给 MAIN 的一页接入说明**：接线、参数初值、期望行为、资源估计、接入步骤 |
| `GITHUB_RESEARCH.md` | 外部实现调研记录（本目录内，不写共享 `docs/`） |
| `TASK.md` | 开工记录（等价任务说明；本机无法创建 GitHub Issue） |

## 2. 跑自检

```bash
python features/color_target/run_color_classify.py          # 分类器：31 个参数组合 / 30074 像素
python features/color_target/run_color_classify.py --locked-only   # 只跑 26 条手算锁定用例（最快）
python features/color_target/run_color_target.py            # 检测：20 个用例
python features/color_target/run_color_target.py --full     # 追加一个完整 1280x720 帧
```

（五个自检脚本用法相同：`--sim iverilog|modelsim|auto`、`--msim <路径>`。）

**仿真器怎么指**（五个脚本共用 `tools/simlib.py` 的查找逻辑）：

1. **Icarus Verilog**（仓库既有 runner 的默认）：装好并放进 PATH，或用环境变量
   `COLOR_TARGET_IVERILOG_DIR=<bin 目录>`；
2. **ModelSim**：用 `--msim <win32aloem 路径>`，或环境变量 `COLOR_TARGET_MSIM`。

两者都没找到时会打印一段怎么装的说明，而不是静默失败。**脚本不写死任何人的安装路径**
（协议 §5.1：不写死负责人的 D 盘路径），也**不猜**"常见安装位置"——猜测的列表一旦命中
一个陈旧安装就会静默用错版本。保留的唯一默认值是 `C:\iverilog\bin`，那是仓库既有 runner
本来就写着的约定，不是某个人的机器布局。若 PATH 上的 `python` 是 Windows 应用商店占位符，
请改用真实解释器。

### 2.0 分类器（T1）自检

```bash
python features/color_target/run_color_classify.py
```

最近一次结果：**31/31 参数组合通过，30074 个像素逐点比对**（ModelSim ASE 14.1）。

这个脚本和另外四个不同的一点：**期望值不来自 `model/`**。判据在这里用交叉乘积重写了
一遍（第三份独立实现），所以"RTL 与参考模型一起错"这种情形它也能暴露——参考模型是照
同一套意图写的，逐拍对拍对不出这一点。

覆盖方式是参数扫描，而不是几组固定颜色：`HUE_HALF_WIDTH_DEG` 扫 0/1/2/5/10/15/25/30/
31/32/45/47/48/59/60/90（90 用来验证编译期夹取），`C_MIN`/`V_MIN` 各推到取等号的两侧，
三个 `TARGET_CLASS` 各扫一遍，每个组合喂一整张 RGB 网格（10³ 取样点）+ 手算边界像素。

其中 26 条是**手算锁定用例**：期望值由人按判据推导、算式写在注释里，脚本先断言
"手算值 == 判据实现"，任何一方写错都会立刻失败。它们钉住的是判据边界本身，例如：

| 用例 | 钉住什么 |
|---|---|
| `(255,200,0)`，W=10 → 否 / W=47 → 否 / W=48 → 是 | hue=60·200/255=47.06°，判据边界两侧各测一次 |
| `(255,42,0)` W=10 → 是 / `(255,43,0)` W=10 → 否 | 9.88° 与 10.12° 跨过 W=10 |
| `(255,255,0)` W=60 → 是 / W=59 → 否 | 黄正好 60°，夹取后 15300≤15300 取等号成立 |
| `(255,1,0)` W=0 → 否 / W=15 → 是 | W=0 表示"只认纯色"，不是"全否" |
| `(100,76,76)` C_MIN=24 → 是 / C_MIN=25 → 否 | 彩度门限含等号 |
| `(32,8,8)` V_MIN=32 → 是 / V_MIN=33 → 否 | 亮度门限含等号 |
| `(250,150,40)` W=30 → 否 / W=31 → 否 / W=32 → 是 | 31.43°，跨过默认值 |

### 2.1 检测（T2）自检

最近一次结果：**20/20 通过**（`--full` 为 21/21），覆盖：

| 用例 | 覆盖点 |
|---|---|
| `flat_white_no_target` | 无目标：`present=0` 且坐标清零 |
| `single_beat_all_red` | `sof` 与 `eof` 同拍的**单拍帧** |
| `count_below_min` | 门限边界：3 < `MIN_COUNT`(4) → 不判存在 |
| `red_rect_bbox` | 包围框与**包围框中心**（非质心）精确值 |
| `corner_origin` | 贴 `x=0 / y=0` 的边界 |
| `xmax_at_1279` | `xmax` 达 11 位上限 1279（同时也是"eof 那拍必须计入"的判据） |
| `aborted_frame` / `abort_mid_frame` / `abort_on_idle_no_leak` | 中断帧作废整帧；首拍 / 中途 / 空闲拍三条中断路径 |
| `abort_then_single_beat_ok` | **上一帧中止后紧跟的正常单拍帧必须照常发布**（见 §6 缺陷②） |
| `single_beat_aborted_still_void` | 反向：单拍帧**自己**被中止时仍须作废（防修复矫枉过正） |
| `truncated_then_ok` | 无 `eof` 的截断帧不发布，不污染下一帧 |
| `orange_out_of_hue` | hue 出窗（橙，31.43°）不计入 |
| `low_chroma` | 彩度不足（`C=20 < C_MIN=24`）不计入 |
| `dark_red` | 亮度不足（`max=28 < V_MIN=32`，彩度 26 达标）不计入 |
| `green_as_class1` / `green_not_counted_as_red` / `blue_as_class2` | `TARGET_CLASS` 真的生效，不是写死红色 |
| `frame_id_propagation` | 跨帧 `session/frame` 身份对应正确 |
| `full_1280x720` | 完整帧尺寸（`--full`） |

`abort_then_single_beat_ok`、`single_beat_aborted_still_void` 与上面三条颜色门限用例的
期望值是**硬编码**的（不经参考模型），写在 `build_cases()` 里各用例的第 4 项。

自检台还带两条不依赖期望值的结构断言：`O_result_ready` 必须恰好对应当拍 `valid&&eof`；
未发布期间结果寄存器必须保持不变（§4.3 原子发布要求）。

### 2.2 标注模块（T3）自检

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

### 2.3 跟踪模块（T4）自检

```bash
python features/color_target/run_color_target_track.py
```

最近一次结果：**21/21 通过**，逐帧比对。覆盖：

| 用例 | 覆盖点 |
|---|---|
| `never_present` | 始终无目标 → 停在 SEARCH、不显示 |
| `acquire_at_threshold` | 恰好第 `ACQ_FRAMES` 帧才转 TRACK |
| `acq_interrupted` | 确认前断掉 → 退回 SEARCH，计数清零 |
| `track_hold_reacquire` | TRACK → 丢失 → HOLD（仍显示）→ 重现 → TRACK |
| `hold_then_lost` | HOLD 连续丢满 `LOST_FRAMES` 帧 → SEARCH、不再显示 |
| `abort_frames_ignored` | `I_result_valid=0` 的中止帧**不改变状态** |
| `session_change_resets` / `session_switch_reevaluates_frame` | 会话变化 → 当帧按 SEARCH 重判，不把旧状态带进新会话 |
| `bundle_held_during_hold` | HOLD 期间显示结果保持"上次被接受"的那一帧，不被丢失帧清零 |
| `jump_rejected` / `jump_allowed_when_disabled` | `MAX_JUMP` 启用/关闭的对照 |
| `no_strobe_no_change` | 无 strobe 的拍不得改变任何状态 |
| `lost_frames_1_hides_on_first_miss` | **`LOST_FRAMES=1`：首次丢失立刻隐藏**（见 §6 缺陷③） |
| `lost_frames_2_holds_once` | `LOST_FRAMES=2`：首次丢失只到 HOLD，第二次才回 SEARCH |
| `default_lost_frames_holds_14_then_search` | 默认门限：前 14 次丢失保持 HOLD 且一直显示，第 15 次才失去 |
| `reappear_after_loss_reacquires` | 彻底失去后重现，必须**重新走一遍确认**，不能直接 TRACK |
| `counter_full_range_255` | `ACQ_FRAMES`/`LOST_FRAMES` 取满 255 时真的数到第 255 帧（510 帧序列） |
| `acq_frames_0_is_immediate` / `lost_frames_0_hides_immediately` | 取 0 与取 1 同义（"立即"，不是"永不"） |
| `acq_frames_256_clamped_to_255` | 超范围夹到 255，而不是被 `[7:0]` 截成 0（那会反变成"第一帧就确认"） |
| `negative_max_jump_is_disabled` | 负的门限夹到 0（关闭），而不是变成"任意偏移都超标" |

**参数合法范围**（都在 RTL 里编译期夹取，不产生运行时逻辑；模型侧 `clamp_frames()` /
`clamp_max_jump()` 与之逐条对应）：`ACQ_FRAMES`、`LOST_FRAMES` 取 **1..255**（底层 8 位
计数器；0 与 1 同义），`MAX_JUMP` 取 **0 或正数**（0 = 关闭）。

上表标注了"（见 §6 缺陷③）"的那组共 **10 个新增用例**，期望值都是**硬编码**的
（`build_cases()` 里各用例的第 4 项，形如 `{帧序号: {字段名: 期望值}}`），不经过参考模型。

**设计口径**（与协议一致，已在 RTL 注释中说明）：
- **中止帧不等于目标消失**：§4.3 要求检测模块丢弃中止帧结果，但把中止当丢失会误判，
  所以本模块直接跳过不评估。
- **会话变化强制清零**：§4.1 要求复位/重新采集开新 session，不得把旧会话的跟踪状态带过去；
  这里把新会话首帧当作 SEARCH 重新判定，而不是丢弃它。
- **跳变门限默认关闭**（`MAX_JUMP=0`）：它是给"画面里有第二块同色区域"准备的，
  但会让快速移动的目标被判丢，因此默认不启用，需按实板场景再定。

**自检台写法上的一个坑（值得记下）**：跟踪是逐帧驱动，若把 `$fscanf` 读到的值直接送给
DUT，第一行会因与复位释放时刻重合而跨过两个 posedge、**被评估两次**，表现是"DUT 比模型早
一帧"。改为"先读临时寄存器、再在 negedge 统一驱动"后正常。检测与标注两个自检**不受**此
影响——它们的用例里含"若被双次评估就必然失败"的项（`count_below_min`、`single_beat_all_red`），
一直是绿的。

**性质不变量（不依赖参考模型）**：除逐帧对拍外，自检还直接检查 RTL 转储本身就能判定的性质
——它们独立于我的状态机设计意图，因此能抓到"RTL 与模型一起错"的情况：

| 编号 | 性质 |
|---|---|
| P0 | `show` 必须恰好等价于 `state ∈ {TRACK, HOLD}` |
| P1 | 显示时，结果必须来自某个**被接受**的帧（`strobe && rvalid && present`） |
| P2 | 显示时坐标合法：`min<=max`、在 1280×720 内、`count>=1` |
| P3 | `SEARCH` 不得显示 |
| P4 | `change` 必须恰好表示"状态发生了变化"（含会话变化的语义） |
| P5 | 连续 `HOLD` 期间结果不得变化 |

**这六条都做过反向验证**（喂进"故意写错"的转储确认能抓到、喂正确转储确认无误报）：
P1/P0/P4 直接构造违反即命中；P2 用"被接受但 `xmin>xmax`"的 bundle 独立证明；
P5 用"两个 bundle 都合法来源、但 HOLD 期间被换掉"独立证明——这两条刻意绕开 P1，
否则会被 P1 顺带抓到、无法证明它们自己有效。

### 2.4 三级链路端到端自检（detect → track → overlay）

```bash
python features/color_target/run_color_target_chain.py
```

最近一次结果：**PASS，396 拍逐拍比对**。用 6 帧合成画面驱动整条链路：无目标 → 红块左移
→ 中 → 右 → 无目标 → 红块重现。实测状态迁移：

```
拍   0: SEARCH  show=0
拍 130: ACQ     show=0     ← 第 1 次确认计数
拍 262: TRACK   show=1     ← 连续 3 帧确认
拍 328: HOLD    show=1     ← 目标消失，框保持
拍 394: TRACK   show=1     ← 目标重现
```

**这条自检刻意按逐拍时序接，而不是"把三个模型首尾相接"**，因为协议 §4.3 特意警告过
"不能把上一帧的框悄悄标成当前帧检测结果"。实际时序是：

- detect 的结果在 **eof 那一拍之后 1 拍**才发布（`O_result_ready` 单拍脉冲）；
- track 在那个脉冲那一拍消费它，所以 **track 的输出在 eof 之后 1 拍才更新**；
- overlay 是纯组合的，于是**框在 eof 之后 1 拍才变**，而那一拍仍属于本帧的最后像素。

**这条要交给 MAIN**：如果直接把 overlay 接在 track 上，本帧最后 1~2 个像素会用到刚发布的
新结果。要完全避免，需要在**帧边界**把结果寄存一级再喂给 overlay（协议 §4.3 要求的
"读出时使用匹配结果"）。本自检台按其**现有直接接线**测量并如实记录了这个现象，没有在
测试里替 MAIN 加适配层——免得掩盖真实接线行为。

**这条自检的价值**：它证明了我自己三个模块之间的接口接法（含 `O_show` 到 overlay 两行接线、
帧身份的传递、HOLD 期间 overlay 用的是保持住的框）是正确的，也给 MAIN 提供了一份可照抄的
接线与期望行为参考。**但它仍是模拟输入，不代表整机或上板。**

## 3. 为什么这样设计

**为什么用 HSV 扇区法而不是 RGB 阈值**：协议 §2.2 要求"不修改主线 AWB/曝光来迁就检测"，
而 RGB 阈值随增益与白平衡漂移；hue 与亮度无关。公开资料的通行做法也是 HSV（见
`GITHUB_RESEARCH.md`）。

**为什么不需要除法器**：设 `C = max-min`、`d` 为另两个通道之差的绝对值，在目标通道为最大
的扇区内有 `|hue 偏移| = 60°·|d|/C`，因此 `|hue 偏移| ≤ W` 等价于**交叉乘积**判据
`60·|d| ≤ W·C`。两侧都是常数乘法（`60` 是常数，`W` 是参数），TD 会把它们分解成移位
加减——**无除法器、无 DSP 乘法器**，也避免引入厂商 divider IP。

（早期版本为省一次乘法，把 `60/W` 预合并成一个 Q8 常数斜率。那个形式的斜率随 `W` 变小
而变大，`W=10` 时 `255×1536=391680` 需要 19 位，却被固定 18 位承载，乘积被截断后判据
失效。交叉乘积两侧上界恒为 `60×255`，**位宽与 `W` 无关**，因此弃用斜率形式。详见 §6。）

**为什么不做形态学滤波**：T1 的前提是"单个主要颜色目标、背景较易区分"；在还没有实板
噪声数据时凭猜测加滤波器会引入无法归因的变量。去噪与防抖按协议属 **T4**，留到有实测
数据之后再做。

## 4. 资源估计（**估计值，未经综合验证**）

按逻辑逐项估算：4 路分类器约 450 LUT6；累加与比较约 80–150 LUT6 + 约 20 位进位链；
结果锁存约 120 个触发器。

每路分类器含两个常数乘法（`d×60` 与 `C×W`），TD 会分解成移位加法：`60 = 2⁶−2²`，
默认 `W=30 = 2⁵−2¹`，各是一个 14 位减法器的量级（十几 LUT6），四路合计多出几十 LUT6。
**这里要如实说明一处变化**：旧版把判据写成"常数斜率 × 差值"，`W=30` 时斜率恰是 2 的幂、
乘法退化成纯移位，看着更省；但那个形式在小 `W` 下会溢出（§6 缺陷①）。改成交叉乘积后
多出这点减法器开销，换来的是**位宽与 `W` 无关**，代价在下方估值区间的噪声范围内。

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

完整清单见 `INTERFACE.md` 第 9 节，其中对外必须原样转述的是：

1. **整帧所有匹配像素合成一个包围框**，不分离多目标；画面中两块同色区域会被并进同一个框。
2. **无形态学/游程滤波**，孤立高饱和噪点会拉大包围框（T4 处理）。
3. **中心是包围框中心，不是像素质心**。
4. 强偏色下阈值可能失效，需重新评估 `HUE_HALF_WIDTH_DEG`，**不得改主线 AWB/曝光**。
5. **未接入主线、未上板。**

## 6. 本轮修复（审查意见 ①②③）

三处缺陷都在提交 `8c5d34f` 上审出。三处都是**先复现、再修、再补回归**；并且把**修复前的
RTL 喂给新回归确认它确实会失败**（做法：只 `git stash` 掉 `rtl/` 与 `model/` 的改动、
保留新测试跑一遍），所以"这些回归真的覆盖了这些缺陷"不是推断。

### 缺陷① 色相判定的乘积溢出（`color_classify.v`）

旧判据 `diff_abs × HUE_SLOPE_Q8 ≤ chroma × 256`，其中斜率是 `60·256/W`：`W` 越小斜率越大，
`W=10` 时为 1536，`255×1536 = 391680` 需要 19 位，却固定用 18 位承载，乘积被截断。
审查给的复现成立：`RGB=(255,200,0)`、`W=10` → `d=200`、`200×1536 = 307200` 截成
`45056 ≤ 255×256 = 65280`，于是 hue 实际 **47.06°** 的橙色被判成红色。

修复：改用交叉乘积 `60·|d| ≤ W·C`，两侧上界都是 `60×255 = 15300`，14 位足够且
**位宽与 `W` 无关**；`W` 在编译期夹到 `0..60`。

修复前的实测影响面（新回归 `run_color_classify.py`）。这个表比审查意见更细 ——
失配只在 `W<15` 出现，`W≥15` 完全干净，与旧注释自述的上界 `255×1024` 相符。
每个 `W` 组合的像素数是 1000（10³ 网格）加上该组合的手算边界像素：

| `W` | 失配/像素数 | 性质 |
|---|---|---|
| 0 | 295/1005 | 旧公式 `(60·256 + W/2)/W` **除零** → 输出 `x`（未定态），比"算错"更糟 |
| 1 | 20/1003 | 误报：hue 高达 60° 的像素被判成红 |
| 2 | 6/1003 | 误报 |
| 5 | 18/1003 | 误报 |
| 10 | 24/1006 | 误报，含审查给的 `(255,200,0)` |
| ≥15 | 0 | 斜率 ≤1024，不溢出 |

三个 `TARGET_CLASS` 与各档 `C_MIN`/`V_MIN` 在 `W=10` 下都有失配（共 9/31 个参数组合失败）。
修复后 **31/31 组合、30074 像素**全部与判据一致。

### 缺陷② 中止状态泄漏到紧随其后的单拍帧（`color_target_detect.v`）

旧写法 `eff_abort = aborted_f | I_frame_abort`。`aborted_f` 是上一帧留下的粘滞标志，
新帧开始那一拍仍读到它，于是新帧被误判为中止帧。多拍帧侥幸没事（`start_f` 那一拍就把
`aborted_f` 清掉，而那一拍不发布结果），**`sof` 与 `eof` 同拍的单拍帧直接踩中**：
整帧结果被丢弃（`valid=0`）。

修复：`eff_abort = start_f ? I_frame_abort : (aborted_f | I_frame_abort)` ——
新帧开始时只看**本帧**的中止输入。

回归 `abort_then_single_beat_ok`：中止帧之后接一帧正常单拍全红帧、`MIN_COUNT=1`，
期望 **`valid=1`、`present=1`、`count=4`**（硬编码，不经模型）。修复前该用例失败。
反向用例 `single_beat_aborted_still_void` 锁住"单拍帧**自己**被中止时仍须作废"，
防止修复矫枉过正。

### 缺陷③ 门限对 TRACK 的首次丢失不生效（`color_target_track.v`）

`S_TRACK` 收到首次丢失时**无条件**进 `HOLD`，没有走门限判断（`S_HOLD` 分支却有），
于是 `LOST_FRAMES=1` 时目标不会立刻隐藏，要多丢一帧才消失 —— 比配置要求的晚一帧，
也与其他门限的行为不一致。修复后该分支与 `S_HOLD` 一致地做门限判断。

顺带把 `ACQ_FRAMES` / `LOST_FRAMES` / `MAX_JUMP` 的合法范围在编译期夹取（见 §2.3）：
8 位计数器上 `ACQ_FRAMES=256` 会被 `[7:0]` 截成 0，反变成"第一帧就确认"，与"要 256 帧"
完全相反。

回归 10 条（见 §2.3 表）。修复前 `lost_frames_1_hides_on_first_miss` 与
`reappear_after_loss_reacquires` 失败，转储是：

```
帧1 state: got=3 want=0     ← 应为 SEARCH，实际停在 HOLD
帧1 show:  got=1 want=0     ← 因此仍在显示，没有立刻隐藏
```

### 证据口径（对外必须原样转述）

以上全部是**独立仿真**（ModelSim ASE 14.1，模拟输入，逐拍/逐像素比对）。
**整机接口、统一 OSD、资源与时序、上板效果均未验证，仍需 MAIN 集成确认。**
§4 的资源数字是逐项推算，不是综合结果。
