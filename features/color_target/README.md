# `features/color_target/` —— 颜色目标检测（TARGET）

对应赛题 **扩展二、进阶二**；对应协议 `TEAM_PROTOCOL_V1` 的 TARGET 角色与 §2.2 分阶段任务。
当前完成 **T1（参数化颜色分类）+ T2（匹配像素数 / 包围框 / 包围框中心 / 帧身份）+ T3（框线与中心十字的覆盖请求）+ T4（跟踪状态机与参数化防抖）**
的独立模块与自检。数据通路为 `detect → track → overlay`，三段都可独立自检。

> ⚠️ **状态口径（协议 §5.3.4、§6 要求如实区分）**：
> 本功能**独立模块完成、模拟事件验证通过**。**未接入主线、未生成 bit、未上板。**
> 不得对外表述为"已整机完成"或"进阶二已完成"。

当前入口：**[验证方法](VERIFICATION.md)**、[接入摘要](INTEGRATION.md)、
[实板观察与回报](board/OBSERVATION_GUIDE.md)。A1已修复；A2新增经批准的
[独立guard](integration/TRACK_GUARD_INTERFACE.md)，旧track未包装路径仍保留六项缺口。
[帧事务实施准备](integration/FRAME_TRANSACTIONS_V1.md)提供联合模型、生产RTL联动和MAIN具体确认包；
MAIN接线、CDC/DDR/显示时序、生产年龄及整机验收仍未完成。
历史章节记录当时实验；当前集成状态与资源口径以验证入口及对应版本证据为准。

---

本次上传/接入/板测请从 [MAIN_HANDOFF](board/MAIN_HANDOFF.md) 开始。
包含guard与联合验证的新完整命令为 `run_verification.py --profile handoff --sim modelsim --msim <目录> --out <新目录>`。
当前尚无含TARGET的整机bit，由MAIN队友接入后构建与上板。

## 1. 目录

