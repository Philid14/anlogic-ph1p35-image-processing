# 基础多算法融合：Stage 0 / Stage 1 集成方案

审计日期：2026-10-10。正式基础为 A 的 `design_top_wrapper` / `camera_to_dsi_display.al`，Git `c1e3002`（GAIN_TEST_E candidate）。用户本轮反馈 15.75× 亮度基本满意，选为临时固定基准；仅代表用户画质选择，不补造定量噪声、长稳或 I²C 读回结果。赛题 PDF 第 16–18 页已回读：Stage 1 对应 FPGA 基础算法、连续显示、安路 Logo；四模式与状态显示属于后续进阶功能。本轮止于固定 Edge candidate。

## 三工程结构与编译依据

路径缩写：

- A：`in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd`。
- B：`edge_example/lab_ex2_edge_SC500_720P/lab_ex2_edge`。
- C：`2026-10-05/2026-10-05/wo/outputs/ph1p35a_vision_system`，来自用户指定的队友目录；全部只读，不能执行会写入其中的生成/仿真/构建脚本。

| 项目 | A 正式主工程 | B 随仓库边缘参考 | C 队友工作工程 |
|---|---|---|---|
| 入口 / Top | `td_project/camera_to_dsi_display.al` / `design_top_wrapper` | 同名入口 / `design_top_wrapper` | `td_project/al_high_vision.al` / `al_top_main` |
| 实际 ISP | RAW10 饱和减 15 → BGGR demosaic → `data128_96` → 根级 `awb.v`（AWB_V2） | demosaic → `data128_96` → 根级旧 AWB → `edge_detect_96` | 修改过的 RAW 解包/BLC → demosaic → vendor AWB → CCM → Gamma → `al_pix_pipeline`，另有 AE 统计和控制 |
| 算法位置 | 当前 AWB 后直接打包 | AWB 后、DDR 前 | AWB/CCM/Gamma 后、DDR 前 |
| 位宽 | RAW10 40b=4 像素；demosaic 128b=4 个带 padding 的 RGB；紧凑 RGB 96b；DDR 128b连续字节流；HDMI 24b | 同 A；Sobel 96b→96b | 同 A；亮度 32b=4×8，窗口64b=8×8，Sobel幅值44b=4×11 |
| 算法/控制 | BLC_V1、AWB_V2、固定 15.75×、Logo/CNT | 两像素对 Sobel，固定阈值80 | 灰度、Binary、中值、Gaussian、Sobel、局部 Canny、锐化、模式/阈值按键、拨码、动态 OSD |
| 状态 | 用户确认可采集显示，15.75×亮度基本满意 | 本轮静态参考，不把文件名视为官方原版或本轮上板证明 | 用户称已实现但效果尚不理想；其文档实测声明与当前文件不等价于本项目验证 |

A 的 `.al` 在改动前显式列出 53 个源/IP/约束条目；活动模块为根级 `awb.v`、根级 `signal_delay.v`、`isp/isp_top.v`、`demosaic_4x_2_0/*` 和打包器。目录中的 `isp/awb/awb.v`、独立 `isp/BLC/BLC.v` 等不是当前活动模块；`data96_128` 虽列入工程，本链路并未实例化。Stage 1 新模块必须同时加入 `.al` 与 TD run `.prj`，不能只放文件到目录。

## 四像素打包与时序契约

- `data128_96` 输出 `{I[23:0],I[55:32],I[87:64],I[119:96]}`。紧凑流的 pixel0 在 `[95:72]`，随后 `[71:48]`、`[47:24]`、`[23:0]`；每像素 `R[23:16],G[15:8],B[7:0]`。AWB 保持此顺序。
- AWB_V2 的 `O_tuser=I_tuser`，为**提前帧首通知**；像素经既有 RAM 延迟50及乘法流水后到达。它不是标准 AXI 中必须与首有效拍重合的 SOF。`video_in` 用它展宽并跨 DDR 域复位 FIFO，必须保留该提前量。
- AWB `O_tlast=!valid_d1 && valid_d2`，是最后有效拍伴随的行尾通知；不是帧末。新窗口计数按每行320有效拍推进，以行宽为主要依据，禁止把无效期独立 `tlast` 当一拍像素。
- A 是无背压采集流：Top 的 `S_ISP_O_tready` 未驱动，原 AWB/demosaic 有 ready 透传但不按 ready 停止数据。DDR 端用异步 FIFO 解耦。Stage 1 明确恒可接收，算法有效拍不因外部 ready 丢弃；这不宣称为完整可背压 AXI 模块。
- `data_96bit_to_128bit` 每连续4个96b拍输出3个128b拍，无效拍将计数清零；所以主链路每行有效像素必须连续且320拍可被4整除。Stage 1 必须只延迟有效包络、不插入行内气泡，生成每帧172800个DDR字（1280×720×3/16）。