| 路径 | 内容 |
|---|---|
| `rtl/color_classify.v` | 单像素颜色分类（HSV 扇区法，无除法器） |
| `rtl/color_target_detect.v` | 检测顶层：4 路并行分类 + 帧内统计 + 帧末原子锁存 |
| `rtl/color_target_support3.v` | 候选 A：默认旁路的独立 4PPC 二值中心支持过滤；未接入检测器 |
| `rtl/color_target_detect_stream.v` / `rtl/color_target_mask_stats.v` | 独立 RGB→可选过滤→固定光栅统计，默认关闭过滤；未接入主线 |
| `REPLAY.md` / `REPLAY_MAIN_CHECKLIST.md` | RGB 回放、取消/复位、素材格式及待 MAIN 确认项 |
| `run_color_target_replay.py` / `run_replay_data_checks.py` | 全链路回放、原 RTL 旁路对照、逐帧评价与数据契约检查 |
| `SUPPORT3.md` | 原型接口、两行 RAM/无消隐帧尾结算、限制与复现 |
| `model/ref_color_target_support3.py` | 不复制 RTL 调度器的帧集合 oracle |
| `tb/tb_color_target_support3.v` / `run_color_target_support3.py` | 四个 lane 对齐的 512 邻域穷举、完整帧、默认旁路和原语网表自检 |
| `rtl/color_target_overlay.v` | 标注模块（T3）：框线 + 中心十字的覆盖请求，纯组合、不加流水级 |
| `rtl/color_target_text_overlay.v` | **文字标注**：坐标 + 像素数 + 状态的文字块（T3 的文字部分），区域参数化、不实例化字库 |
| `model/ref_color_target.py` | 位精确 Python 参考模型（与检测 RTL 逐拍等价） |
| `model/ref_color_target_overlay.py` | 标注的逐像素参考模型（单独成文件，与检测解耦） |
| `model/ref_color_target_text.py` | 文字标注的参考模型；可解析**主线真字库**做逐位比对 |
| `tb/tb_color_classify.v` | 单像素分类的参数化自检台（纯组合，参数由 runner 逐个组合注入） |
| `tb/tb_color_target.v` | 检测自检台；另带两条不依赖期望值的结构断言 |
| `tb/tb_color_target_overlay.v` | 标注自检台（纯组合，无需时钟） |
| `tb/tb_color_target_text_overlay.v` | 文字标注自检台；含"沉降-扫描"两段式激励（等十进制转换跑完再扫像素） |
| `tb/tb_color_target_text_updates.v` | 逐拍读取公开字形端口，检查忙时更新和复位下的整组一致性 |
| `tb/ct_text_font_stub.v` | 自检用的字形**桩**（不依赖主线任何文件） |
| `tb/ct_text_font_real.v` | 把**主线共享字库** `osd_char_lib.v` 包成同一字形端口（只读引用，不改它） |
| `run_color_classify.py` | 分类器自检驱动：**期望值按数学判据独立计算**，不经过模型 |
| `run_color_target.py` | 检测自检驱动：生成激励 → 仿真 → 与模型逐行比对 |
| `run_color_target_overlay.py` | 标注自检驱动 |
| `run_color_target_text_overlay.py` | 文字标注自检驱动（可 `--font real` 用主线真字库逐位比对） |
| `run_color_target_text_updates.py` | 文字更新动态回归；不复制 RTL 转换状态机，支持 `--rtl` 检查旧实现 |
| `rtl/color_target_track.v` | 跟踪状态机与防抖（T4）：SEARCH / ACQ / TRACK / HOLD |
| `model/ref_color_target_track.py` | 跟踪的逐帧参考模型 |
| `tb/tb_color_target_track.v` | 跟踪自检台 |
| `run_color_target_track.py` | 跟踪自检驱动 |
| `model/ref_color_target_chain.py` | 三级链路的组合参考模型（按逐拍时序，非简单首尾相接） |
| `tb/tb_color_target_chain.v` | 链路自检台：实例化全部三个模块 |
| `run_color_target_chain.py` | 链路自检驱动 |
| `tb/tb_color_target_chain_render.v` | 渲染台：把 4 个 lane **逐个**送进 overlay，导出合成后的逐像素输出 |
| `render_color_target_frames.py` | 渲染驱动：合成多帧画面 → 逐像素回归 → 输出 PNG 帧图 |
| `tools/simlib.py` | 六个自检脚本共用的仿真内核调用；**不写死任何人的安装路径**（协议 §5.1） |
| `INTERFACE.md` | 接口说明（状态：**接口草案**，待 MAIN 确认） |
| `INTEGRATION.md` | 给 MAIN 的接入摘要：检测路径选择、未实现依赖、参数与资源证据边界 |
| `DEMO_STEPS.md` | 独立演示、当前视频基线板测与未来 TARGET 整机验收步骤 |
| `GITHUB_RESEARCH.md` | 外部实现调研记录（本目录内，不写共享 `docs/`） |
| `TASK.md` | 开工记录（等价任务说明；本机无法创建 GitHub Issue） |

## 2. 跑自检

```bash
python features/color_target/run_color_classify.py          # 分类器：40 个参数组合 / 39079 像素
python features/color_target/run_color_classify.py --locked-only   # 只跑 31 条手算锁定用例（最快）
python features/color_target/run_color_target.py            # 检测：24 个用例
python features/color_target/run_color_target.py --full     # 追加一个完整 1280x720 帧
python features/color_target/run_color_target_overlay.py
python features/color_target/run_color_target_text_overlay.py     # 文字标注（默认用主线真字库）
python features/color_target/run_color_target_text_updates.py     # 忙时更新、复位和整组发布
python features/color_target/run_color_target_support3.py         # 独立候选 A；不改变现有检测行为
python features/color_target/run_color_target_support3.py --geometry 1280x720
python features/color_target/run_replay_data_checks.py
python features/color_target/run_color_target_replay.py --full --out <目录> # 合成 RGB 控制；相机结论保留
python features/color_target/run_color_target_track.py
python features/color_target/run_color_target_chain.py
python features/color_target/render_color_target_frames.py --out <目录>   # 渲染 10 帧 PNG
```

（仿真脚本共用 `--sim iverilog|modelsim|auto`、`--msim <路径>`。）

**仿真器怎么指**（七个脚本共用 `tools/simlib.py` 的查找逻辑）：

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

最近一次结果：**40/40 参数组合通过，39079 个像素逐点比对；等价性断言 8/8 通过**（ModelSim ASE 14.1）。

这个脚本和另外五个不同的一点：**期望值不来自 `model/`**。判据在这里用交叉乘积重写了
一遍（第三份独立实现），所以"RTL 与参考模型一起错"这种情形它也能暴露——参考模型是照
同一套意图写的，逐拍对拍对不出这一点。

覆盖方式是参数扫描，而不是几组固定颜色：`HUE_HALF_WIDTH_DEG` 扫 0/1/2/5/10/15/25/30/
31/32/45/47/48/59/60/90（90 用来验证编译期夹取），`C_MIN`/`V_MIN` 各推到取等号的两侧
**并再往外推到越界**（512、-1、300、-1），三个 `TARGET_CLASS` 各扫一遍（外加越界值 3/7），
每个组合喂一整张 RGB 网格（10³ 取样点）+ 手算边界像素。

其中 31 条是**手算锁定用例**：期望值由人按判据推导、算式写在注释里，脚本先断言
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
| `C_MIN=512` → 否 / `C_MIN=-1` → 是 | **夹取不是位截断**：截断会把 512 变成 0（判成命中）、把 -1 变成 511（判成否），方向正相反 |
| `V_MIN=300` → 否 / `V_MIN=-1` → 是 | 同上（截断会变成 44 / 255） |
| `TARGET_CLASS=3`、`=7` → 与红完全一致 | 越界类比退化到红，不是"选不中任何类"的静默失效 |

除逐像素比对之外，还有 **8 条等价性断言**（不依赖判据、也不依赖模型，直接比两次 RTL 运行的
转储）：`C_MIN=512` 必须与显式 `511` 逐像素一致、`W=90` 必须与显式 `60` 一致、
`TARGET_CLASS=3/7` 必须与红一致，等等。两侧没有共同激励时会**报故障而不是静默跳过**。

### 2.1 检测（T2）自检

最近一次结果：**24/24 通过**（`--full` 为 25/25），覆盖：

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
| `mincount_over_20bit_is_clamped` | `MIN_COUNT=2²⁰` 夹到 `2²⁰-1`（不夹会被 20 位截成 0，反变成"零命中也算存在"） |
| `tiny_geometry_xw2_yw2` / `small_geometry_xw3_yw2` | `XW=2`/`YW=2` 与 `XW=3`/`YW=2` 的小几何 —— **旧实现在这里直接编译失败**（拍内 x0+k 的显式零扩展是负数重复次数） |
| `frame_id_propagation` | 跨帧 `session/frame` 身份对应正确 |
| `stray_eof_after_complete_frame` | EOF 关闭帧；后续缺 SOF 的 EOF 无效，下一正常单拍帧恢复 |
| `full_1280x720` | 完整帧尺寸（`--full`） |

`abort_then_single_beat_ok`、`single_beat_aborted_still_void` 与上面三条颜色门限用例的
期望值是**硬编码**的（不经参考模型），写在 `build_cases()` 里各用例的第 4 项。

自检台还带两条不依赖期望值的结构断言：`O_result_ready` 必须恰好对应当拍 `valid&&eof`；
未发布期间结果寄存器必须保持不变（§4.3 原子发布要求）。

### 2.2 标注模块（T3）自检

```bash
python features/color_target/run_color_target_overlay.py
```

最近一次结果：**10/10 通过；参数夹取等价性 5/5 通过**。逐像素比对（每例约 0.3k–27k 个采样点），覆盖：

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

参数合法范围（编译期夹取，不产生运行时逻辑）：`BOX_THICK >= 1`、`CROSS_THICK >= 1`、
`CROSS_ARM >= 0`。**5 条夹取等价性断言**不依赖模型，直接比两次 RTL 运行：`BOX_THICK=0`
与 `=-3` 必须与 `=1` 逐像素一致（各 27984 像素）、`CROSS_THICK=0/-2` 与 `=1` 一致、
`CROSS_ARM=-5` 与 `=0` 一致。这条能独立抓住"夹取写成了位截断"或"夹了但没接到判据上"。

`BOX_THICK=0` 的语义是**夹到 1**，不是"没有框"：让框消失应当由 `I_target_present=0`
表达（协议 §4.3 的语义），而不是把线宽设成 0 让判据悄悄失效。

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
- **当前仅有效结果触发会话重判**：新 session 有效首帧按 SEARCH 判定；无效新 session 不清旧状态，
  旧 session 有效包也可回切。原回归没有证明完整 session 屏障；A2 提案仍待实现。
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