## B Sobel 的精度、缓存与问题

参考文件 `user_source/hdl_source/isp/edge_detect_96.v` SHA-256：`68c1676a7af4728caddcd5e0932e329baf1e23cca66ca4bef552aa3bb0ec98a3`。

四像素分别算 `floor(R/4)+floor(G/2)+floor(B/4)`（最大253），相邻两个灰度取平均，形成每拍两样本。两条320×16b行缓存总逻辑容量10240bit；每拍计算两个3×3 Sobel窗口，`|Gx|+|Gy|>=80` 输出白，否则黑，输出 `{edge0,edge0,edge1,edge1}`。有效空间采样为 **640×720**，HDMI格式仍1280×720；横向核步距相当于两个原像素，并非1280点逐像素 Sobel。窗口中心对应上一行及前一个水平样本，显示约右移2原像素、下移1行；原实现前两行及每行首4像素置黑，右端/末行缺相应中心结果，不声称坐标无偏移。

原文件一个输出寄存级，RAM组合读→Sobel多级加减→绝对值→阈值在同一路径；`ram_style=block` 不保证异步读一定映射ERAM。存储阵列不复位，依靠前两行屏蔽。`I_tuser` 仅在 valid 分支影响 x/y，遇 A/B 的提前帧首通知会漏掉复位，异常帧后易失步。行缓存写入也没有按 SOF 使用有效地址修正。原 `I_tready` 是输入、`O_tready` 是输出，B 集成层又把其连成自反馈/多驱动，不能沿用该接线。B ISP 顶层把 AWB tlast 送输出但数据已经过 Edge，属于延迟不一致（当前 DDR 不用此信号，不能据此认为契约正确）。

Stage 1 保留 B 的灰度、像素对采样、Sobel核、阈值和结果复制；局部适配提前 SOF、ready 命名、同步 RAM 与运算流水，先获得可审计的低开销版本。没有获得可信官方原始压缩包核验，不新建伪官方 baseline tag。

## C 可复用评估

| 文件（相对 C） | 分类与适配难度 | 结论 |
|---|---|---|
| `rtl/pix/al_binarize.v` | 判决/黑白打包可复用，低 | 参数hi/lo、4×8亮度→4bit/32bit，1拍；rst_n 未使用，集成前要补控制复位与统一时序 |
| `rtl/pix/al_rgb2ycbcr.v` | 需接口/资源适配，中 | Y=(77R+150G+29B+128)>>8，2拍；Cb/Cr目前无需求，不能把全模块零DSP注释当实测，宜只保留共享Y思想 |
| `rtl/pix/al_linebuf_3x3.v` / `al_sobel.v` | 需适配，中高 | 三RAM轮转、重叠8像素字，可形成四个水平逐像素结果；控制2拍，Sobel1拍；仍存在空间偏移、SOF不与valid同拍和输出坐标未寄存等适配问题，Stage1不接入 |
| `rtl/ctrl/al_key_debounce.v` | 同步/消抖思路可复用，低中 | 两级输入同步、释放短按、独立长按；应重新核对板上按键和时钟，Stage1不改变按键 |
| `rtl/ctrl/al_mode_ctrl.v` | 仅局部思想，高 | 功能混入BLC、AE、CCM；24MHz输出直接进像素域，拨码未同步、无帧边界模式锁存，不能整块复制 |
| `rtl/osd/al_osd_statusbar.v` | 需精简/CDC适配，中 | 在现有Logo层后独立文字层、复用字模的思路可用；当前模式/使能等直接跨域，统计逐位同步不保证多位一致性，需帧级状态协议 |
| `rtl/pix/al_pix_pipeline.v` | 不适合整体复用，高 | 文件头仍说5拍，实际 LAT=12；包含大量本轮禁用功能，空间与分支延迟复杂且资源开销较高 |

C 中已确认具体错误：`al_morph3x3.i_mode` 为2位，却传 `.i_mode(2'd4)`；4被截断为0，所谓Edge去斑点实际选择旁路。控制域 `S_disp_mode` 直接用于像素MUX和HDMI OSD，未帧边界生效，也没有DDR帧关联，可能半帧切换且文字与显示内容不同步。OSD `dec1` 只减十位未减百位，值100/200的个位会截断成4/8，后续不能直接复用其数值显示。不能因为仿真模型通过就忽略这些接口事实。当前 C route.qor 为 Slice17224（81.18%）、RAM69、DSP22、Setup+108ps/Hold+20ps；仅为C自身报告，不预测A集成结果。