此自检按逐拍时序比较既有同域直接连接。以 EOF 采样沿为 0，原检测器在该沿后发布，
track 在下一沿消费，组合 overlay 随输入更新；输入最后拍和同步消费时刻不能混为一谈。
测试台不是实际 HDMI 扫描，不能据此断言整机“最后几个像素跳框”。
MAIN 必须建立帧身份/DDR代次关联，在扫描前完成文字准备并整组提交。
仅加边界寄存器不能证明同帧，具体见 [接口草案](integration/MAIN_CONTRACT_DRAFT.md)。

### 2.5 链路渲染（把行为画出来）

```bash
python features/color_target/render_color_target_frames.py --out <输出目录>
```

跑一条 10 帧的合成画面序列，把**每一帧的最终像素**（overlay 合成之后）写成 PNG，于是
"框在哪里、什么时候出现、什么时候保持、什么时候消失"可以直接看。同时它还是一次
**比 §2.4 更严的回归**：逐拍比对状态与显示之外，还把**每个像素的 4 个 lane 全部**与链路
模型比对（§2.4 那个台只在 lane0 的坐标上采一次）。

最近一次结果：**逐拍 192010 拍、逐像素 768000 像素与链路模型一致**，
10 帧渲染到 `outputs/`（`320x240`、`XW=9 / YW=8`——顺带证明这三个模块的参数化是真的，
默认参数是 `XW=11 / YW=10` 的 `1280x720`）。

三件渲染出来的事实，比文字更清楚：

1. **该演示的框使用旧观测**。第 3 帧红方块在右侧、框在中间，体现直接接线测试架缺少同帧关联。
   该现象不作为新整机验收标准；MAIN 要匹配真实 frame_key，若显示历史观测须显式标识且满足获批年龄。
2. **孤立噪点会把框撑爆**：第 4 帧给目标和背景加了 40 个孤立单像素高饱和红点，
   包围框当场从 `60×60` 变成 `309×209`（几乎整幅 320×240），`count` 从 3600 变 3640。
3. **一次噪声会污染之后若干帧**：因为框只在"被接受"的帧更新，第 4 帧这个被撑大的框
   会一直被 HOLD 保持（渲染里的第 5、6 帧都是它），直到有新的被接受帧才刷新。

> ⚠️ 画面是**合成**的（几何、颜色、噪声都按判据构造），**不是实拍**，不代表上板效果。
> 它的用途是让行为可见 + 顺带回归。输出目录里有一份 `index.md` 逐帧记录状态与框的来源。

### 2.6 文字标注（T3 的文字部分）自检

```bash
python features/color_target/run_color_target_text_overlay.py               # 默认用主线真字库
python features/color_target/run_color_target_text_overlay.py --font stub   # 只用桩，不依赖主线
```

最近一次结果：**28/28 用例通过，307078 像素逐点比对**（真字库与桩两条路径都通过）。

赛题（选题二）扩展要求(2) 要求"叠加检测结果与**文字说明**"、高阶挑战项(2) 叫"动态目标跟踪与
**坐标叠加**"——这一节补的就是那半句。画面内容两行：

```
RED X0159 Y119
N003600 TRACK
```

§2.5 的渲染已经把这块文字画进帧图（用的就是主线真字库），可以直接看效果。

三个设计要点（都写进了 RTL 注释）：

1. **不实例化字库**（协议 §3：共享 OSD 归 MAIN）：字形通过 `O_glyph_char` / `O_glyph_row` /
   `I_glyph_bits` 三个端口**借** MAIN 已有的 `osd_char_lib` 实例，不复制也不改写。
   参考代价：整份 `edge_status_osd`（**含字库**）在主线综合报告里是 **248 LUT / 234 reg**。
2. **必须在显示侧合成**：主线现有的 `edge_status_osd` 在 ISP→DDR 之前，因为它显示的是"配置值"
   （帧首就知道）；而**目标检测结果要帧末才有**，塞不进本帧的像素流。MAIN 需要为显示侧转换
   预留消隐时间，不能假定总有一整帧余量。
3. **十进制不用除法器**：逐位双-dabble，每组 3 轮共 70 拍。开始时快照数字、状态和明暗，
   最后一轮结束后整组发布；忙时保持旧显示，再处理最新稳定值（最多 140 拍）。
   数字、状态或明暗变化均会自动触发，不要求接 `I_update`；中间变化允许合并。
   此机制不替代 MAIN 的原子 CDC、帧身份匹配或显示帧边界适配（见 §9）。

**最有价值的一条验证是用真字库逐位比对**：字形位的索引约定（`[15]` 最左、每行 16 位、共 16 行）
是本模块与字库之间**唯一的隐式契约**，用桩测不出来——桩用什么约定，模块就跟着用什么约定，
两边一起错也发现不了。所以模型里的 `parse_font()` 直接解析主线的 `osd_char_lib.v`（**只读**），
逐位预测每个像素再与 RTL 比对：**接入前就把这条约定钉死了**。

用例覆盖：十进制进位边界（0/1/9/10/99/100/999/1000/9999/99999/100000/921600/999999/1048575）、
**饱和**（`count` 超 6 位、`x` 超 4 位、`y` 超 3 位都饱和而不是截断）、四个状态名、
`I_show` 的亮/暗两档、`SCALE=1/2`、区域移到别处、`ENABLE=0`、每行字符数 10/14/20，
以及"**区域外一个像素都不覆盖**"这条只看转储的独立断言。

## 3. 为什么这样设计

**为什么用 HSV 扇区法而不是 RGB 阈值**：协议 §2.2 要求"不修改主线 AWB/曝光来迁就检测"，
而 RGB 阈值随增益与白平衡漂移。理想统一通道增益下色相比值较稳定，但量化、低彩度噪声、
饱和与 AWB 的不同通道增益仍会改变判定，不能称为绝对光照不变。公开实现参照见
`GITHUB_RESEARCH.md`；下一阶段比较见 `research/ROADMAP.md`。

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

## 4. 资源与时序证据

| 范围 / 源版本 | 已有结果 | 适用边界 |
|---|---|---|
| RGB 独立 gate 架 / 5565545 | 旁路 918 LUT/579 reg/0 ERAM/0 DSP；过滤 1224/950/1/0 | 含影子寄存器和观测选择器，10 ns 人工时钟、74 未绑定 I/O；不是整机增量或 routed Fmax |
| 文字 gate / 172815e | 282 LUT/194 reg/0 ERAM/0 DSP | 独立文字模块，不等于全套显示预算 |
| 历史 MAIN routed / dff499a | LUT6 14724/21216、FF 14417、Slice 16473/21216、ERAM39、DSP9；SWNS/HWNS .100/.020 ns | 未含 TARGET，STA覆盖96.14%，板测待；不得混用旧 gate LUT 口径 |