只读源码指纹：`al_pix_pipeline.v=c8c2f4777b84d470efe1b0dda37fd97d3205c7aa89b5bae74b13e57fee0e0027`；`al_linebuf_3x3.v=e62b7163d1d747f8e9c6eecd770dd7a2f4ad66fd25eab2d4d466e5d121de3bd1`；`al_sobel.v=51010ab8c5da25df9019e71e118e8582d89814384f3a80fb2ad890947b4ea1c2`。本轮不复制C RTL，不修改C，也不把其全部内容加入Git。

## Stage 1 具体实施

实际连接：SC500CS→MIPI→RAW10→BLC15→demosaic→AWB_V2→**edge_detect_96**→96/128打包→DDR→现有Logo/CNT OSD→HDMI。仅新增算法文件并在 `isp_top` 局部接线；`EDGE_ENABLE` 编译时参数默认1，0生成分支完全恢复原96b输出路径，不同时并行硬MUX不同延迟的分支。运行时切换和MODE文字留Stage3。

算法预定5个寄存级：灰度/像素对→同步RAM读/当前行对齐→Gx/Gy→绝对值幅值和→阈值RGB。数据valid、提前tuser、tlast同样延迟5拍。打包器再寄存1拍，Edge分支的顶层tlast也补1拍，与128b valid/data对齐；Original生成分支保留原接线。两行RAM不复位，后一行缓存写入延后一拍，用已寄存中间行数据避免组合RAM级联；行地址随数据寄存。SOF无论valid与否都重置计数/横向carry；同拍首像素使用地址0和行0。每帧/每行像素数保持不变，前两行和首组清黑，后续边缘核遵循B近似定义。

新增验证应覆盖：均匀/黑白竖界/横界/斜界/RGB分量、阈值边界、四像素顺序、像素对复制、连续多帧、提前/同拍SOF、复位/截断帧恢复、不同消隐长度与有效气泡（模块级）、全宽1280；逐拍比较独立软件空间模型与RTL。用真实打包器核对每帧DDR字数、字节顺序与提前SOF位置。软件模型、RTL仿真、TD实现与上板必须分别记录。

## 资源、时序门槛与后续接口

GAIN_TEST_E：LUT6 13757/21216、FF13625/42432、Slice15652/21216（73.77%）、ERAM40/108、DSP9/40；Setup0ps/Hold20ps。容量允许尝试小规模Sobel，但零setup裕量不保证加入后成功；必须完整实现，发现负WNS不能交付通过版本，先局部等价流水优化，不能修改SDC/PLL/DDR/HDMI来掩盖违例。

未来 Gamma/CCM 可在 AWB→共享RGB处理接口之间串联，96b每拍4像素且必须连同有效/帧通知/行尾定义统一；Stage1不增加Gamma/CCM。Stage2共享一份灰度供Gray/Binary/Sobel，Binary阈值参数化；选择保留低开销像素对Edge还是升级全宽窗口，要依据Stage1实拍与资源。Stage3统一所有分支的拍数与空间坐标，控制同步并在输入帧边界锁存，再把生效模式随DDR帧传递给HDMI OSD；不能只延迟按键状态就声称画面/文字对应同一帧。

## 本轮验证与交付状态

静态审计及 Icarus Verilog RTL 仿真已完成。`tests/run_edge_v1.py --full` 用独立空间模型逐拍对照真实算法和原有打包器，七组测试共512024有效输入拍通过，含64/1280行宽、阈值0/80/81/2025、均匀/水平/垂直/斜向/RGB/随机场景、提前或同拍SOF、截断帧恢复及算法级气泡。两完整1280×720帧共460800个96b输入拍、345600个128b输出字，字节内容、valid、tuser、tlast、5拍算法延迟全部匹配；每完整帧172800个DDR字。算法级气泡测试不用于宣称原打包器支持行内气泡。

测试还在AWB输出边界注入相同激励，对照实际 `isp_top` 的 Original 生成分支与原打包器；完整1280×720激励另验证实际 Edge 生成分支的128b data/valid/tuser及补偿后的tlast。`tests/isp_boundary_stubs.v` 只用于这个接线测试，不模拟冻结的AWB或demosaic算法。

`tests/edge_v1_frozen_manifest.json` 保存改动前的192个主工程文件及68个B/C只读源码指纹，运行前后均一致。RTL测试不模拟MIPI、AWB RAM/除法IP、完整DDR/HDMI；这些由完整TD实现检查以及随后上板验证覆盖。此节将在TD全流程结束后补充实际资源/时序，当前不宣称新增Sobel已上板。