原先全功能约 900–1400 LUT 的估算不再用于预算判断；历史首轮常数乘法曾映射成 8 DSP，
后经等价移位加减取得 0 DSP，必须引用具体工具与源码版本，不能仅凭数学形式推断映射。
观察者无反压仍需满足真实时序；并接产生的扇出/布线影响也需整机评估。
本轮 A1 后没有重新综合；MAIN 接入后须给出真实顶层资源、时钟、约束与 P&R。
完整报告、历史失败和边界见 [验证入口 §5](VERIFICATION.md#5-资源与板测证据分开引用)。

## 5. 已知限制

完整清单见 `INTERFACE.md` 第 9 节，其中对外必须原样转述的是：

1. **整帧所有匹配像素合成一个包围框**，不分离多目标；画面中两块同色区域会被并进同一个框。
2. **无形态学/游程滤波**，孤立高饱和噪点会拉大包围框。§2.5 的渲染把这个后果量化了：
   在 320×240 的合成画面里，40 个孤立单像素红点就把包围框从 `60×60` 撑到 `309×209`
   （几乎整幅画面）。**而且它不是只影响一帧**：框只在"被接受"的帧更新，被撑大的那个框
   会被 HOLD 一直保持到有新的被接受帧为止（渲染的第 5、6 帧都是它）。
   是否需要在像素级加去噪，等实板噪声数据——凭猜测加滤波器会引入无法归因的变量。
3. **中心是包围框中心，不是像素质心**。
4. 强偏色下阈值可能失效，需重新评估 `HUE_HALF_WIDTH_DEG`，**不得改主线 AWB/曝光**。
   §2.5 的渲染给了一个具体例子：白平衡把红目标推到 hue 30.7°（刚越出默认 ±30°）时，
   检测丢目标，而框还停留在上一帧的位置。
5. **未接入主线、未上板。**
6. **TRACK 身份/年龄未闭环**：重复/乱序可被接受，无效与沉默不按时间失效，session 权威未落实；见 A2 提案。
7. **文字颜色名固定为 RED**：当前演示按默认红色配置；绿/蓝分类及结果标签通过不等于文字随类别变化。

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

## 7. 参数健壮性收敛与渲染验收（本轮）

上一轮把审查意见 ①②③ 修掉之后，顺着同一条思路把**所有参数**都过了一遍：凡是越界取值会
造成"静默失效"的，一律在编译期夹取，并给每个夹取配一条**不依赖模型**的回归。
之所以要一轮专门做这件事，是因为审查意见①本身就是一个参数越界导致判据失效的例子，
而同一类问题当时在别的参数上还留着：

| 参数 | 越界时的旧行为 | 现在 |
|---|---|---|
| `C_MIN` | `512` 被 9 位截成 `0` → 本意"严到不可能命中"变成"完全不滤彩度"；`-1` 截成 `511` → 变成"永不命中" | 夹到 `0..511` |
| `V_MIN` | `300` 截成 `44`（变成几乎不滤）、`-1` 截成 `255`（变成永不命中） | 夹到 `0..255` |
| `MIN_COUNT` | `2²⁰` 被 20 位截成 `0` → "零命中也算存在"，输出中性元包围框垃圾坐标 | 夹到 `1..2²⁰-1` |
| `BOX_THICK` | `0`/负数让四条带退化成空集，判据悄悄失效 | 夹到 `>=1` |
| `CROSS_THICK` | `0` 靠整数除法截断"碰巧"等于 1；负数靠空集"碰巧"不画 | 夹到 `>=1` |
| `CROSS_ARM` | 负数靠空集"碰巧"不画 | 夹到 `>=0` |
| `XW` / `YW` | **`XW<3` 直接编译失败**（拍内 `x0+k` 的零扩展是负数重复次数） | 任意 `>=1` 都能编译；`XW=2/YW=2`、`XW=3/YW=2` 已实测 |
| `ACQ_FRAMES` / `LOST_FRAMES` / `MAX_JUMP` | 上一轮已修（见 §2.3） | 同左 |

**"碰巧对"不是对**：`CROSS_THICK=0` 那两条属于"写 0 却按 1 跑"，行为虽对但没有任何保证，
换个数或换个工具就可能变；夹取把语义写死。所有夹取都是常量折叠，不产生运行时逻辑。

除了逐像素比对，本轮还引入了两类**不依赖模型、也不依赖判据**的断言——直接比两次 RTL 运行的
转储（"参数等价性"）：

- 分类器 8 条：`C_MIN=512` 必须与显式 `511` 逐像素一致、`W=90` 与 `60` 一致、
  `TARGET_CLASS=3/7` 与红一致……两侧没有共同激励时**报故障而不是静默跳过**；
- 标注 5 条：`BOX_THICK=0/-3` 必须与 `=1` 一致（各 27984 像素）、`CROSS_THICK=0/-2` 与 `=1`、
  `CROSS_ARM=-5` 与 `=0`。

同时新增 **§2.5 的渲染工具**：它把链路在 10 帧合成画面上的输出画成 PNG，既是"让行为可见"
的验收素材，也是一次比链路自检更严的回归（逐像素比对 4 个 lane，而不只是 lane0），
并且跑在 `XW=9/YW=8` 的非默认几何上——参数化不再只是"声明支持"。

本轮实测：分类器 40/40 组合 + 8/8 等价性（39079 像素）、检测 23/23（`--full` 24/24）、
标注 10/10 + 5/5 等价性、跟踪 21/21、链路 396 拍、渲染 192010 拍 / 768000 像素全部通过。

**证据口径同上**：全部为独立仿真；整机接口、统一 OSD、资源时序、上板效果仍需 MAIN 集成确认。

## 8. 文字标注与交付物补齐（再一轮）

上一轮末尾列的"下一步"里，**像素级去噪建议等实拍数据**（理由见 §5 限制 2），所以这一轮做的是
另外两件价值更高、且不依赖实板的事：**把赛题要求的"文字说明/坐标叠加"补上**，
以及**把协议点名的交付物补全、把接口疑点查实**。

### 8.1 文字标注（新增 `rtl/color_target_text_overlay.v`）

赛题原文（选题二）里，扩展要求(2) 是"…并在输出画面中叠加检测结果与**文字说明**"，
高阶挑战项(2) 直接叫"动态目标跟踪与**坐标叠加**"。在此之前，这两句里的"文字/坐标叠加"
**没有任何人交付**——我原来把它写成"文字归 MAIN 的统一字库，这是明确边界"，
按协议的权责划分（§4.5）站得住，但从赛题措辞看是个**值得重新评估的边界**：MAIN 忙不过来时
就成了"谁都没做"，而评分标准特别强调"演示直观性"和"现场展示效果"。

现在补上了，**做法刻意克制**（细节见 §2.6）：

- **区域、放大倍数、字符数、颜色全部参数化**，默认放左下角，`ENABLE` 可关；
- **不实例化字库**：字形借 MAIN 已有的 `osd_char_lib` 实例（协议 §3 共享 OSD 归 MAIN），
  所以不复制 248 LUT 的共享件、不改写它；
- **不碰 mixer、不绑引脚/按键**（§4.5），合成顺序仍由 MAIN 决定；
- 假设不成立也不会影响现有行为：不接它、或 `ENABLE=0`，其余功能一字不变。

**接入前就验证到了什么**：模型里的 `parse_font()` 解析主线**真实字库**，逐位预测每个像素
再与 RTL 比对，28 个用例 / 307078 像素全过——这钉死了"字形位索引 `[15]` 最左"这条
**唯一的隐式契约**（用桩测不出：桩用什么约定，模块就跟着用什么约定）。渲染出的帧图用的是真字库，
直接能看到接入后的样子。

### 8.2 交付物与接口

- **`DEMO_STEPS.md`（新增）**：协议 §2.2 把"演示步骤"列为 TARGET 交付物，此前缺失。
  内容是 A 级仿真演示（五步 + 对着帧图的讲解脚本）与 B 级上板演示（步骤表 + 降级方案 + 现场话术）。
- **`INTERFACE.md` §10 重写**：原来是 6 条"待确认"，现在每条都给出**我在主线代码里查到的事实
  （带 `文件:行号` 证据）**、**我的默认假设**、**假设不成立的影响**，MAIN 只需逐条确认或纠正。
  其中两条是查证出来的**真风险**：
  1. 主线的 `I_last` 是**行尾 EOL，不是帧尾**（`isp/uial2axis.v:55`，`isp_top.v:124` 注释同）——
     我的 `I_eof` 必须由 MAIN 另造；**若把 `I_last` 直接当 `I_eof`，每行都会发布一次结果，
     整帧统计全错**。这是接入时最容易踩的一条。
  2. 观察流在 **`S_csi_rx_clk`** 域、显示在 HDMI 像素时钟域（`design_top_wrapper.v:589`）——
     **CDC 是必需的**；握手/FIFO选择需证明最坏突发、服务时间、容量及复位屏障，不能由平均帧率决定。
- **资源口径后来已修订**：旧 gate 锚点与概算不再据以判断预算；当前 §4 和 VERIFICATION.md
  区分独立 gate 与历史 MAIN routed。整机增量必须由新的实际顶层构建得出。

**证据口径不变**：以上仍是独立仿真；`S_csi_rx_clk` 的真实频率、综合资源与时序、
以及整机画面效果，都要 MAIN 接入后才能回答。

## 9. 文字更新整组发布（2026-10-17）

旧测试等待转换结束后才扫像素，漏掉了转换期间的输出：旧 RTL 分别发布 count、X、Y，
状态和明暗直接跟随新输入；三轮转换还会重新读取不同时间的输入。实测会出现
`N123456` 已更新、坐标仍为 `X0000 Y000`，并可能把忙时新来的坐标拼进旧 count。

现在开始转换时快照 `count/x/y/state/show`，前两轮结果暂存，最后一轮结束后整组同拍发布。
一组转换 70 拍，忙时先保留上一组完整显示，再处理最新稳定输入，最多 140 拍可见。
中间更新允许合并；该模块没有事件队列，也不替代 MAIN 的原子 CDC、帧身份匹配或整帧切换。

新增回归通过公开字形端口逐拍读完整两行，使用 Python 十进制格式化和输入快照集合检查一致性，
不复制 RTL 双-dabble/FSM。覆盖各转换阶段到达新值、连续更新、仅状态/明暗变化、
中途复位、饱和及停止更新后的收敛；`XW/YW=11/10` 与 `14/12` 共 **7962 拍通过**。
将同一测试指向旧 RTL，能抓出 **4036 个不一致采样**，其中有 2926 个数字字段混合采样。
既有真实字库回归 **28/28、307078 像素**及链路渲染 **192010 拍、768000 像素**均通过。

另补 `tools/synth_text.tcl` 独立 gate 综合检查，使用 TD **6.2.168116**、
PH1P35MDG324/-3、人工 10 ns 测试时钟；不改主线 TD 文件。
旧版为 **232 LUT/148 reg**，修复后 **282 LUT/194 reg**，增量 **50 LUT/46 reg**，
两者均 **0 ERAM/0 DSP**。这是文字模块的 gate 结果，未做布局布线或整机验证。
复现命令、范围和原始 area 报告见 [`VALIDATION.md`](evidence/text_atomic_2026-10-17/VALIDATION.md)。

## 10. 下一阶段研究（2026-10-17）

[`research/ROADMAP.md`](research/ROADMAP.md) 记录六个固定版本公开仓库的核查、选型标准，
以及 10 种候选在 88 份合成输入上的 880 次 CPU 对照。初步优先研究中心支持过滤与
强弱两阶段候选关联，保留弱桥、快速位移和碎片目标的失败证据。
这些是离线研究原型，未修改 RTL 或默认参数；目标选择语义和新接口仍需 MAIN 确认。

## 11. RGB 回放与帧结束修复（2026-10-18）

独立 RGB→可选过滤→统计→track→框/文字链已完成六尺寸、两模式回放，实际接收
7760408 像素。分类数学等价优化消除了独立 gate 测试架中的 8 DSP；
数据契约、逐帧评价、复位取消及待 MAIN 确认项见 [REPLAY.md](REPLAY.md)。
完整结果归档在 [回放验证](evidence/replay_2026-10-17/VALIDATION.md)。

随后负对照发现原检测器在 EOF 后仍保持帧打开，零散 EOF 会把上一帧 count=4
错误地再发布为有效 count=8。现于 EOF 关闭帧，新增不依赖模型的硬编码回归；
检测器含 720p 用例 25/25、既有链路 396 拍及 RGB 异常 EOF 检查通过。
修复前后证据见 [EOF 验证](evidence/eof_close_2026-10-18/VALIDATION.md)。
相机效果、最小目标与多个同色目标策略按用户要求保留，过滤仍默认关闭。

## 12. 系统闭环审计与A1修复（2026-10-18，本地待审）

本地隔离分支完成类别标签最小修复：非法TARGET_CLASS与分类判据统一回退红色。
12组参数、四条结果路径硬期望通过；旧基线7组失败，修复只改变42个结果包的类别字段。
分类/检测/链路及六尺寸两模式RGB完整回归通过，见
[A1_VALIDATION.md](evidence/integration_audit_2026-10-18/A1_VALIDATION.md)。

本轮还提供 [工程事实审计](integration/ENGINEERING_AUDIT.md)、
[A2待批准方案](integration/TRACK_ADMISSION_PROPOSAL.md)、
[MAIN接口草案](integration/MAIN_CONTRACT_DRAFT.md) 和 [故障矩阵](integration/FAULT_MATRIX.md)。
审计纠正了AWB提前user不能直接作SOF的旧建议；真实帧身份、DDR代次、CDC/显示仍待MAIN。
TRACK生产RTL未改，六个特征测试缺口保持OPEN；36条契约模型通过不表示整机实现。
本轮未推送、未改MAIN、未综合/P&R/bit/板测。

```text
python features/color_target/run_target_class_contract.py --out <新目录>
python features/color_target/run_target_class_contract.py --models-only --out <新目录>
python features/color_target/run_track_admission_audit.py --out <新目录>
python features/color_target/run_integration_contract.py --out <新目录>
python features/color_target/tools/audit_integration_sources.py --out <新目录>
```

## 13. 整合交付与验证方法（2026-10-18）

run_verification.py 汇总已有独立测试，保留原始日志、命令、退出码、源码哈希及开放决策门。
models/quick/full 分别为 3/7/13 项；TRACK 特征吻合单列 MATCHED / OPEN，不伪装生产需求通过。
INTEGRATION、INTERFACE、DEMO_STEPS 已统一 SOF、EOF 计时、身份/年龄、框文字提交和资源口径。
board 下纳入现有完整视频的观察步骤与回报模板；既有证据目录、失败对照和 bit 不覆盖。
本轮上传沿原 TARGET 分支及 PR #2，仍由负责人审查；MAIN/A2 生产适配与实拍门限待决策。
